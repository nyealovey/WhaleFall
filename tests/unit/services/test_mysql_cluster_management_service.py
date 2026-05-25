from __future__ import annotations

from typing import Any

import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.core.exceptions import ConflictError, ValidationError
from app.models.instance import Instance
from app.models.mysql_cluster import MySQLCluster, MySQLClusterInstance
from app.services.mysql_clusters.service import MySQLClusterManagementService


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
