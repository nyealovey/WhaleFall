"""实例容量与统计相关接口."""

from flask import flash, render_template
from flask_login import login_required

from app.core.constants import FlashCategory
from app.core.exceptions import SystemError
from app.routes.instances.manage import instances_bp
from app.services.instances.instance_statistics_read_service import InstanceStatisticsReadService
from app.infra.flask_typing import RouteReturn
from app.core.types.instance_statistics import InstanceStatisticsResult
from app.utils.decorators import view_required
from app.infra.route_safety import safe_route_call


@instances_bp.route("/statistics")
@login_required
@view_required
def statistics() -> RouteReturn:
    """实例统计页面.

    Returns:
        str: 渲染后的统计页面.

    """

    def _load() -> InstanceStatisticsResult:
        return InstanceStatisticsReadService().build_statistics()

    try:
        stats = safe_route_call(
            _load,
            module="instances",
            action="statistics_page",
            public_error="获取实例统计信息失败",
            context={"endpoint": "instances_statistics_page"},
        )
    except SystemError:
        stats = InstanceStatisticsReadService.empty_statistics()
        flash("获取实例统计信息失败,请稍后重试", FlashCategory.ERROR)
    return render_template("instances/statistics.html", stats=stats)
