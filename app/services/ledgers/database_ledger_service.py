"""数据库台账服务.

负责为数据库台账页面提供列表数据、容量走势等复用接口.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from app import db
from app.constants import SyncStatus
from app.errors import NotFoundError, SystemError
from app.repositories.ledgers.database_ledger_repository import DatabaseLedgerRepository
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.types.ledgers import (
    DatabaseLedgerCapacitySummary,
    DatabaseLedgerFilters,
    DatabaseLedgerInstanceSummary,
    DatabaseLedgerItem,
    DatabaseLedgerSyncStatusSummary,
)
from app.types.listing import PaginatedResult
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils

RECENT_SYNC_THRESHOLD_HOURS = 6
STALE_SYNC_THRESHOLD_HOURS = 48
MB_PER_GB = 1024
BYTES_PER_MB = 1024 * 1024

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.orm import Session


class DatabaseLedgerService:
    """数据库台账查询服务."""

    DEFAULT_PAGINATION = 20
    DEFAULT_TREND_DAYS = 30
    MAX_TREND_DAYS = 90

    def __init__(self, *, session: Session | None = None) -> None:
        """初始化服务.

        Args:
            session: 可选的 SQLAlchemy 会话,默认使用全局 db.session.

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
    ) -> PaginatedResult[DatabaseLedgerItem]:
        """获取数据库台账分页数据.

        Args:
            search: 关键字,支持数据库名称、实例名称、主机模糊匹配.
            db_type: 数据库类型,传入 all/空表示不过滤.
            tags: 标签 ID 列表,传入时仅返回拥有任一匹配标签的数据库.
            page: 页码,起始为 1.
            per_page: 每页数量,默认 `DEFAULT_PAGINATION`.

        """
        try:
            per_page = per_page or self.DEFAULT_PAGINATION
            filters = DatabaseLedgerFilters(
                search=search.strip(),
                db_type=(db_type or "all"),
                tags=[tag.strip() for tag in (tags or []) if tag.strip()],
                page=page,
                per_page=per_page,
            )
            repository = DatabaseLedgerRepository(session=self.session)
            page_result = repository.list_ledger(filters)
            items = [self._build_item(projection) for projection in page_result.items]
        except Exception as exc:
            log_error(
                "获取数据库台账失败",
                module="ledgers_database_service",
                error=str(exc),
                exc_info=True,
            )
            msg = "获取数据库台账失败"
            raise SystemError(msg) from exc
        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )

    def iterate_all(
        self,
        *,
        search: str = "",
        db_type: str | None = None,
        tags: list[str] | None = None,
    ) -> Iterable[DatabaseLedgerItem]:
        """遍历所有台账记录(用于导出).

        Args:
            search: 搜索关键字.
            db_type: 数据库类型筛选.
            tags: 标签 ID 列表,导出时用于限定数据范围.

        Yields:
            LedgerItem: 结构化的台账项.

        """
        try:
            filters = DatabaseLedgerFilters(
                search=search.strip(),
                db_type=(db_type or "all"),
                tags=[tag.strip() for tag in (tags or []) if tag.strip()],
                page=1,
                per_page=self.DEFAULT_PAGINATION,
            )
            repository = DatabaseLedgerRepository(session=self.session)
            projections = repository.iterate_all(filters)
            for projection in projections:
                yield self._build_item(projection)
        except Exception as exc:
            log_error(
                "遍历数据库台账失败",
                module="ledgers_database_service",
                error=str(exc),
                exc_info=True,
            )
            msg = "导出数据库台账失败"
            raise SystemError(msg) from exc

    def _build_item(self, projection: object) -> DatabaseLedgerItem:
        resolved = cast("Any", projection)
        collected_at = cast("datetime | None", getattr(resolved, "collected_at", None))
        size_mb = cast("int | None", getattr(resolved, "size_mb", None))
        status_payload = self._resolve_sync_status(collected_at)

        capacity_payload = DatabaseLedgerCapacitySummary(
            size_mb=size_mb,
            size_bytes=self._to_bytes(size_mb),
            label=self._format_size(size_mb),
            collected_at=collected_at.isoformat() if collected_at else None,
        )
        instance_payload = DatabaseLedgerInstanceSummary(
            id=cast(int, getattr(resolved, "instance_id", 0)),
            name=cast(str, getattr(resolved, "instance_name", "")),
            host=cast(str, getattr(resolved, "instance_host", "")),
            db_type=cast(str, getattr(resolved, "db_type", "")),
        )
        sync_status_payload = DatabaseLedgerSyncStatusSummary(
            value=status_payload["value"],
            label=status_payload["label"],
            variant=status_payload["variant"],
        )
        return DatabaseLedgerItem(
            id=cast(int, getattr(resolved, "id", 0)),
            database_name=cast(str, getattr(resolved, "database_name", "")),
            instance=instance_payload,
            db_type=instance_payload.db_type,
            capacity=capacity_payload,
            sync_status=sync_status_payload,
            tags=cast("Any", getattr(resolved, "tags", [])),
        )

    def get_capacity_trend(self, database_id: int, *, days: int | None = None) -> dict[str, Any]:
        """获取指定数据库最近 N 天的容量走势.

        Args:
            database_id: InstanceDatabase 主键.
            days: 查询天数,默认 30 天,最大 90 天.

        Returns:
            包含 database 元数据与 points 列表的字典.

        Raises:
            NotFoundError: 当数据库不存在时抛出.

        """
        days = days or self.DEFAULT_TREND_DAYS
        days = max(1, min(days, self.MAX_TREND_DAYS))

        record = InstanceDatabase.query.get(database_id)
        if record is None:
            msg = "数据库不存在或已删除"
            raise NotFoundError(msg)

        instance = Instance.query.get(record.instance_id)
        if instance is None:
            msg = "数据库所属实例不存在"
            raise NotFoundError(msg)

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

    def _resolve_sync_status(self, collected_at: datetime | None) -> dict[str, str]:
        """根据采集时间生成同步状态.

        通过比较当前时间与采集时间的差值,推断同步状态标签.

        Args:
            collected_at: 最新采集时间, ``None`` 表示尚无采集记录.

        Returns:
            dict[str, str]: 包含 ``value``/``label``/``variant`` 的状态描述.

        """
        if not collected_at:
            return {"value": SyncStatus.PENDING, "label": "待采集", "variant": "secondary"}

        now = time_utils.now()
        delay_hours = (now - collected_at).total_seconds() / 3600

        if delay_hours <= RECENT_SYNC_THRESHOLD_HOURS:
            return {"value": SyncStatus.COMPLETED, "label": "已更新", "variant": "success"}
        if delay_hours <= STALE_SYNC_THRESHOLD_HOURS:
            return {"value": SyncStatus.RUNNING, "label": "待刷新", "variant": "warning"}
        return {"value": SyncStatus.FAILED, "label": "超时", "variant": "danger"}

    def _format_size(self, size_mb: int | None) -> str:
        """将大小(MB)格式化为易读文本.

        自动在 MB 与 GB 之间切换单位,提升界面可读性.

        Args:
            size_mb: 以 MB 为单位的容量值, ``None`` 表示未知.

        Returns:
            str: 格式化后的容量显示文本.

        """
        if size_mb is None:
            return "未采集"
        if size_mb >= MB_PER_GB:
            size_gb = size_mb / MB_PER_GB
            return f"{size_gb:.2f} GB"
        return f"{size_mb:.0f} MB"

    @staticmethod
    def _to_bytes(size_mb: int | None) -> int | None:
        """将 MB 转换为字节.

        在需要与字节单位的结构对齐时使用,保持数值精度.

        Args:
            size_mb: 以 MB 为单位的容量; ``None`` 表示未知.

        Returns:
            int | None: 换算后的字节值,或 ``None``.

        """
        if size_mb is None:
            return None
        return int(size_mb) * BYTES_PER_MB
