"""实例容量与统计相关接口."""

from flask import flash, render_template
from flask_login import login_required
from werkzeug.exceptions import HTTPException

from app.core.constants import FlashCategory
from app.core.exceptions import AppError, SystemError
from app.infra.flask_typing import RouteReturn
from app.infra.route_safety import log_fallback, safe_route_call
from app.routes.instances.manage import instances_bp
from app.services.instances.instance_statistics_read_service import InstanceStatisticsReadService
from app.utils.decorators import view_required


@instances_bp.route("/statistics")
@login_required
@view_required
def statistics() -> RouteReturn:
    """实例统计页面.

    Returns:
        str: 渲染后的统计页面.

    """
    public_error = "获取实例统计信息失败"

    def _execute() -> RouteReturn:
        try:
            stats = InstanceStatisticsReadService().build_statistics()
        except SystemError as exc:
            stats = InstanceStatisticsReadService.empty_statistics()
            flash("获取实例统计信息失败,请稍后重试", FlashCategory.ERROR)
            log_fallback(
                "warning",
                "实例统计页面降级",
                module="instances",
                action="statistics_page",
                fallback_reason=exc.__class__.__name__,
                context={"endpoint": "instances_statistics_page"},
                extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
            )
        except (AppError, HTTPException):
            raise
        except Exception as exc:
            stats = InstanceStatisticsReadService.empty_statistics()
            flash("获取实例统计信息失败,请稍后重试", FlashCategory.ERROR)
            log_fallback(
                "error",
                "实例统计页面降级",
                module="instances",
                action="statistics_page",
                fallback_reason=exc.__class__.__name__,
                context={"endpoint": "instances_statistics_page"},
                extra={"error_type": exc.__class__.__name__, "error_message": str(exc), "unexpected": True},
            )
        return render_template("instances/statistics.html", stats=stats)

    return safe_route_call(
        _execute,
        module="instances",
        action="statistics_page",
        public_error=public_error,
        context={"endpoint": "instances_statistics_page"},
    )
