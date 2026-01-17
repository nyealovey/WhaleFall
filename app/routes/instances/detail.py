"""实例详情相关接口.

仅保留实例详情页面路由(HTML).
"""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

from app.core.constants import DatabaseType
from app.infra.flask_typing import RouteReturn
from app.infra.route_safety import safe_route_call
from app.repositories.credentials_repository import CredentialsRepository
from app.repositories.instance_accounts_repository import InstanceAccountsRepository
from app.repositories.instances_repository import InstancesRepository
from app.utils.database_type_utils import get_database_type_display_name
from app.utils.decorators import view_required

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
        instances_repository = InstancesRepository()
        instance_accounts_repository = InstanceAccountsRepository()

        instance = instances_repository.get_active_instance(instance_id)
        tags_map = instances_repository.fetch_tags_map([instance_id])
        account_summary = instance_accounts_repository.fetch_summary(instance_id)
        credentials = CredentialsRepository.list_active_credentials()
        database_type_options = [
            {"value": db_type, "label": get_database_type_display_name(db_type)} for db_type in DatabaseType.RELATIONAL
        ]

        return render_template(
            "instances/detail.html",
            instance=instance,
            tags=tags_map.get(instance_id, []),
            account_summary=account_summary,
            credentials=credentials,
            database_type_options=database_type_options,
        )

    return safe_route_call(
        _render,
        module="instances",
        action="detail",
        public_error="实例详情加载失败",
        context={"instance_id": instance_id},
    )
