"""
实例容量与统计相关接口
"""

from typing import Any

from flask import Response, flash, render_template
from flask_login import login_required

from app import db
from app.errors import SystemError
from app.constants import TaskStatus, FlashCategory
from app.models.instance import Instance
from app.routes.instances import instances_bp
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error


@instances_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str:
    """实例统计页面"""
    try:
        stats = get_instance_statistics()
    except SystemError:
        stats = _empty_instance_statistics()
        flash("获取实例统计信息失败，请稍后重试", FlashCategory.ERROR)
    return render_template("instances/statistics.html", stats=stats)


@instances_bp.route("/api/statistics")
@login_required
@view_required
def api_statistics() -> Response:
    """获取实例统计API"""
    stats = get_instance_statistics()
    return jsonify_unified_success(data=stats, message="获取实例统计信息成功")


def _empty_instance_statistics() -> dict[str, Any]:
    """构建实例统计信息的空状态结果"""
    return {
        "total_instances": 0,
        "active_instances": 0,
        "inactive_instances": 0,
        "db_types_count": 0,
        "db_type_stats": [],
        "port_stats": [],
        "version_stats": [],
    }


def get_instance_statistics() -> dict[str, Any]:
    """获取实例统计数据"""
    try:
        total_instances = Instance.query.count()
        active_instances = Instance.query.filter_by(is_active=True).count()
        inactive_instances = Instance.query.filter_by(is_active=False).count()

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
            "total_instances": total_instances,
            "active_instances": active_instances,
            "inactive_instances": inactive_instances,
            "db_types_count": len(db_type_stats),
            "db_type_stats": [{"db_type": stat.db_type, "count": stat.count} for stat in db_type_stats],
            "port_stats": [{"port": stat.port, "count": stat.count} for stat in port_stats],
            "version_stats": version_stats,
        }

    except Exception as exc:  # noqa: BLE001
        log_error("获取实例统计失败", module="instances", exception=exc)
        raise SystemError("获取实例统计失败") from exc
