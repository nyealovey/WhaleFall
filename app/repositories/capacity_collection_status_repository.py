"""容量采集状态 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date

from app.models.instance_size_stat import InstanceSizeStat


class CapacityCollectionStatusRepository:
    """容量采集状态读模型 Repository."""

    @staticmethod
    def count_all_stats() -> int:
        """统计全部采集记录数."""
        return int(InstanceSizeStat.query.count() or 0)

    @staticmethod
    def count_stats_since(*, since_date: date) -> int:
        """统计从某日期开始的采集记录数(包含当天)."""
        return int(
            InstanceSizeStat.query.filter(InstanceSizeStat.created_at >= since_date).count() or 0,
        )

    @staticmethod
    def get_latest_stat() -> InstanceSizeStat | None:
        """获取最新采集记录."""
        return InstanceSizeStat.query.order_by(InstanceSizeStat.created_at.desc()).first()

