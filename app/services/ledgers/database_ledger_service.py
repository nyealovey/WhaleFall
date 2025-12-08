"""
数据库台账服务。

负责为数据库台账页面提供列表数据、容量走势等复用接口。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any
from collections.abc import Iterable

from sqlalchemy import and_, func, or_

from app import db
from app.constants import SyncStatus
from app.errors import NotFoundError, SystemError
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.models.tag import Tag, instance_tags
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils


class DatabaseLedgerService:
    """数据库台账查询服务。"""

    DEFAULT_PAGINATION = 20
    DEFAULT_TREND_DAYS = 30
    MAX_TREND_DAYS = 90

    def __init__(self, *, session: Any | None = None) -> None:
        """初始化服务。

        Args:
            session: 可选的 SQLAlchemy 会话，默认使用全局 db.session。

        """
        self.session = session or db.session

    def get_ledger(
        self,
        *,
        search: str = "",
        db_type: str | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        per_page: int | None = None,
    ) -> dict[str, Any]:
        """获取数据库台账分页数据。

        Args:
            search: 关键字，支持数据库名称、实例名称、主机模糊匹配。
            db_type: 数据库类型，传入 all/空表示不过滤。
            page: 页码，起始为 1。
            per_page: 每页数量，默认 `DEFAULT_PAGINATION`。

        Returns:
            包含 items/total/page/per_page 的字典。

        """
        try:
            per_page = per_page or self.DEFAULT_PAGINATION
            base_query = self._apply_filters(
                self._base_query(),
                search=search,
                db_type=db_type,
                tags=tags,
            )
            total = base_query.count()

            items = (
                self._with_latest_stats(base_query)
                .order_by(Instance.name.asc(), InstanceDatabase.database_name.asc())
                .offset(max(page - 1, 0) * per_page)
                .limit(per_page)
                .all()
            )
            instance_ids = [instance.id for _, instance, _, _ in items if instance]
            tags_map = self._fetch_instance_tags(instance_ids)

            rows = [
                self._serialize_row(
                    record,
                    instance,
                    collected_at,
                    size_mb,
                    tags_map.get(instance.id if instance else None, []),
                )
                for record, instance, collected_at, size_mb in items
            ]

            return {
                "items": rows,
                "total": total,
                "page": page,
                "per_page": per_page,
            }
        except Exception as exc:
            log_error(
                "获取数据库台账失败",
                module="ledgers_database_service",
                error=str(exc),
                exc_info=True,
            )
            raise SystemError("获取数据库台账失败") from exc

    def iterate_all(
        self,
        *,
        search: str = "",
        db_type: str | None = None,
        tags: list[str] | None = None,
    ) -> Iterable[dict[str, Any]]:
        """遍历所有台账记录（用于导出）。

        Args:
            search: 搜索关键字。
            db_type: 数据库类型筛选。

        Yields:
            LedgerItem: 结构化的台账项。

        """
        try:
            query = (
                self._with_latest_stats(
                    self._apply_filters(self._base_query(), search=search, db_type=db_type, tags=tags),
                )
                .order_by(Instance.name.asc(), InstanceDatabase.database_name.asc())
            )
            results = query.all()
            instance_ids = [instance.id for _, instance, _, _ in results if instance]
            tags_map = self._fetch_instance_tags(instance_ids)
            for record, instance, collected_at, size_mb in results:
                yield self._serialize_row(
                    record,
                    instance,
                    collected_at,
                    size_mb,
                    tags_map.get(instance.id if instance else None, []),
                )
        except Exception as exc:
            log_error(
                "遍历数据库台账失败",
                module="ledgers_database_service",
                error=str(exc),
                exc_info=True,
            )
            raise SystemError("导出数据库台账失败") from exc

    def get_capacity_trend(self, database_id: int, *, days: int | None = None) -> dict[str, Any]:
        """获取指定数据库最近 N 天的容量走势。

        Args:
            database_id: InstanceDatabase 主键。
            days: 查询天数，默认 30 天，最大 90 天。

        Returns:
            包含 database 元数据与 points 列表的字典。

        Raises:
            NotFoundError: 当数据库不存在时抛出。

        """
        days = days or self.DEFAULT_TREND_DAYS
        days = max(1, min(days, self.MAX_TREND_DAYS))

        record = InstanceDatabase.query.get(database_id)
        if record is None:
            raise NotFoundError("数据库不存在或已删除")

        instance = Instance.query.get(record.instance_id)
        if instance is None:
            raise NotFoundError("数据库所属实例不存在")

        since_date = time_utils.now().date() - timedelta(days=days - 1)
        stats = (
            DatabaseSizeStat.query.filter(
                DatabaseSizeStat.instance_id == record.instance_id,
                DatabaseSizeStat.database_name == record.database_name,
                DatabaseSizeStat.collected_date >= since_date,
            )
            .order_by(DatabaseSizeStat.collected_at.asc())
            .all()
        )

        points = [
            {
                "collected_at": stat.collected_at.isoformat() if stat.collected_at else None,
                "collected_date": stat.collected_date.isoformat() if stat.collected_date else None,
                "size_mb": int(stat.size_mb) if stat.size_mb is not None else None,
                "size_bytes": self._to_bytes(stat.size_mb),
                "label": self._format_size(stat.size_mb),
            }
            for stat in stats
        ]

        return {
            "database": {
                "id": record.id,
                "name": record.database_name,
                "instance_id": record.instance_id,
                "instance_name": instance.name if instance else "",
                "db_type": instance.db_type if instance else "",
            },
            "points": points,
        }

    def _base_query(self):
        """构造基础查询。"""
        return (
            self.session.query(InstanceDatabase)
            .join(Instance, InstanceDatabase.instance_id == Instance.id)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceDatabase.is_active.is_(True),
            )
        )

    def _apply_filters(
        self,
        query,
        *,
        search: str = "",
        db_type: str | None = None,
        tags: list[str] | None = None,
    ):
        """在基础查询上叠加筛选条件。"""
        normalized_type = (db_type or "").strip().lower()
        if normalized_type and normalized_type != "all":
            query = query.filter(Instance.db_type == normalized_type)

        normalized_search = (search or "").strip()
        if normalized_search:
            like_pattern = f"%{normalized_search}%"
            query = query.filter(
                or_(
                    InstanceDatabase.database_name.ilike(like_pattern),
                    Instance.name.ilike(like_pattern),
                    Instance.host.ilike(like_pattern),
                )
            )

        normalized_tags = [tag.strip() for tag in (tags or []) if tag.strip()]
        if normalized_tags:
            query = (
                query.join(instance_tags, Instance.id == instance_tags.c.instance_id)
                .join(Tag, Tag.id == instance_tags.c.tag_id)
                .filter(Tag.name.in_(normalized_tags), Tag.is_active.is_(True))
                .distinct()
            )
        return query

    def _with_latest_stats(self, query):
        """为查询附加最新容量信息。"""
        latest_stats = (
            self.session.query(
                DatabaseSizeStat.instance_id.label("instance_id"),
                DatabaseSizeStat.database_name.label("database_name"),
                func.max(DatabaseSizeStat.collected_at).label("latest_collected_at"),
            )
            .group_by(DatabaseSizeStat.instance_id, DatabaseSizeStat.database_name)
            .subquery()
        )

        return (
            query.outerjoin(
                latest_stats,
                and_(
                    InstanceDatabase.instance_id == latest_stats.c.instance_id,
                    InstanceDatabase.database_name == latest_stats.c.database_name,
                ),
            )
            .outerjoin(
                DatabaseSizeStat,
                and_(
                    DatabaseSizeStat.instance_id == latest_stats.c.instance_id,
                    DatabaseSizeStat.database_name == latest_stats.c.database_name,
                    DatabaseSizeStat.collected_at == latest_stats.c.latest_collected_at,
                ),
            )
            .with_entities(
                InstanceDatabase,
                Instance,
                latest_stats.c.latest_collected_at,
                DatabaseSizeStat.size_mb,
            )
        )

    def _serialize_row(
        self,
        record: InstanceDatabase,
        instance: Instance,
        collected_at,
        size_mb,
        tags: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """将数据库记录转换为序列化结构。"""
        size_mb_value = int(size_mb) if size_mb is not None else None
        status_payload = self._resolve_sync_status(collected_at)
        capacity_payload = {
            "size_mb": size_mb_value,
            "size_bytes": self._to_bytes(size_mb_value),
            "label": self._format_size(size_mb_value),
            "collected_at": collected_at.isoformat() if collected_at else None,
        }

        instance_payload = {
            "id": instance.id if instance else None,
            "name": instance.name if instance else "",
            "host": instance.host if instance else "",
            "db_type": instance.db_type if instance else "",
        }

        return {
            "id": record.id,
            "database_name": record.database_name,
            "instance": instance_payload,
            "db_type": instance_payload["db_type"],
            "capacity": capacity_payload,
            "sync_status": status_payload,
            "tags": tags or [],
        }

    def _fetch_instance_tags(self, instance_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
        """根据实例 ID 批量获取标签列表。"""
        normalized_ids = [instance_id for instance_id in instance_ids if instance_id]
        if not normalized_ids:
            return {}
        rows = (
            self.session.query(
                instance_tags.c.instance_id,
                Tag.name,
                Tag.display_name,
                Tag.color,
            )
            .join(Tag, Tag.id == instance_tags.c.tag_id)
            .filter(
                instance_tags.c.instance_id.in_(normalized_ids),
                Tag.is_active.is_(True),
            )
            .order_by(Tag.display_name.asc())
            .all()
        )
        mapping: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for instance_id, name, display_name, color in rows:
            mapping[instance_id].append(
                {
                    "name": name,
                    "display_name": display_name,
                    "color": color or "secondary",
                }
            )
        return mapping

    def _resolve_sync_status(self, collected_at) -> dict[str, str]:
        """根据采集时间生成同步状态。"""
        if not collected_at:
            return {"value": SyncStatus.PENDING, "label": "待采集", "variant": "secondary"}

        now = time_utils.now()
        delay_hours = (now - collected_at).total_seconds() / 3600

        if delay_hours <= 6:
            return {"value": SyncStatus.COMPLETED, "label": "已更新", "variant": "success"}
        if delay_hours <= 48:
            return {"value": SyncStatus.RUNNING, "label": "待刷新", "variant": "warning"}
        return {"value": SyncStatus.FAILED, "label": "超时", "variant": "danger"}

    def _format_size(self, size_mb: int | None) -> str:
        """将大小（MB）格式化为易读文本。"""
        if size_mb is None:
            return "未采集"
        if size_mb >= 1024:
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        return f"{size_mb:.0f} MB"

    @staticmethod
    def _to_bytes(size_mb: int | None) -> int | None:
        """将 MB 转换为字节。"""
        if size_mb is None:
            return None
        return int(size_mb) * 1024 * 1024
