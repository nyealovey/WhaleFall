"""
实例统计服务

封装实例数量、类型、端口、版本等统计逻辑，供仪表盘及统计页面复用。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app import db
from app.errors import SystemError
from app.models.instance import Instance
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils


def fetch_summary(*, db_type: str | None = None) -> dict[str, int]:
    """获取实例数汇总（总数=活跃+已删除，活跃=正常+禁用）。"""
    try:
        query = Instance.query
        if db_type:
            query = query.filter(Instance.db_type == db_type)

        total_instances = query.count()

        active_query = query.filter(Instance.deleted_at.is_(None))
        active_instances = active_query.count()

        disabled_instances = active_query.filter(Instance.is_active.is_(False)).count()
        deleted_instances = max(total_instances - active_instances, 0)
        normal_instances = max(active_instances - disabled_instances, 0)

        return {
            "total_instances": total_instances,
            "active_instances": active_instances,
            "normal_instances": normal_instances,
            "disabled_instances": disabled_instances,
            "deleted_instances": deleted_instances,
        }
    except Exception as exc:  # noqa: BLE001
        log_error("获取实例汇总失败", module="instance_statistics", exception=exc)
        raise SystemError("获取实例汇总失败") from exc


def fetch_capacity_summary(*, recent_days: int = 7) -> dict[str, float]:
    """汇总实例容量信息，返回总容量与使用率。"""
    try:
        from app.models.instance_size_stat import InstanceSizeStat

        recent_date = time_utils.now_china().date() - timedelta(days=recent_days)
        recent_stats = (
            InstanceSizeStat.query.join(Instance, Instance.id == InstanceSizeStat.instance_id)
            .filter(InstanceSizeStat.collected_date >= recent_date)
            .filter(Instance.is_active.is_(True), Instance.deleted_at.is_(None))
            .all()
        )

        latest_per_instance: dict[int, dict[str, Any]] = {}
        for stat in recent_stats:
            current = latest_per_instance.get(stat.instance_id)
            if current is None or stat.collected_date > current["date"]:
                latest_per_instance[stat.instance_id] = {
                    "size_mb": stat.total_size_mb or 0,
                    "date": stat.collected_date,
                }

        total_capacity_gb = sum(item["size_mb"] for item in latest_per_instance.values()) / 1024
        capacity_usage_percent = 0
        return {
            "total_gb": round(total_capacity_gb, 1),
            "usage_percent": capacity_usage_percent,
        }
    except Exception as exc:  # noqa: BLE001
        log_error("获取实例容量统计失败", module="instance_statistics", exception=exc)
        raise SystemError("获取实例容量统计失败") from exc


def build_aggregated_statistics() -> dict[str, Any]:
    """构建实例统计页面需要的详细数据。"""
    try:
        totals = fetch_summary()

        db_type_stats = (
            db.session.query(Instance.db_type, db.func.count(Instance.id).label("count"))
            .group_by(Instance.db_type)
            .all()
        )

        port_stats = (
            db.session.query(Instance.port, db.func.count(Instance.id).label("count"))
            .group_by(Instance.port)
            .order_by(db.func.count(Instance.id).desc())
            .limit(10)
            .all()
        )

        version_stats_query = (
            db.session.query(
                Instance.db_type,
                Instance.main_version,
                db.func.count(Instance.id).label("count"),
            )
            .group_by(Instance.db_type, Instance.main_version)
            .all()
        )

        version_stats = [
            {
                "db_type": stat.db_type,
                "version": stat.main_version or "未知版本",
                "count": stat.count,
            }
            for stat in version_stats_query
        ]

        return {
            **totals,
            "inactive_instances": totals["disabled_instances"],
            "db_types_count": len(db_type_stats),
            "db_type_stats": [{"db_type": stat.db_type, "count": stat.count} for stat in db_type_stats],
            "port_stats": [{"port": stat.port, "count": stat.count} for stat in port_stats],
            "version_stats": version_stats,
        }
    except SystemError:
        raise
    except Exception as exc:  # noqa: BLE001
        log_error("获取实例统计失败", module="instance_statistics", exception=exc)
        raise SystemError("获取实例统计失败") from exc


def empty_statistics() -> dict[str, Any]:
    """构造空的实例统计结果。"""
    return {
        "total_instances": 0,
        "active_instances": 0,
        "normal_instances": 0,
        "disabled_instances": 0,
        "deleted_instances": 0,
        "inactive_instances": 0,
        "db_types_count": 0,
        "db_type_stats": [],
        "port_stats": [],
        "version_stats": [],
    }
