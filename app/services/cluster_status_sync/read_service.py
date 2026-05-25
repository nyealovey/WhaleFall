"""SQL Server AG 数据库同步状态读取服务."""

from __future__ import annotations

from collections import defaultdict
from math import ceil
from typing import Any, cast

from app.models.sqlserver_ag_sync_state import SQLServerAgDatabaseSyncState
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
