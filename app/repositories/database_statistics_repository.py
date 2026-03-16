"""数据库统计 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, desc, func

from app import db
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase


class DatabaseStatisticsRepository:
    """数据库统计读模型 Repository."""

    @staticmethod
    def fetch_summary(*, instance_id: int | None = None) -> dict[str, int]:
        """获取数据库统计摘要."""
        query = InstanceDatabase.query.join(Instance, Instance.id == InstanceDatabase.instance_id).filter(
            Instance.is_active.is_(True),
            Instance.deleted_at.is_(None),
        )

        if instance_id is not None:
            query = query.filter(InstanceDatabase.instance_id == instance_id)

        total_databases = int(query.count())
        active_databases = int(
            query.filter(
                InstanceDatabase.is_active.is_(True),
                InstanceDatabase.deleted_at.is_(None),
            ).count(),
        )
        deleted_databases = int(query.filter(InstanceDatabase.deleted_at.isnot(None)).count())
        inactive_databases = max(total_databases - active_databases - deleted_databases, 0)
        total_instances_value = (
            db.session.query(func.count(func.distinct(InstanceDatabase.instance_id)))
            .join(Instance, Instance.id == InstanceDatabase.instance_id)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
            )
        )
        if instance_id is not None:
            total_instances_value = total_instances_value.filter(InstanceDatabase.instance_id == instance_id)
        total_instances_scalar = total_instances_value.scalar()
        total_instances = int(total_instances_scalar) if total_instances_scalar is not None else 0

        return {
            "total_databases": total_databases,
            "active_databases": active_databases,
            "inactive_databases": inactive_databases,
            "deleted_databases": deleted_databases,
            "total_instances": total_instances,
        }

    @staticmethod
    def fetch_db_type_stats() -> list[Any]:
        """获取当前活跃数据库按类型分布."""
        return (
            db.session.query(
                Instance.db_type.label("db_type"),
                func.count(InstanceDatabase.id).label("count"),
            )
            .join(Instance, Instance.id == InstanceDatabase.instance_id)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceDatabase.is_active.is_(True),
            )
            .group_by(Instance.db_type)
            .order_by(desc("count"), Instance.db_type.asc())
            .all()
        )

    @staticmethod
    def fetch_instance_stats(limit: int = 10) -> list[Any]:
        """获取当前活跃数据库按实例分布."""
        return (
            db.session.query(
                Instance.id.label("instance_id"),
                Instance.name.label("instance_name"),
                Instance.db_type.label("db_type"),
                func.count(InstanceDatabase.id).label("count"),
            )
            .join(InstanceDatabase, Instance.id == InstanceDatabase.instance_id)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceDatabase.is_active.is_(True),
            )
            .group_by(Instance.id, Instance.name, Instance.db_type)
            .order_by(desc("count"), Instance.name.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def fetch_latest_sync_rows() -> list[Any]:
        """获取活跃数据库最近一次容量采集时间."""
        latest_stats = DatabaseStatisticsRepository._latest_capacity_subquery()
        return (
            db.session.query(latest_stats.c.latest_collected_at.label("collected_at"))
            .select_from(InstanceDatabase)
            .join(Instance, Instance.id == InstanceDatabase.instance_id)
            .outerjoin(
                latest_stats,
                and_(
                    InstanceDatabase.instance_id == latest_stats.c.instance_id,
                    InstanceDatabase.database_name == latest_stats.c.database_name,
                ),
            )
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceDatabase.is_active.is_(True),
            )
            .all()
        )

    @staticmethod
    def fetch_capacity_rankings(limit: int = 10) -> list[Any]:
        """获取活跃数据库最新容量排行."""
        latest_stats = DatabaseStatisticsRepository._latest_capacity_subquery()
        return (
            db.session.query(
                Instance.id.label("instance_id"),
                Instance.name.label("instance_name"),
                Instance.db_type.label("db_type"),
                InstanceDatabase.database_name.label("database_name"),
                DatabaseSizeStat.size_mb.label("size_mb"),
                latest_stats.c.latest_collected_at.label("collected_at"),
            )
            .select_from(InstanceDatabase)
            .join(Instance, Instance.id == InstanceDatabase.instance_id)
            .join(
                latest_stats,
                and_(
                    InstanceDatabase.instance_id == latest_stats.c.instance_id,
                    InstanceDatabase.database_name == latest_stats.c.database_name,
                ),
            )
            .join(
                DatabaseSizeStat,
                and_(
                    DatabaseSizeStat.instance_id == latest_stats.c.instance_id,
                    DatabaseSizeStat.database_name == latest_stats.c.database_name,
                    DatabaseSizeStat.collected_at == latest_stats.c.latest_collected_at,
                ),
            )
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceDatabase.is_active.is_(True),
            )
            .order_by(DatabaseSizeStat.size_mb.desc(), latest_stats.c.latest_collected_at.desc(), Instance.name.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def fetch_capacity_summary() -> dict[str, float]:
        """汇总活跃数据库最新容量."""
        latest_stats = DatabaseStatisticsRepository._latest_capacity_subquery()
        row = (
            db.session.query(
                func.coalesce(func.sum(DatabaseSizeStat.size_mb), 0).label("total_size_mb"),
                func.coalesce(func.avg(DatabaseSizeStat.size_mb), 0).label("avg_size_mb"),
                func.coalesce(func.max(DatabaseSizeStat.size_mb), 0).label("max_size_mb"),
            )
            .select_from(InstanceDatabase)
            .join(Instance, Instance.id == InstanceDatabase.instance_id)
            .join(
                latest_stats,
                and_(
                    InstanceDatabase.instance_id == latest_stats.c.instance_id,
                    InstanceDatabase.database_name == latest_stats.c.database_name,
                ),
            )
            .join(
                DatabaseSizeStat,
                and_(
                    DatabaseSizeStat.instance_id == latest_stats.c.instance_id,
                    DatabaseSizeStat.database_name == latest_stats.c.database_name,
                    DatabaseSizeStat.collected_at == latest_stats.c.latest_collected_at,
                ),
            )
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceDatabase.is_active.is_(True),
            )
            .one()
        )
        return {
            "total_size_mb": float(getattr(row, "total_size_mb", 0) or 0),
            "avg_size_mb": float(getattr(row, "avg_size_mb", 0) or 0),
            "max_size_mb": float(getattr(row, "max_size_mb", 0) or 0),
        }

    @staticmethod
    def _latest_capacity_subquery() -> Any:
        return (
            db.session.query(
                DatabaseSizeStat.instance_id.label("instance_id"),
                DatabaseSizeStat.database_name.label("database_name"),
                func.max(DatabaseSizeStat.collected_at).label("latest_collected_at"),
            )
            .group_by(DatabaseSizeStat.instance_id, DatabaseSizeStat.database_name)
            .subquery()
        )
