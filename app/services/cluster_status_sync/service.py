"""群集同步状态检测 Service."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import SimpleNamespace
from typing import Any, Protocol, cast

from app import db
from app.core.constants import DatabaseType
from app.core.types import SyncConnection
from app.models.instance import Instance
from app.models.mysql_cluster import MySQLCluster
from app.models.sqlserver_ag_sync_state import SQLServerAgDatabaseSyncState, SQLServerAgReplicaSyncState
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.services.mysql_clusters.service import MySQLClusterManagementService
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

_AG_DATABASE_SYNC_STATUS_QUERY = """
DECLARE @seeding_expr nvarchar(128) =
    CASE
        WHEN COL_LENGTH(N'sys.availability_replicas', N'seeding_mode_desc') IS NOT NULL
        THEN N'ar.seeding_mode_desc'
        ELSE N'CONVERT(nvarchar(64), NULL)'
    END;

DECLARE @cluster_type_expr nvarchar(128) =
    CASE
        WHEN COL_LENGTH(N'sys.availability_groups', N'cluster_type_desc') IS NOT NULL
        THEN N'ag.cluster_type_desc'
        ELSE N'CONVERT(nvarchar(64), NULL)'
    END;

DECLARE @sql nvarchar(max) = N'
SELECT
    ag.name AS ag_name,
    DB_NAME(drs.database_id) AS database_name,
    ar.replica_server_name AS replica_server_name,
    drs.synchronization_state_desc AS synchronization_state_desc,
    drs.synchronization_health_desc AS synchronization_health_desc,
    drs.database_state_desc AS database_state_desc,
    drs.is_suspended AS is_suspended,
    drs.suspend_reason_desc AS suspend_reason_desc,
    drs.log_send_queue_size AS log_send_queue_size,
    drs.redo_queue_size AS redo_queue_size,
    ars.role_desc AS replica_role_desc,
    ar.availability_mode_desc AS availability_mode_desc,
    ar.failover_mode_desc AS failover_mode_desc,
    ' + @seeding_expr + N' AS seeding_mode_desc,
    ars.synchronization_health_desc AS replica_synchronization_health_desc,
    ars.connected_state_desc AS connected_state_desc,
    ars.operational_state_desc AS operational_state_desc,
    ars.recovery_health_desc AS recovery_health_desc,
    hc.quorum_state_desc AS cluster_state_desc,
    ' + @cluster_type_expr + N' AS cluster_type_desc
FROM sys.dm_hadr_database_replica_states AS drs
JOIN sys.availability_groups AS ag ON drs.group_id = ag.group_id
JOIN sys.availability_replicas AS ar ON drs.replica_id = ar.replica_id
LEFT JOIN sys.dm_hadr_availability_replica_states AS ars
    ON drs.group_id = ars.group_id AND drs.replica_id = ars.replica_id
OUTER APPLY (SELECT TOP 1 quorum_state_desc FROM sys.dm_hadr_cluster) AS hc
ORDER BY ag.name, DB_NAME(drs.database_id), ar.replica_server_name;';

EXEC sys.sp_executesql @sql;
"""


class _ConnectionFactoryProtocol(Protocol):
    def create_connection(self, instance: Instance) -> SyncConnection | None: ...


class ClusterStatusSyncService:
    """检测 MySQL 主从状态与 SQL Server AG 数据库同步健康状态."""

    def __init__(self, *, connection_factory: _ConnectionFactoryProtocol | None = None) -> None:
        self._connection_factory = connection_factory or ConnectionFactory

    def sync_mysql_cluster(self, cluster_id: int) -> dict[str, Any]:
        return MySQLClusterManagementService(connection_factory=self._connection_factory).sync_topology(cluster_id)

    def sync_sqlserver_cluster(self, cluster_id: int) -> dict[str, Any]:
        prepared = self._prepare_sqlserver_cluster(cluster_id)
        if isinstance(prepared, dict):
            return prepared
        cluster, bindings, ags = prepared

        rows, source_instance_ids, source_errors = self._collect_sqlserver_status_rows(cluster, bindings)
        if not source_instance_ids:
            error_message = "; ".join(source_errors) if source_errors else "已绑定实例均无法读取 SQL Server AG 状态"
            return self._mark_sqlserver_cluster_result(cluster, [], status="failed", error_message=error_message)

        known_ag = {ag.name: ag for ag in ags}
        known_rows = [row for row in rows if self._value(row, "ag_name", 0) in known_ag]
        replica_states_by_scope = {
            (state.ag_name, state.replica_server_name): state
            for state in (self._upsert_sqlserver_replica_state(cluster, known_ag, row) for row in known_rows)
        }
        replica_states = list(replica_states_by_scope.values())
        states = [self._upsert_sqlserver_state(cluster, known_ag, row) for row in known_rows]
        self._apply_sqlserver_cluster_status(
            cluster,
            status="completed",
            error_message="; ".join(source_errors) if source_errors else None,
        )
        db.session.flush()
        abnormal_database_count = len({(state.ag_name, state.database_name) for state in states if state.is_abnormal})
        abnormal_replica_count = len({state.replica_server_name for state in replica_states if state.is_abnormal})
        log_info(
            "检测 SQL Server AG 数据库同步状态",
            module="cluster_status_sync",
            cluster_id=cluster.id,
            cluster_name=cluster.name,
            abnormal_database_count=abnormal_database_count,
            abnormal_replica_count=abnormal_replica_count,
        )
        return {
            "cluster_id": cluster.id,
            "status": "completed",
            "source_instance_id": source_instance_ids[0],
            "source_instance_ids": source_instance_ids,
            "source_errors": source_errors,
            "items_total": len(states),
            "abnormal_database_count": abnormal_database_count,
            "abnormal_replica_count": abnormal_replica_count,
            "items": [state.to_dict() for state in states],
            "replicas": [state.to_dict() for state in sorted(replica_states, key=lambda item: item.replica_server_name)],
        }

    def _collect_sqlserver_status_rows(
        self,
        cluster: SQLServerCluster,
        bindings: list[SQLServerClusterInstance],
    ) -> tuple[list[Any], list[int], list[str]]:
        rows: list[Any] = []
        source_instance_ids: list[int] = []
        source_errors: list[str] = []
        for binding in bindings:
            source_instance = cast(Instance | None, binding.instance)
            if source_instance is None:
                source_errors.append(f"binding:{binding.id} 绑定实例不存在")
                continue
            target = self._build_sqlserver_status_target(source_instance)
            connection = self._connection_factory.create_connection(target)
            if connection is None:
                source_errors.append(f"{source_instance.name} 无法创建 SQL Server 连接")
                continue
            try:
                if not connection.connect():
                    source_errors.append(f"{source_instance.name} 无法连接 SQL Server 实例")
                    continue
                rows.extend(list(connection.execute_query(_AG_DATABASE_SYNC_STATUS_QUERY)))
                source_instance_ids.append(source_instance.id)
            except (RuntimeError, ValueError, LookupError, ConnectionError, TimeoutError, OSError) as exc:
                source_errors.append(f"{source_instance.name} {exc}")
            finally:
                connection.disconnect()
        if source_errors:
            log_info(
                "检测 SQL Server AG 数据库同步状态存在部分实例失败",
                module="cluster_status_sync",
                cluster_id=cluster.id,
                cluster_name=cluster.name,
                source_errors=source_errors,
            )
        return rows, source_instance_ids, source_errors

    def _prepare_sqlserver_cluster(
        self,
        cluster_id: int,
    ) -> tuple[SQLServerCluster, list[SQLServerClusterInstance], list[SQLServerAvailabilityGroup]] | dict[str, Any]:
        cluster = cast(SQLServerCluster | None, SQLServerCluster.query.get(cluster_id))
        if cluster is None:
            return {"cluster_id": cluster_id, "status": "failed", "error_message": "SQL Server 群集不存在"}
        bindings = (
            SQLServerClusterInstance.query.filter(SQLServerClusterInstance.cluster_id == cluster.id)
            .order_by(SQLServerClusterInstance.created_at.asc())
            .all()
        )
        ags = (
            SQLServerAvailabilityGroup.query.filter(SQLServerAvailabilityGroup.cluster_id == cluster.id)
            .order_by(SQLServerAvailabilityGroup.name.asc())
            .all()
        )
        if not bindings:
            return self._mark_sqlserver_cluster_result(cluster, [], status="failed", error_message="请先绑定 SQL Server 实例")
        if not ags:
            return self._mark_sqlserver_cluster_result(cluster, [], status="completed", error_message=None)
        return cluster, bindings, ags

    @staticmethod
    def list_enabled_mysql_clusters() -> list[MySQLCluster]:
        return (
            MySQLCluster.query.filter(MySQLCluster.is_enabled.is_(True))
            .order_by(MySQLCluster.id.asc())
            .all()
        )

    @staticmethod
    def list_enabled_sqlserver_clusters() -> list[SQLServerCluster]:
        return (
            SQLServerCluster.query.filter(SQLServerCluster.is_enabled.is_(True))
            .order_by(SQLServerCluster.id.asc())
            .all()
        )

    @staticmethod
    def _mark_sqlserver_cluster_result(
        cluster: SQLServerCluster,
        states: list[SQLServerAgDatabaseSyncState],
        *,
        status: str,
        error_message: str | None,
    ) -> dict[str, Any]:
        ClusterStatusSyncService._apply_sqlserver_cluster_status(cluster, status=status, error_message=error_message)
        db.session.flush()
        abnormal_database_count = len({(state.ag_name, state.database_name) for state in states if state.is_abnormal})
        abnormal_replica_count = len({state.replica_server_name for state in states if state.is_abnormal})
        log_info(
            "检测 SQL Server AG 数据库同步状态",
            module="cluster_status_sync",
            cluster_id=cluster.id,
            cluster_name=cluster.name,
            status=status,
            error=error_message,
        )
        return {
            "cluster_id": cluster.id,
            "status": status,
            "error_message": error_message,
            "items_total": len(states),
            "abnormal_database_count": abnormal_database_count,
            "abnormal_replica_count": abnormal_replica_count,
            "items": [state.to_dict() for state in states],
        }

    @staticmethod
    def _apply_sqlserver_cluster_status(
        cluster: SQLServerCluster,
        *,
        status: str,
        error_message: str | None,
    ) -> None:
        cluster.last_status_sync_at = time_utils.now()
        cluster.last_status_sync_status = status
        cluster.last_status_sync_error = error_message
        db.session.add(cluster)

    @staticmethod
    def _build_sqlserver_status_target(instance: Instance) -> Instance:
        return cast(
            Instance,
            SimpleNamespace(
                id=instance.id,
                name=f"{instance.name}/ag-status",
                db_type=DatabaseType.SQLSERVER,
                host=instance.host,
                port=instance.port,
                database_name="master",
                credential_id=instance.credential_id,
                credential=instance.credential,
                is_active=True,
            ),
        )

    def _upsert_sqlserver_state(
        self,
        cluster: SQLServerCluster,
        known_ag: Mapping[str, SQLServerAvailabilityGroup],
        row: Any,
    ) -> SQLServerAgDatabaseSyncState:
        ag_name = str(self._value(row, "ag_name", 0) or "").strip()
        database_name = str(self._value(row, "database_name", 1) or "").strip()
        replica_server_name = str(self._value(row, "replica_server_name", 2) or "").strip()
        state = SQLServerAgDatabaseSyncState.query.filter_by(
            cluster_id=cluster.id,
            ag_name=ag_name,
            database_name=database_name,
            replica_server_name=replica_server_name,
        ).first()
        if state is None:
            state = SQLServerAgDatabaseSyncState()
            state.cluster_id = cluster.id
            state.ag_name = ag_name
            state.database_name = database_name
            state.replica_server_name = replica_server_name
        ag = known_ag.get(ag_name)
        state.availability_group_id = ag.id if ag else None
        state.synchronization_state_desc = self._text_value(row, "synchronization_state_desc", 3)
        state.synchronization_health_desc = self._text_value(row, "synchronization_health_desc", 4)
        state.database_state_desc = self._text_value(row, "database_state_desc", 5)
        state.is_suspended = self._as_bool(self._value(row, "is_suspended", 6))
        state.suspend_reason_desc = self._text_value(row, "suspend_reason_desc", 7)
        state.log_send_queue_size = self._int_value(row, "log_send_queue_size", 8)
        state.redo_queue_size = self._int_value(row, "redo_queue_size", 9)
        state.is_abnormal, state.error_summary = self._judge_sqlserver_state(state)
        state.last_checked_at = time_utils.now()
        db.session.add(state)
        return state

    def _upsert_sqlserver_replica_state(
        self,
        cluster: SQLServerCluster,
        known_ag: Mapping[str, SQLServerAvailabilityGroup],
        row: Any,
    ) -> SQLServerAgReplicaSyncState:
        ag_name = str(self._value(row, "ag_name", 0) or "").strip()
        replica_server_name = str(self._value(row, "replica_server_name", 2) or "").strip()
        state = SQLServerAgReplicaSyncState.query.filter_by(
            cluster_id=cluster.id,
            ag_name=ag_name,
            replica_server_name=replica_server_name,
        ).first()
        if state is None:
            state = SQLServerAgReplicaSyncState()
            state.cluster_id = cluster.id
            state.ag_name = ag_name
            state.replica_server_name = replica_server_name
        ag = known_ag.get(ag_name)
        state.availability_group_id = ag.id if ag else None
        state.role_desc = self._text_value(row, "replica_role_desc", 10)
        state.availability_mode_desc = self._text_value(row, "availability_mode_desc", 11)
        state.failover_mode_desc = self._text_value(row, "failover_mode_desc", 12)
        state.seeding_mode_desc = self._text_value(row, "seeding_mode_desc", 13)
        state.synchronization_health_desc = self._text_value(row, "replica_synchronization_health_desc", 14)
        state.connected_state_desc = self._text_value(row, "connected_state_desc", 15)
        state.operational_state_desc = self._text_value(row, "operational_state_desc", 16)
        state.recovery_health_desc = self._text_value(row, "recovery_health_desc", 17)
        state.cluster_state_desc = self._text_value(row, "cluster_state_desc", 18)
        state.cluster_type_desc = self._text_value(row, "cluster_type_desc", 19)
        state.is_primary = (state.role_desc or "").upper() == "PRIMARY"
        state.is_abnormal, state.error_summary = self._judge_sqlserver_replica_state(state)
        state.last_checked_at = time_utils.now()
        db.session.add(state)
        return state

    @staticmethod
    def _judge_sqlserver_state(state: SQLServerAgDatabaseSyncState) -> tuple[bool, str | None]:
        reasons: list[str] = []
        health = (state.synchronization_health_desc or "").upper()
        sync_state = (state.synchronization_state_desc or "").upper()
        database_state = (state.database_state_desc or "").upper()
        if health and health != "HEALTHY":
            reasons.append(f"health={health}")
        if sync_state and sync_state not in {"SYNCHRONIZED", "SYNCHRONIZING"}:
            reasons.append(f"sync_state={sync_state}")
        if database_state and database_state != "ONLINE":
            reasons.append(f"database_state={database_state}")
        if state.is_suspended:
            suffix = f":{state.suspend_reason_desc}" if state.suspend_reason_desc else ""
            reasons.append(f"suspended{suffix}")
        return bool(reasons), "; ".join(reasons) if reasons else None

    @staticmethod
    def _judge_sqlserver_replica_state(state: SQLServerAgReplicaSyncState) -> tuple[bool, str | None]:
        reasons: list[str] = []
        health = (state.synchronization_health_desc or "").upper()
        connected = (state.connected_state_desc or "").upper()
        operational = (state.operational_state_desc or "").upper()
        recovery = (state.recovery_health_desc or "").upper()
        if health and health != "HEALTHY":
            reasons.append(f"health={health}")
        if connected and connected != "CONNECTED":
            reasons.append(f"connected={connected}")
        if operational and operational not in {"ONLINE", "PENDING_FAILOVER"}:
            reasons.append(f"operational={operational}")
        if recovery and recovery != "ONLINE":
            reasons.append(f"recovery={recovery}")
        return bool(reasons), "; ".join(reasons) if reasons else None

    @staticmethod
    def _value(row: Any, key: str, index: int) -> Any:
        if isinstance(row, Mapping):
            return row.get(key)
        if isinstance(row, Sequence) and not isinstance(row, str):
            values = list(row)
            return values[index] if index < len(values) else None
        return None

    def _text_value(self, row: Any, key: str, index: int) -> str | None:
        value = self._value(row, key, index)
        return str(value).strip() if value not in {None, ""} else None

    def _int_value(self, row: Any, key: str, index: int) -> int | None:
        value = self._value(row, key, index)
        return int(value) if value not in {None, ""} else None

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
