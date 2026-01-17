"""实例统计 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app import db
from app.models.instance import Instance
from app.models.instance_size_stat import InstanceSizeStat


class InstanceStatisticsRepository:
    """实例统计读模型 Repository."""

    @staticmethod
    def fetch_summary(*, db_type: str | None = None) -> dict[str, int]:
        """获取实例统计摘要."""
        query = Instance.query
        if db_type:
            query = query.filter(Instance.db_type == db_type)

        total_instances = query.count()

        existing_query = query.filter(Instance.deleted_at.is_(None))
        existing_instances = existing_query.count()
        active_instances = existing_query.filter(Instance.is_active.is_(True)).count()
        disabled_instances = max(existing_instances - active_instances, 0)
        deleted_instances = max(total_instances - existing_instances, 0)
        normal_instances = active_instances

        return {
            "total_instances": total_instances,
            "active_instances": active_instances,
            "normal_instances": normal_instances,
            "disabled_instances": disabled_instances,
            "deleted_instances": deleted_instances,
        }

    @staticmethod
    def fetch_db_type_stats() -> list[Any]:
        """获取实例按数据库类型统计."""
        return (
            db.session.query(Instance.db_type, db.func.count(Instance.id).label("count"))
            .group_by(Instance.db_type)
            .all()
        )

    @staticmethod
    def fetch_port_stats(limit: int = 10) -> list[Any]:
        """获取实例按端口统计."""
        return (
            db.session.query(Instance.port, db.func.count(Instance.id).label("count"))
            .group_by(Instance.port)
            .order_by(db.func.count(Instance.id).desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def fetch_version_stats() -> list[Any]:
        """获取实例按版本统计."""
        return (
            db.session.query(
                Instance.db_type,
                Instance.main_version,
                db.func.count(Instance.id).label("count"),
            )
            .group_by(Instance.db_type, Instance.main_version)
            .all()
        )

    @staticmethod
    def fetch_total_capacity_mb(*, recent_date: date) -> float:
        """汇总最近 N 天内每个实例最新容量的总和(MB)."""
        ranked_stats_subquery = (
            db.session.query(
                InstanceSizeStat.instance_id.label("instance_id"),
                db.func.coalesce(InstanceSizeStat.total_size_mb, 0).label("total_size_mb"),
                db.func.row_number()
                .over(
                    partition_by=InstanceSizeStat.instance_id,
                    order_by=(InstanceSizeStat.collected_date.desc(), InstanceSizeStat.collected_at.desc()),
                )
                .label("rn"),
            )
            .join(Instance, Instance.id == InstanceSizeStat.instance_id)
            .filter(InstanceSizeStat.collected_date >= recent_date)
            .filter(Instance.is_active.is_(True), Instance.deleted_at.is_(None))
            .subquery()
        )

        total_size_mb = (
            db.session.query(db.func.coalesce(db.func.sum(ranked_stats_subquery.c.total_size_mb), 0))
            .filter(ranked_stats_subquery.c.rn == 1)
            .scalar()
        )
        total_value = total_size_mb if total_size_mb is not None else 0
        return float(total_value)
