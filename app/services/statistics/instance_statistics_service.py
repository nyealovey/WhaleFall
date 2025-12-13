"""实例统计服务.

封装实例数量、类型、端口、版本等统计逻辑,供仪表盘及统计页面复用.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app import db
from app.errors import SystemError
from app.models.instance import Instance
from app.models.instance_size_stat import InstanceSizeStat
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils


def fetch_summary(*, db_type: str | None = None) -> dict[str, int]:
    """获取实例数量汇总统计.

    统计实例总数、活跃数、正常数、禁用数和已删除数.
    可选择性地只统计指定数据库类型的实例.

    Args:
        db_type: 可选的数据库类型筛选,如 'mysql'、'postgresql'.

    Returns:
        包含实例统计信息的字典,格式如下:
        {
            'total_instances': 100,      # 实例总数
            'active_instances': 85,      # 活跃实例数(未删除)
            'normal_instances': 80,      # 正常实例数(活跃且启用)
            'disabled_instances': 5,     # 禁用实例数
            'deleted_instances': 15      # 已删除实例数
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    try:
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

    except Exception as exc:
        log_error("获取实例汇总失败", module="instance_statistics", exception=exc)
        msg = "获取实例汇总失败"
        raise SystemError(msg) from exc
    else:
        return {
            "total_instances": total_instances,
            "active_instances": active_instances,
            "normal_instances": normal_instances,
            "disabled_instances": disabled_instances,
            "deleted_instances": deleted_instances,
        }


def fetch_capacity_summary(*, recent_days: int = 7) -> dict[str, float]:
    """汇总实例容量信息.

    基于最近指定天数的容量统计数据,计算所有活跃实例的总容量.
    对每个实例取最新的一条统计记录.

    Args:
        recent_days: 统计最近多少天的数据,默认 7 天.

    Returns:
        包含容量统计信息的字典,格式如下:
        {
            'total_gb': 1024.5,        # 总容量(GB)
            'usage_percent': 0         # 使用率(暂未实现)
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    try:
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
    except Exception as exc:
        log_error("获取实例容量统计失败", module="instance_statistics", exception=exc)
        msg = "获取实例容量统计失败"
        raise SystemError(msg) from exc


def build_aggregated_statistics() -> dict[str, Any]:
    """构建实例统计页面的详细数据.

    汇总实例的基本统计、数据库类型分布、端口分布和版本分布.

    Returns:
        包含详细统计信息的字典,格式如下:
        {
            'total_instances': 100,
            'active_instances': 85,
            'normal_instances': 80,
            'disabled_instances': 5,
            'deleted_instances': 15,
            'inactive_instances': 5,
            'db_types_count': 3,
            'db_type_stats': [
                {'db_type': 'mysql', 'count': 50},
                {'db_type': 'postgresql', 'count': 30},
                ...
            ],
            'port_stats': [
                {'port': 3306, 'count': 50},
                {'port': 5432, 'count': 30},
                ...
            ],
            'version_stats': [
                {'db_type': 'mysql', 'version': '8.0', 'count': 30},
                ...
            ]
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
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
    except Exception as exc:
        log_error("获取实例统计失败", module="instance_statistics", exception=exc)
        msg = "获取实例统计失败"
        raise SystemError(msg) from exc


def empty_statistics() -> dict[str, Any]:
    """构造空的实例统计结果.

    Returns:
        所有统计值为 0 或空数组的字典,格式与 build_aggregated_statistics 返回值相同.

    """
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
