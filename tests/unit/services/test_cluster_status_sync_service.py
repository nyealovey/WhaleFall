from __future__ import annotations

from typing import Any, cast

import pytest

from app import create_app, db
from app.core.constants import DatabaseType
from app.core.types import SyncConnection
from app.models.instance import Instance
from app.models.sqlserver_ag_sync_state import SQLServerAgDatabaseSyncState, SQLServerAgReplicaSyncState
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.services.cluster_status_sync.read_service import SQLServerAgDatabaseSyncStatesReadService
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
            db.metadata.tables["sqlserver_ag_replica_sync_states"],
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

    def create_connection(self, instance: Instance) -> SyncConnection:
        del instance
        return cast(SyncConnection, self.connection)


class _FakeFactoryByInstance:
    def __init__(self, connections: dict[str, _FakeConnection]) -> None:
        self.connections = connections
        self.requested_instance_names: list[str] = []

    def create_connection(self, instance: Instance) -> SyncConnection:
        self.requested_instance_names.append(instance.name)
        return cast(SyncConnection, self.connections[instance.name])


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
                            "replica_role_desc": "PRIMARY",
                            "availability_mode_desc": "SYNCHRONOUS_COMMIT",
                            "failover_mode_desc": "AUTOMATIC",
                            "seeding_mode_desc": "AUTOMATIC",
                            "replica_synchronization_health_desc": "HEALTHY",
                            "connected_state_desc": "CONNECTED",
                            "operational_state_desc": "ONLINE",
                            "recovery_health_desc": "ONLINE",
                            "cluster_state_desc": "NORMAL_QUORUM",
                            "cluster_type_desc": "WSFC",
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
        replica_state = SQLServerAgReplicaSyncState.query.one()
        assert replica_state.replica_server_name == "sql-1"
        assert replica_state.role_desc == "PRIMARY"
        assert replica_state.is_primary is True
        assert replica_state.is_abnormal is False
        assert replica_state.cluster_state_desc == "NORMAL_QUORUM"
        assert replica_state.cluster_type_desc == "WSFC"
        db.session.refresh(cluster)
        assert cluster.last_status_sync_status == "completed"
        assert cluster.last_status_sync_error is None
        assert cluster.last_status_sync_at is not None


@pytest.mark.unit
def test_sqlserver_ag_status_sync_collects_rows_from_all_bound_instances() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        secondary = Instance(name="sql-secondary", db_type=DatabaseType.SQLSERVER, host="10.0.0.11", port=1433)
        primary = Instance(name="sql-primary", db_type=DatabaseType.SQLSERVER, host="10.0.0.10", port=1433)
        cluster = SQLServerCluster(name="cluster-a", domain_name="wz.dc", description="")
        db.session.add_all([secondary, primary, cluster])
        db.session.flush()
        db.session.add_all(
            [
                SQLServerClusterInstance(cluster_id=cluster.id, instance_id=secondary.id),
                SQLServerClusterInstance(cluster_id=cluster.id, instance_id=primary.id),
                SQLServerAvailabilityGroup(
                    cluster_id=cluster.id,
                    name="AG01",
                    listener_name="AG01",
                    listener_host="10.0.0.20",
                ),
            ],
        )
        db.session.commit()

        factory = _FakeFactoryByInstance(
            {
                "sql-secondary/ag-status": _FakeConnection(
                    [
                        {
                            "ag_name": "AG01",
                            "database_name": "billing",
                            "replica_server_name": "sql-secondary",
                            "synchronization_state_desc": "SYNCHRONIZED",
                            "synchronization_health_desc": "HEALTHY",
                            "database_state_desc": "ONLINE",
                            "is_suspended": 0,
                            "replica_role_desc": "SECONDARY",
                            "replica_synchronization_health_desc": "HEALTHY",
                            "connected_state_desc": "CONNECTED",
                            "cluster_state_desc": "NORMAL_QUORUM",
                            "cluster_type_desc": "WSFC",
                        },
                    ],
                ),
                "sql-primary/ag-status": _FakeConnection(
                    [
                        {
                            "ag_name": "AG01",
                            "database_name": "billing",
                            "replica_server_name": "sql-primary",
                            "synchronization_state_desc": "SYNCHRONIZED",
                            "synchronization_health_desc": "HEALTHY",
                            "database_state_desc": "ONLINE",
                            "is_suspended": 0,
                            "replica_role_desc": "PRIMARY",
                            "replica_synchronization_health_desc": "HEALTHY",
                            "connected_state_desc": "CONNECTED",
                            "cluster_state_desc": "NORMAL_QUORUM",
                            "cluster_type_desc": "WSFC",
                        },
                    ],
                ),
            },
        )

        result = ClusterStatusSyncService(connection_factory=factory).sync_sqlserver_cluster(cluster.id)

        assert result["status"] == "completed"
        assert result["source_instance_ids"] == [secondary.id, primary.id]
        assert factory.requested_instance_names == ["sql-secondary/ag-status", "sql-primary/ag-status"]
        replica_states = SQLServerAgReplicaSyncState.query.order_by(SQLServerAgReplicaSyncState.replica_server_name.asc()).all()
        assert [state.replica_server_name for state in replica_states] == ["sql-primary", "sql-secondary"]
        assert [state.replica_server_name for state in replica_states if state.is_primary] == ["sql-primary"]
        dashboard = SQLServerAgDatabaseSyncStatesReadService().get_ag_dashboard(cluster.id, SQLServerAvailabilityGroup.query.one().id)
        assert dashboard["summary"]["primary_replica"] == "sql-primary"


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
        db.session.refresh(cluster)
        assert cluster.last_status_sync_status == "failed"
        assert cluster.last_status_sync_error == "sql-1 boom"
        assert cluster.last_status_sync_at is not None


@pytest.mark.unit
def test_sqlserver_ag_dashboard_groups_database_states_by_replica() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        _create_schema()
        cluster = SQLServerCluster(
            name="cluster-a",
            domain_name="wz.dc",
            description="",
            last_status_sync_status="completed",
        )
        db.session.add(cluster)
        db.session.flush()
        ag = SQLServerAvailabilityGroup(cluster_id=cluster.id, name="AG01", listener_host="ag01")
        db.session.add(ag)
        db.session.flush()
        db.session.add_all(
            [
                SQLServerAgReplicaSyncState(
                    cluster_id=cluster.id,
                    availability_group_id=ag.id,
                    ag_name="AG01",
                    replica_server_name="sql-1",
                    role_desc="PRIMARY",
                    availability_mode_desc="SYNCHRONOUS_COMMIT",
                    failover_mode_desc="AUTOMATIC",
                    synchronization_health_desc="HEALTHY",
                    connected_state_desc="CONNECTED",
                    is_primary=True,
                    is_abnormal=False,
                ),
                SQLServerAgReplicaSyncState(
                    cluster_id=cluster.id,
                    availability_group_id=ag.id,
                    ag_name="AG01",
                    replica_server_name="sql-2",
                    role_desc="SECONDARY",
                    availability_mode_desc="SYNCHRONOUS_COMMIT",
                    failover_mode_desc="AUTOMATIC",
                    synchronization_health_desc="NOT_HEALTHY",
                    connected_state_desc="DISCONNECTED",
                    is_primary=False,
                    is_abnormal=True,
                    error_summary="health=NOT_HEALTHY; connected=DISCONNECTED",
                ),
                SQLServerAgDatabaseSyncState(
                    cluster_id=cluster.id,
                    availability_group_id=ag.id,
                    ag_name="AG01",
                    database_name="billing",
                    replica_server_name="sql-1",
                    synchronization_state_desc="SYNCHRONIZED",
                    synchronization_health_desc="HEALTHY",
                    database_state_desc="ONLINE",
                    is_abnormal=False,
                ),
                SQLServerAgDatabaseSyncState(
                    cluster_id=cluster.id,
                    availability_group_id=ag.id,
                    ag_name="AG01",
                    database_name="billing",
                    replica_server_name="sql-2",
                    synchronization_state_desc="NOT_SYNCHRONIZING",
                    synchronization_health_desc="NOT_HEALTHY",
                    database_state_desc="ONLINE",
                    is_abnormal=True,
                    error_summary="health=NOT_HEALTHY",
                    log_send_queue_size=12,
                    redo_queue_size=7,
                ),
            ],
        )
        db.session.commit()

        result = SQLServerAgDatabaseSyncStatesReadService().get_ag_dashboard(cluster.id, ag.id)

        assert result["summary"]["cluster_name"] == "cluster-a"
        assert result["summary"]["ag_name"] == "AG01"
        assert result["summary"]["primary_replica"] == "sql-1"
        assert result["summary"]["status"] == "abnormal"
        assert result["kpis"] == {
            "total_databases": 1,
            "abnormal_databases": 1,
            "normal_databases": 0,
            "replica_count": 2,
            "affected_replicas": 1,
        }
        assert [replica["replica_server_name"] for replica in result["replicas"]] == ["sql-1", "sql-2"]
        assert result["replicas"][1]["status"] == "abnormal"
        assert [group["replica_server_name"] for group in result["database_groups"]] == ["sql-1", "sql-2"]
        assert result["database_groups"][1]["databases"][0]["database_name"] == "billing"
        assert result["database_groups"][1]["databases"][0]["status"] == "abnormal"
