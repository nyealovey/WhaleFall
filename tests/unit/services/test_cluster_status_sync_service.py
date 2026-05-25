from __future__ import annotations

from typing import Any

import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.models.instance import Instance
from app.models.sqlserver_ag_sync_state import SQLServerAgDatabaseSyncState
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.services.cluster_status_sync.service import ClusterStatusSyncService


def _create_schema() -> None:
    db.metadata.create_all(
        bind=db.engine,
        tables=[
            db.metadata.tables["instances"],
            db.metadata.tables["sqlserver_clusters"],
            db.metadata.tables["sqlserver_cluster_instances"],
            db.metadata.tables["sqlserver_availability_groups"],
            db.metadata.tables["sqlserver_ag_database_sync_states"],
        ],
    )


class _FakeConnection:
    def __init__(self, rows: list[dict[str, Any]] | Exception) -> None:
        self.rows = rows
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def execute_query(self, _query: str, params=None):
        del params
        if isinstance(self.rows, Exception):
            raise self.rows
        return self.rows


class _FakeFactory:
    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    def create_connection(self, _instance: Instance) -> _FakeConnection:
        return self.connection


@pytest.mark.unit
def test_sqlserver_ag_status_sync_records_healthy_database_state() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        instance = Instance(name="sql-1", db_type=DatabaseType.SQLSERVER, host="10.0.0.10", port=1433)
        cluster = SQLServerCluster(name="cluster-a", domain_name="wz.dc", description="")
        db.session.add_all([instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        db.session.add(
            SQLServerAvailabilityGroup(
                cluster_id=cluster.id,
                name="AG01",
                listener_name="AG01",
                listener_host="10.0.0.20",
            ),
        )
        db.session.commit()

        service = ClusterStatusSyncService(
            connection_factory=_FakeFactory(
                _FakeConnection(
                    [
                        {
                            "ag_name": "AG01",
                            "database_name": "billing",
                            "replica_server_name": "sql-1",
                            "synchronization_state_desc": "SYNCHRONIZED",
                            "synchronization_health_desc": "HEALTHY",
                            "database_state_desc": "ONLINE",
                            "is_suspended": 0,
                            "log_send_queue_size": 0,
                            "redo_queue_size": 0,
                        },
                    ],
                ),
            ),
        )

        result = service.sync_sqlserver_cluster(cluster.id)

        assert result["status"] == "completed"
        assert result["abnormal_database_count"] == 0
        state = SQLServerAgDatabaseSyncState.query.one()
        assert state.ag_name == "AG01"
        assert state.database_name == "billing"
        assert state.is_abnormal is False


@pytest.mark.unit
def test_sqlserver_ag_status_sync_marks_suspended_and_not_online_as_abnormal() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        instance = Instance(name="sql-1", db_type=DatabaseType.SQLSERVER, host="10.0.0.10", port=1433)
        cluster = SQLServerCluster(name="cluster-a", domain_name="wz.dc", description="")
        db.session.add_all([instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        db.session.add(
            SQLServerAvailabilityGroup(
                cluster_id=cluster.id,
                name="AG01",
                listener_name="AG01",
                listener_host="10.0.0.20",
            ),
        )
        db.session.commit()

        service = ClusterStatusSyncService(
            connection_factory=_FakeFactory(
                _FakeConnection(
                    [
                        {
                            "ag_name": "AG01",
                            "database_name": "billing",
                            "replica_server_name": "sql-1",
                            "synchronization_state_desc": "NOT_SYNCHRONIZING",
                            "synchronization_health_desc": "NOT_HEALTHY",
                            "database_state_desc": "RECOVERY_PENDING",
                            "is_suspended": 1,
                            "suspend_reason_desc": "USER",
                            "log_send_queue_size": 12,
                            "redo_queue_size": 8,
                        },
                    ],
                ),
            ),
        )

        result = service.sync_sqlserver_cluster(cluster.id)

        assert result["status"] == "completed"
        assert result["abnormal_database_count"] == 1
        state = SQLServerAgDatabaseSyncState.query.one()
        assert state.is_abnormal is True
        assert "NOT_HEALTHY" in (state.error_summary or "")
        assert "RECOVERY_PENDING" in (state.error_summary or "")
        assert "suspended" in (state.error_summary or "")


@pytest.mark.unit
def test_sqlserver_ag_status_sync_connection_failure_is_cluster_scoped() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        instance = Instance(name="sql-1", db_type=DatabaseType.SQLSERVER, host="10.0.0.10", port=1433)
        cluster = SQLServerCluster(name="cluster-a", domain_name="wz.dc", description="")
        db.session.add_all([instance, cluster])
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        db.session.add(
            SQLServerAvailabilityGroup(
                cluster_id=cluster.id,
                name="AG01",
                listener_name="AG01",
                listener_host="10.0.0.20",
            ),
        )
        db.session.commit()

        service = ClusterStatusSyncService(connection_factory=_FakeFactory(_FakeConnection(RuntimeError("boom"))))

        result = service.sync_sqlserver_cluster(cluster.id)

        assert result["status"] == "failed"
        assert "boom" in result["error_message"]
