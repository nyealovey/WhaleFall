"""实例详情相关接口.

仅保留实例详情页面路由(HTML).
"""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from app.services.instances.instance_detail_page_service import InstanceDetailPageService
from app.types import RouteReturn
from app.utils.decorators import view_required
from app.utils.route_safety import safe_route_call

instances_detail_bp = Blueprint("instances_detail", __name__, url_prefix="/instances")


@instances_detail_bp.route("/<int:instance_id>")
@login_required
@view_required
def detail(instance_id: int) -> RouteReturn:
    """实例详情页面.

    Args:
        instance_id: 实例 ID.

    Returns:
        渲染的实例详情页面,包含账户列表和统计信息.

    Raises:
        NotFoundError: 当实例不存在时抛出.

    Query Parameters:
        include_deleted: 是否包含已删除账户,默认 'true'.

    """

    def _render() -> str:
        context = InstanceDetailPageService().build_context(instance_id)

        return render_template(
            "instances/detail.html",
            instance=context.instance,
            tags=context.tags,
            account_summary=context.account_summary,
            credentials=context.credentials,
            database_type_options=context.database_type_options,
        )

    return safe_route_call(
        _render,
        module="instances",
        action="detail",
        public_error="实例详情加载失败",
        context={"instance_id": instance_id},
    )
