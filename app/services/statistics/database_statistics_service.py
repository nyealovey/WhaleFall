"""
数据库统计服务

提供仪表盘、统计页面等可复用的数据库聚合数据接口。
"""

from __future__ import annotations

from app import db
from app.errors import SystemError
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.utils.structlog_config import log_error


def fetch_summary(*, instance_id: int | None = None) -> dict[str, int]:
    """
    汇总数据库数量统计。

    Args:
        instance_id: 可选实例过滤条件，仅统计指定实例下的数据库。
    """
    try:
        query = InstanceDatabase.query.join(Instance, Instance.id == InstanceDatabase.instance_id)

        if instance_id is not None:
            query = query.filter(InstanceDatabase.instance_id == instance_id)

        total_databases = query.count()
        active_databases = query.filter(InstanceDatabase.is_active.is_(True)).count()
        inactive_databases = max(total_databases - active_databases, 0)

        deleted_databases = (
            db.session.query(db.func.count(InstanceDatabase.id))
            .join(Instance, Instance.id == InstanceDatabase.instance_id)
            .filter(Instance.deleted_at.isnot(None))
        )
        if instance_id is not None:
            deleted_databases = deleted_databases.filter(InstanceDatabase.instance_id == instance_id)
        deleted_databases = deleted_databases.scalar() or 0

        return {
            "total_databases": total_databases,
            "active_databases": active_databases,
            "inactive_databases": inactive_databases,
            "deleted_databases": deleted_databases,
        }
    except Exception as exc:  # noqa: BLE001
        log_error("获取数据库统计失败", module="database_statistics", exception=exc)
        raise SystemError("获取数据库统计失败") from exc


def empty_summary() -> dict[str, int]:
    """构造空的数据库统计结果。"""
    return {
        "total_databases": 0,
        "active_databases": 0,
        "inactive_databases": 0,
        "deleted_databases": 0,
    }
