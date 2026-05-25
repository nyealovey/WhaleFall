from __future__ import annotations

from typing import Any

import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.core.exceptions import ConflictError, ValidationError
from app.models.instance import Instance
from app.models.mysql_cluster import MySQLCluster, MySQLClusterInstance
from app.schemas.mysql_clusters import MySQLClusterListQuery
from app.services.mysql_clusters.service import MySQLClusterManagementService
from app.utils.time_utils import time_utils


def _create_schema() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["instances"],
            db.metadata.tables["mysql_clusters"],
            db.metadata.tables["mysql_cluster_instances"],
        ],
    )


class _FakeConnection:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.queries: list[str] = []

    def connect(self) -> bool:
        return True

    def disconnect(self) -> None:
        return None

    def execute_query(self, query: str, params=None):
        del params
        self.queries.append(query)
        response = self.responses.get(query)
        if isinstance(response, Exception):
            raise response
        return response or []


class _FakeFactory:
    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    def create_connection(self, _instance: Instance) -> _FakeConnection:
        return self.connection


@pytest.mark.unit
def test_mysql_cluster_replace_instances_allows_only_existing_mysql_instances() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        mysql = Instance(name="mysql-1", db_type=DatabaseType.MYSQL, host="127.0.0.1", port=3306)
        sqlserver = Instance(name="sql-1", db_type=DatabaseType.SQLSERVER, host="127.0.0.1", port=1433)
        cluster = MySQLCluster(name="mysql-cluster-a")
        db.session.add_all([mysql, sqlserver, cluster])
        db.session.commit()

        service = MySQLClusterManagementService()

        result = service.replace_instances(cluster.id, {"instance_ids": [mysql.id]})

        assert result["instances"][0]["id"] == mysql.id
        with pytest.raises(ValidationError, match="只能绑定未删除的 MySQL 实例"):
            service.replace_instances(cluster.id, {"instance_ids": [sqlserver.id]})


@pytest.mark.unit
def test_mysql_instance_can_only_bind_one_cluster() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        mysql = Instance(name="mysql-1", db_type=DatabaseType.MYSQL, host="127.0.0.1", port=3306)
        first = MySQLCluster(name="mysql-cluster-a")
        second = MySQLCluster(name="mysql-cluster-b")
        db.session.add_all([mysql, first, second])
        db.session.flush()
        db.session.add(MySQLClusterInstance(cluster_id=first.id, instance_id=mysql.id))
        db.session.commit()

        service = MySQLClusterManagementService()

        with pytest.raises(ConflictError, match="已绑定到群集"):
            service.replace_instances(second.id, {"instance_ids": [mysql.id]})


@pytest.mark.unit
def test_mysql_topology_sync_prefers_show_replica_status() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        mysql = Instance(name="mysql-replica", db_type=DatabaseType.MYSQL, host="10.0.0.2", port=3306)
        cluster = MySQLCluster(name="mysql-cluster-a")
        db.session.add_all([mysql, cluster])
        db.session.flush()
        db.session.add(MySQLClusterInstance(cluster_id=cluster.id, instance_id=mysql.id))
        db.session.commit()

        connection = _FakeConnection(
            {
                "SHOW REPLICA STATUS": [
                    {
                        "Source_Host": "10.0.0.1",
                        "Source_Port": 3306,
                        "Replica_IO_Running": "Yes",
                        "Replica_SQL_Running": "Yes",
                        "Seconds_Behind_Source": 0,
                        "Replica_IO_State": "Waiting for source to send event",
                    },
                ],
            },
        )
        service = MySQLClusterManagementService(connection_factory=_FakeFactory(connection))

        result = service.sync_topology(cluster.id)

        assert result["items"][0]["replication_role"] == "replica"
        assert result["items"][0]["source_host"] == "10.0.0.1"
        assert result["items"][0]["replication_status"] == "healthy"
        assert connection.queries == ["SHOW REPLICA STATUS"]


@pytest.mark.unit
def test_mysql_topology_sync_falls_back_to_show_slave_status() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        mysql = Instance(name="mysql-57", db_type=DatabaseType.MYSQL, host="10.0.0.3", port=3306)
        cluster = MySQLCluster(name="mysql-cluster-a")
        db.session.add_all([mysql, cluster])
        db.session.flush()
        db.session.add(MySQLClusterInstance(cluster_id=cluster.id, instance_id=mysql.id))
        db.session.commit()

        connection = _FakeConnection(
            {
                "SHOW REPLICA STATUS": RuntimeError("syntax error"),
                "SHOW SLAVE STATUS": [
                    {
                        "Master_Host": "10.0.0.1",
                        "Master_Port": 3306,
                        "Slave_IO_Running": "Yes",
                        "Slave_SQL_Running": "No",
                        "Seconds_Behind_Master": None,
                        "Last_SQL_Error": "duplicate key",
                    },
                ],
            },
        )
        service = MySQLClusterManagementService(connection_factory=_FakeFactory(connection))

        result = service.sync_topology(cluster.id)

        assert result["items"][0]["replication_role"] == "replica"
        assert result["items"][0]["source_host"] == "10.0.0.1"
        assert result["items"][0]["replication_status"] == "unhealthy"
        assert result["items"][0]["last_error"] == "duplicate key"
        assert connection.queries == ["SHOW REPLICA STATUS", "SHOW SLAVE STATUS"]


@pytest.mark.unit
def test_mysql_topology_sync_marks_replication_status_permission_denied_as_failed() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        mysql = Instance(name="mysql-57", db_type=DatabaseType.MYSQL, host="10.0.0.3", port=3306)
        cluster = MySQLCluster(name="mysql-cluster-a")
        db.session.add_all([mysql, cluster])
        db.session.flush()
        db.session.add(MySQLClusterInstance(cluster_id=cluster.id, instance_id=mysql.id))
        db.session.commit()

        connection = _FakeConnection(
            {
                "SHOW REPLICA STATUS": RuntimeError("syntax error near 'REPLICA STATUS'"),
                "SHOW SLAVE STATUS": RuntimeError(
                    "Access denied; you need (at least one of) the SUPER, REPLICATION CLIENT privilege(s)"
                ),
                "SELECT @@global.read_only AS read_only, @@global.super_read_only AS super_read_only": [(0, 0)],
            },
        )
        service = MySQLClusterManagementService(connection_factory=_FakeFactory(connection))

        result = service.sync_topology(cluster.id)

        assert result["status"] == "failed"
        assert result["instances_failed"] == 1
        assert result["items"][0]["replication_role"] == "unknown"
        assert result["items"][0]["replication_status"] == "failed"
        assert "REPLICATION CLIENT" in result["items"][0]["last_error"]


@pytest.mark.unit
def test_mysql_topology_sync_marks_non_replica_read_write_as_primary() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        mysql = Instance(name="mysql-primary", db_type=DatabaseType.MYSQL, host="10.0.0.1", port=3306)
        cluster = MySQLCluster(name="mysql-cluster-a")
        db.session.add_all([mysql, cluster])
        db.session.flush()
        db.session.add(MySQLClusterInstance(cluster_id=cluster.id, instance_id=mysql.id))
        db.session.commit()

        connection = _FakeConnection(
            {
                "SHOW REPLICA STATUS": [],
                "SHOW SLAVE STATUS": [],
                "SELECT @@global.read_only AS read_only, @@global.super_read_only AS super_read_only": [(0, 0)],
            },
        )
        service = MySQLClusterManagementService(connection_factory=_FakeFactory(connection))

        result = service.sync_topology(cluster.id)

        assert result["items"][0]["replication_role"] == "primary"
        assert result["items"][0]["replication_status"] == "healthy"


@pytest.mark.unit
def test_mysql_cluster_summary_reports_healthy_replica_counts_and_max_lag() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        checked_at = time_utils.now()
        primary = Instance(name="mysql-primary", db_type=DatabaseType.MYSQL, host="10.0.0.1", port=3306)
        replica_fast = Instance(name="mysql-replica-fast", db_type=DatabaseType.MYSQL, host="10.0.0.2", port=3306)
        replica_slow = Instance(name="mysql-replica-slow", db_type=DatabaseType.MYSQL, host="10.0.0.3", port=3306)
        cluster = MySQLCluster(
            name="mysql-cluster-summary",
            last_topology_sync_at=checked_at,
            last_topology_sync_status="completed",
        )
        db.session.add_all([primary, replica_fast, replica_slow, cluster])
        db.session.flush()
        db.session.add_all(
            [
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=primary.id,
                    replication_role="primary",
                    replication_status="healthy",
                    last_checked_at=checked_at,
                ),
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=replica_fast.id,
                    replication_role="replica",
                    replication_status="healthy",
                    seconds_behind_source=0,
                    last_checked_at=checked_at,
                ),
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=replica_slow.id,
                    replication_role="replica",
                    replication_status="healthy",
                    seconds_behind_source=12,
                    last_checked_at=checked_at,
                ),
            ],
        )
        db.session.commit()

        service = MySQLClusterManagementService()
        result = service.list_clusters(MySQLClusterListQuery())
        summary = next(item for item in result["items"] if item["id"] == cluster.id)

        assert summary["abnormal_replica_count"] == 0
        assert summary["replica_count"] == 2
        assert summary["unknown_replica_lag_count"] == 0
        assert summary["max_replica_lag_seconds"] == 12


@pytest.mark.unit
def test_mysql_cluster_summary_counts_unhealthy_failed_and_unknown_instances() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        checked_at = time_utils.now()
        instances = [
            Instance(name=f"mysql-{index}", db_type=DatabaseType.MYSQL, host=f"10.0.1.{index}", port=3306)
            for index in range(1, 5)
        ]
        cluster = MySQLCluster(
            name="mysql-cluster-abnormal",
            last_topology_sync_at=checked_at,
            last_topology_sync_status="completed",
        )
        db.session.add_all([*instances, cluster])
        db.session.flush()
        db.session.add_all(
            [
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=instances[0].id,
                    replication_role="primary",
                    replication_status="healthy",
                    last_checked_at=checked_at,
                ),
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=instances[1].id,
                    replication_role="replica",
                    replication_status="unhealthy",
                    seconds_behind_source=8,
                    last_checked_at=checked_at,
                ),
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=instances[2].id,
                    replication_role="replica",
                    replication_status="failed",
                    last_checked_at=checked_at,
                ),
                MySQLClusterInstance(
                    cluster_id=cluster.id,
                    instance_id=instances[3].id,
                    replication_role="unknown",
                    replication_status="unknown",
                    last_checked_at=checked_at,
                ),
            ],
        )
        db.session.commit()

        service = MySQLClusterManagementService()
        result = service.list_clusters(MySQLClusterListQuery())
        summary = next(item for item in result["items"] if item["id"] == cluster.id)

        assert summary["abnormal_replica_count"] == 3
        assert summary["replica_count"] == 2
        assert summary["unknown_replica_lag_count"] == 1
        assert summary["max_replica_lag_seconds"] == 8


@pytest.mark.unit
def test_mysql_cluster_summary_distinguishes_no_replica_from_unknown_lag() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        checked_at = time_utils.now()
        primary = Instance(name="mysql-primary-only", db_type=DatabaseType.MYSQL, host="10.0.2.1", port=3306)
        replica = Instance(name="mysql-replica-unknown-lag", db_type=DatabaseType.MYSQL, host="10.0.2.2", port=3306)
        no_replica_cluster = MySQLCluster(
            name="mysql-no-replica",
            last_topology_sync_at=checked_at,
            last_topology_sync_status="completed",
        )
        unknown_lag_cluster = MySQLCluster(
            name="mysql-unknown-lag",
            last_topology_sync_at=checked_at,
            last_topology_sync_status="completed",
        )
        never_checked_cluster = MySQLCluster(name="mysql-never-checked")
        db.session.add_all([primary, replica, no_replica_cluster, unknown_lag_cluster, never_checked_cluster])
        db.session.flush()
        db.session.add_all(
            [
                MySQLClusterInstance(
                    cluster_id=no_replica_cluster.id,
                    instance_id=primary.id,
                    replication_role="primary",
                    replication_status="healthy",
                    last_checked_at=checked_at,
                ),
                MySQLClusterInstance(
                    cluster_id=unknown_lag_cluster.id,
                    instance_id=replica.id,
                    replication_role="replica",
                    replication_status="healthy",
                    seconds_behind_source=None,
                    last_checked_at=checked_at,
                ),
            ],
        )
        db.session.commit()

        service = MySQLClusterManagementService()
        result = service.list_clusters(MySQLClusterListQuery())
        summaries = {item["name"]: item for item in result["items"]}

        assert summaries["mysql-no-replica"]["replica_count"] == 0
        assert summaries["mysql-no-replica"]["unknown_replica_lag_count"] == 0
        assert summaries["mysql-no-replica"]["max_replica_lag_seconds"] is None
        assert summaries["mysql-unknown-lag"]["replica_count"] == 1
        assert summaries["mysql-unknown-lag"]["unknown_replica_lag_count"] == 1
        assert summaries["mysql-unknown-lag"]["max_replica_lag_seconds"] is None
        assert summaries["mysql-never-checked"]["last_topology_sync_at"] is None
