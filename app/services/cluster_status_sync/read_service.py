"""SQL Server AG 数据库同步状态读取服务."""

from __future__ import annotations

from collections import defaultdict
from math import ceil
from typing import Any, cast

from app.core.exceptions import NotFoundError
from app.models.sqlserver_ag_sync_state import SQLServerAgDatabaseSyncState, SQLServerAgReplicaSyncState
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster
from app.schemas.sqlserver_clusters import SQLServerDatabaseSyncStatesQuery


class SQLServerAgDatabaseSyncStatesReadService:
    """按数据库聚合展示 SQL Server AG 同步健康结果."""

    def list_states(self, query: SQLServerDatabaseSyncStatesQuery) -> dict[str, Any]:
        rows = self._load_rows(query)
        grouped = [self._serialize_group(group_rows) for group_rows in self._group_rows(rows).values()]
        grouped.sort(
            key=lambda item: (
                0 if item["status"] == "abnormal" else 1,
                str(item["cluster_name"]),
                str(item["ag_name"]),
                str(item["database_name"]),
            ),
        )
        kpis = self._build_kpis(grouped)
        filtered = self._apply_status_filter(grouped, query.status)
        total = len(filtered)
        start = (query.page - 1) * query.limit
        items = filtered[start : start + query.limit]
        return {
            "items": items,
            "total": total,
            "page": query.page,
            "pages": ceil(total / query.limit) if total else 0,
            "limit": query.limit,
            "kpis": kpis,
        }

    def get_ag_dashboard(self, cluster_id: int, ag_id: int) -> dict[str, Any]:
        cluster = cast(SQLServerCluster | None, SQLServerCluster.query.get(cluster_id))
        if cluster is None:
            raise NotFoundError("SQL Server 群集不存在", extra={"cluster_id": cluster_id})
        ag = cast(
            SQLServerAvailabilityGroup | None,
            SQLServerAvailabilityGroup.query.filter_by(id=ag_id, cluster_id=cluster_id).first(),
        )
        if ag is None:
            raise NotFoundError("AG 不存在", extra={"cluster_id": cluster_id, "availability_group_id": ag_id})

        replicas = self._load_ag_replicas(cluster_id, ag)
        database_rows = self._load_ag_database_rows(cluster_id, ag)
        database_groups = self._group_database_rows_by_replica(database_rows)
        database_items = list(self._group_rows(database_rows).values())
        abnormal_database_count = sum(1 for rows in database_items if any(row.is_abnormal for row in rows))
        abnormal_replicas = [row for row in replicas if row.is_abnormal]
        affected_replicas = {row.replica_server_name for row in database_rows if row.is_abnormal}
        if not affected_replicas:
            affected_replicas = {row.replica_server_name for row in abnormal_replicas}
        latest = self._latest_checked_at(replicas, database_rows)
        primary_replica = next((row.replica_server_name for row in replicas if row.is_primary), None)
        first_replica = replicas[0] if replicas else None

        return {
            "summary": {
                "cluster_id": cluster.id,
                "cluster_name": cluster.name,
                "cluster_status": first_replica.cluster_state_desc if first_replica else None,
                "cluster_type": first_replica.cluster_type_desc if first_replica else None,
                "last_status_sync_status": cluster.last_status_sync_status,
                "last_status_sync_error": cluster.last_status_sync_error,
                "availability_group_id": ag.id,
                "ag_name": ag.name,
                "listener_name": ag.listener_name,
                "listener_host": ag.listener_host,
                "listener_port": ag.listener_port,
                "primary_replica": primary_replica,
                "status": self._resolve_ag_status(cluster, abnormal_database_count, len(abnormal_replicas)),
                "last_checked_at": latest.isoformat() if latest else None,
            },
            "replicas": [self._serialize_replica(row) for row in replicas],
            "database_groups": database_groups,
            "kpis": {
                "total_databases": len(database_items),
                "abnormal_databases": abnormal_database_count,
                "normal_databases": len(database_items) - abnormal_database_count,
                "replica_count": len(replicas),
                "affected_replicas": len(affected_replicas),
            },
        }

    @staticmethod
    def list_cluster_options() -> list[dict[str, Any]]:
        clusters = SQLServerCluster.query.order_by(SQLServerCluster.name.asc()).all()
        return [{"id": cluster.id, "name": cluster.name} for cluster in clusters]

    @staticmethod
    def list_ag_options(cluster_id: int | None = None) -> list[dict[str, Any]]:
        query = SQLServerAvailabilityGroup.query
        if cluster_id is not None:
            query = query.filter(SQLServerAvailabilityGroup.cluster_id == cluster_id)
        ags = query.order_by(SQLServerAvailabilityGroup.name.asc()).all()
        return [{"cluster_id": ag.cluster_id, "name": ag.name} for ag in ags]

    def _load_rows(self, query: SQLServerDatabaseSyncStatesQuery) -> list[SQLServerAgDatabaseSyncState]:
        orm_query = SQLServerAgDatabaseSyncState.query.join(SQLServerCluster)
        if query.cluster_id is not None:
            orm_query = orm_query.filter(SQLServerAgDatabaseSyncState.cluster_id == query.cluster_id)
        if query.ag_name:
            orm_query = orm_query.filter(SQLServerAgDatabaseSyncState.ag_name == query.ag_name)
        rows = orm_query.order_by(
            SQLServerAgDatabaseSyncState.cluster_id.asc(),
            SQLServerAgDatabaseSyncState.ag_name.asc(),
            SQLServerAgDatabaseSyncState.database_name.asc(),
            SQLServerAgDatabaseSyncState.replica_server_name.asc(),
        ).all()
        if not query.search:
            return rows
        needle = query.search.lower()
        return [row for row in rows if self._matches_search(row, needle)]

    @staticmethod
    def _load_ag_replicas(cluster_id: int, ag: SQLServerAvailabilityGroup) -> list[SQLServerAgReplicaSyncState]:
        return (
            SQLServerAgReplicaSyncState.query.filter(
                SQLServerAgReplicaSyncState.cluster_id == cluster_id,
                SQLServerAgReplicaSyncState.ag_name == ag.name,
            )
            .order_by(SQLServerAgReplicaSyncState.is_primary.desc(), SQLServerAgReplicaSyncState.replica_server_name.asc())
            .all()
        )

    @staticmethod
    def _load_ag_database_rows(cluster_id: int, ag: SQLServerAvailabilityGroup) -> list[SQLServerAgDatabaseSyncState]:
        return (
            SQLServerAgDatabaseSyncState.query.filter(
                SQLServerAgDatabaseSyncState.cluster_id == cluster_id,
                SQLServerAgDatabaseSyncState.ag_name == ag.name,
            )
            .order_by(
                SQLServerAgDatabaseSyncState.replica_server_name.asc(),
                SQLServerAgDatabaseSyncState.database_name.asc(),
            )
            .all()
        )

    @staticmethod
    def _matches_search(row: SQLServerAgDatabaseSyncState, needle: str) -> bool:
        cluster = cast(SQLServerCluster | None, row.cluster)
        haystacks = (
            cluster.name if cluster else "",
            row.ag_name,
            row.database_name,
            row.replica_server_name,
            row.error_summary or "",
        )
        return any(needle in str(value).lower() for value in haystacks)

    @staticmethod
    def _group_rows(
        rows: list[SQLServerAgDatabaseSyncState],
    ) -> dict[tuple[int, str, str], list[SQLServerAgDatabaseSyncState]]:
        groups: dict[tuple[int, str, str], list[SQLServerAgDatabaseSyncState]] = defaultdict(list)
        for row in rows:
            groups[(int(row.cluster_id), row.ag_name, row.database_name)].append(row)
        return groups

    @staticmethod
    def _serialize_group(rows: list[SQLServerAgDatabaseSyncState]) -> dict[str, Any]:
        first = rows[0]
        cluster = cast(SQLServerCluster | None, first.cluster)
        abnormal_rows = [row for row in rows if row.is_abnormal]
        latest = max((row.last_checked_at for row in rows if row.last_checked_at is not None), default=None)
        log_send_values = [int(row.log_send_queue_size) for row in rows if row.log_send_queue_size is not None]
        redo_values = [int(row.redo_queue_size) for row in rows if row.redo_queue_size is not None]
        error_summaries = [row.error_summary for row in abnormal_rows if row.error_summary]
        abnormal_replica_names = sorted({row.replica_server_name for row in abnormal_rows})
        replica_names = sorted({row.replica_server_name for row in rows})
        return {
            "cluster_id": first.cluster_id,
            "cluster_name": cluster.name if cluster else "",
            "ag_name": first.ag_name,
            "database_name": first.database_name,
            "status": "abnormal" if abnormal_rows else "normal",
            "replica_count": len(replica_names),
            "replica_names": replica_names,
            "abnormal_replica_count": len(abnormal_replica_names),
            "abnormal_replica_names": abnormal_replica_names,
            "max_log_send_queue_size": max(log_send_values) if log_send_values else None,
            "max_redo_queue_size": max(redo_values) if redo_values else None,
            "error_summary": "; ".join(dict.fromkeys(error_summaries)),
            "last_checked_at": latest.isoformat() if latest else None,
        }

    @staticmethod
    def _serialize_replica(row: SQLServerAgReplicaSyncState) -> dict[str, Any]:
        return {
            "replica_server_name": row.replica_server_name,
            "role_desc": row.role_desc,
            "availability_mode_desc": row.availability_mode_desc,
            "failover_mode_desc": row.failover_mode_desc,
            "seeding_mode_desc": row.seeding_mode_desc,
            "synchronization_health_desc": row.synchronization_health_desc,
            "connected_state_desc": row.connected_state_desc,
            "operational_state_desc": row.operational_state_desc,
            "recovery_health_desc": row.recovery_health_desc,
            "is_primary": bool(row.is_primary),
            "status": "abnormal" if row.is_abnormal else "normal",
            "error_summary": row.error_summary,
            "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
        }

    def _group_database_rows_by_replica(self, rows: list[SQLServerAgDatabaseSyncState]) -> list[dict[str, Any]]:
        grouped: dict[str, list[SQLServerAgDatabaseSyncState]] = defaultdict(list)
        for row in rows:
            grouped[row.replica_server_name].append(row)
        return [
            {
                "replica_server_name": replica_name,
                "status": "abnormal" if any(row.is_abnormal for row in replica_rows) else "normal",
                "databases": [self._serialize_database_row(row) for row in replica_rows],
            }
            for replica_name, replica_rows in sorted(grouped.items(), key=lambda item: item[0])
        ]

    @staticmethod
    def _serialize_database_row(row: SQLServerAgDatabaseSyncState) -> dict[str, Any]:
        failover_ready = (row.synchronization_state_desc or "").upper() == "SYNCHRONIZED" and not row.is_suspended
        return {
            "database_name": row.database_name,
            "replica_server_name": row.replica_server_name,
            "synchronization_state_desc": row.synchronization_state_desc,
            "synchronization_health_desc": row.synchronization_health_desc,
            "database_state_desc": row.database_state_desc,
            "is_suspended": bool(row.is_suspended),
            "suspend_reason_desc": row.suspend_reason_desc,
            "failover_ready": failover_ready,
            "log_send_queue_size": row.log_send_queue_size,
            "redo_queue_size": row.redo_queue_size,
            "status": "abnormal" if row.is_abnormal else "normal",
            "error_summary": row.error_summary,
            "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
        }

    @staticmethod
    def _latest_checked_at(
        replicas: list[SQLServerAgReplicaSyncState],
        database_rows: list[SQLServerAgDatabaseSyncState],
    ):
        return max(
            (
                row.last_checked_at
                for row in [*replicas, *database_rows]
                if row.last_checked_at is not None
            ),
            default=None,
        )

    @staticmethod
    def _build_kpis(items: list[dict[str, Any]]) -> dict[str, int]:
        abnormal_items = [item for item in items if item["status"] == "abnormal"]
        return {
            "total_databases": len(items),
            "abnormal_databases": len(abnormal_items),
            "normal_databases": len(items) - len(abnormal_items),
            "affected_replicas": len(
                {
                    replica_name
                    for item in abnormal_items
                    for replica_name in cast(list[str], item["abnormal_replica_names"])
                },
            ),
        }

    @staticmethod
    def _apply_status_filter(items: list[dict[str, Any]], status: str) -> list[dict[str, Any]]:
        if status in {"normal", "abnormal"}:
            return [item for item in items if item["status"] == status]
        return items

    @staticmethod
    def _resolve_ag_status(cluster: SQLServerCluster, abnormal_database_count: int, abnormal_replica_count: int) -> str:
        if cluster.last_status_sync_status == "failed":
            return "failed"
        if cluster.last_status_sync_status != "completed":
            return "not_checked"
        return "abnormal" if abnormal_database_count or abnormal_replica_count else "normal"
