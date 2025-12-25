"""鲸落 - 数据库实例管理路由."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from flask_restx import marshal

from app import db
from app.constants import (
    STATUS_ACTIVE_OPTIONS,
    HttpStatus,
)
from app.errors import ConflictError, ValidationError
from app.models.credential import Credential
from app.models.instance import Instance
from app.routes.instances.batch import batch_deletion_service
from app.services.database_type_service import DatabaseTypeService
from app.services.instances.instance_list_service import InstanceListService
from app.types.instances import InstanceListFilters
from app.utils.data_validator import (
    DataValidator,
)
from app.utils.decorators import create_required, delete_required, require_csrf, update_required, view_required
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.query_filter_utils import get_active_tag_options
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info
from app.routes.instances.restx_models import INSTANCE_LIST_ITEM_FIELDS

if TYPE_CHECKING:
    from werkzeug.datastructures import MultiDict


# 创建蓝图
instances_bp = Blueprint("instances", __name__)


def _parse_instance_filters(args: MultiDict[str, str]) -> InstanceListFilters:
    """解析请求参数,构建统一的筛选条件."""
    page = resolve_page(args, default=1, minimum=1)
    limit = resolve_page_size(
        args,
        default=20,
        minimum=1,
        maximum=100,
        module="instances",
        action="list_instances_data",
    )
    sort_field = (args.get("sort", "id", type=str) or "id").lower()
    sort_order = (args.get("order", "desc", type=str) or "desc").lower()
    if sort_order not in {"asc", "desc"}:
        sort_order = "desc"

    search = (args.get("search") or "").strip()
    db_type = (args.get("db_type") or "").strip()
    status_value = (args.get("status") or "").strip()
    tags = [tag.strip() for tag in args.getlist("tags") if tag and tag.strip()]
    include_deleted_raw = (args.get("include_deleted") or "").strip().lower()
    include_deleted = include_deleted_raw in {"true", "1", "on", "yes"}

    return InstanceListFilters(
        page=page,
        limit=limit,
        sort_field=sort_field,
        sort_order=sort_order,
        search=search,
        db_type=db_type,
        status=status_value,
        tags=tags,
        include_deleted=include_deleted,
    )


@instances_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例管理首页.

    渲染实例列表页面,支持搜索、筛选和标签过滤.

    Returns:
        渲染后的 HTML 页面.

    """
    search = (request.args.get("search") or "").strip()
    db_type = (request.args.get("db_type") or "").strip()
    status_param = (request.args.get("status") or "").strip()
    include_deleted_raw = (request.args.get("include_deleted") or "").strip().lower()
    include_deleted = include_deleted_raw in {"true", "1", "on", "yes"}
    tags_raw = request.args.getlist("tags")
    tags = [tag.strip() for tag in tags_raw if tag.strip()]

    # 获取所有可用的凭据
    credentials = Credential.query.filter_by(is_active=True).all()

    database_type_configs = DatabaseTypeService.get_active_types()
    database_type_options = [
        {
            "value": config.name,
            "label": config.display_name,
            "icon": config.icon or "fa-database",
            "color": config.color or "primary",
        }
        for config in database_type_configs
    ]
    database_type_map = {
        config.name: {
            "display_name": config.display_name,
            "icon": config.icon or "fa-database",
            "color": config.color or "primary",
        }
        for config in database_type_configs
    }

    tag_options = get_active_tag_options()

    return render_template(
        "instances/list.html",
        credentials=credentials,
        database_type_options=database_type_options,
        database_type_map=database_type_map,
        tag_options=tag_options,
        status_options=STATUS_ACTIVE_OPTIONS,
        search=search,
        db_type=db_type,
        status=status_param,
        include_deleted=include_deleted,
        selected_tags=tags,
    )


@instances_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_instance() -> tuple[Response, int]:  # noqa: PLR0915
    """创建实例 API.

    接收 JSON 或表单数据,验证后创建新的数据库实例.

    Returns:
        包含新创建实例信息的 JSON 响应.

    Raises:
        ValidationError: 当数据验证失败时抛出.
        ConflictError: 当实例名称已存在时抛出.
        SystemError: 当创建失败时抛出.

    """
    raw_payload = request.get_json() if request.is_json else request.form
    payload = DataValidator.sanitize_input(raw_payload)
    credential_context_raw = payload.get("credential_id")
    db_type_context_raw = payload.get("db_type")
    if isinstance(credential_context_raw, (str, int)):
        try:
            credential_context = int(credential_context_raw)
        except (TypeError, ValueError):
            credential_context = None
    else:
        credential_context = None
    db_type_context = db_type_context_raw if isinstance(db_type_context_raw, str) else None

    def _execute() -> tuple[Response, int]:
        is_valid, validation_error = DataValidator.validate_instance_data(payload)
        if not is_valid:
            raise ValidationError(validation_error)

        name = str(payload.get("name") or "").strip()
        db_type_raw = payload.get("db_type")
        db_type_value = db_type_raw if isinstance(db_type_raw, str) else ""
        host = str(payload.get("host") or "").strip()
        description = str(payload.get("description") or "").strip()

        port_raw = payload.get("port")
        if not isinstance(port_raw, (str, int)):
            raise ValidationError("端口号格式不正确")
        try:
            port = int(port_raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError("端口号格式不正确") from exc

        credential_id_value = payload.get("credential_id")
        credential_id: int | None = None
        if credential_id_value is not None:
            if not isinstance(credential_id_value, (str, int)):
                raise ValidationError("无效的凭据ID")
            try:
                credential_id = int(credential_id_value)
            except (ValueError, TypeError) as exc:
                msg = "无效的凭据ID"
                raise ValidationError(msg) from exc
            credential = Credential.query.get(credential_id)
            if not credential:
                msg = "凭据不存在"
                raise ValidationError(msg)

        existing_instance = Instance.query.filter_by(name=name).first()
        if existing_instance:
            msg = "实例名称已存在"
            raise ConflictError(msg)

        instance = Instance(
            name=name,
            db_type=db_type_value,
            host=host,
            port=port,
            credential_id=credential_id,
            description=description,
            is_active=True,
        )

        db.session.add(instance)
        db.session.flush()

        log_info(
            "创建数据库实例",
            module="instances",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
            port=instance.port,
        )

        return jsonify_unified_success(
            data={"instance": instance.to_dict()},
            message="实例创建成功",
            status=HttpStatus.CREATED,
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="create_instance",
        public_error="创建实例失败",
        context={"credential_id": credential_context, "db_type": db_type_context},
    )


@instances_bp.route("/api/<int:instance_id>/delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete(instance_id: int) -> tuple[Response, int]:
    """删除实例.

    将指定实例移入回收站（软删除），便于误删恢复。

    Args:
        instance_id: 实例ID.

    Returns:
        包含删除统计信息的 JSON 响应.

    Raises:
        SystemError: 当删除失败时抛出.

    """
    instance = Instance.query.get_or_404(instance_id)

    def _execute() -> tuple[Response, int]:
        log_info(
            "移入回收站",
            module="instances",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
        )

        result = batch_deletion_service.delete_instances(
            [instance.id],
            operator_id=current_user.id,
            deletion_mode="soft",
        )

        return jsonify_unified_success(
            data={
                "instance_id": instance.id,
                "deleted_at": instance.deleted_at.isoformat() if instance.deleted_at else None,
                "deletion_mode": result.get("deletion_mode"),
            },
            message="实例已移入回收站",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="delete_instance",
        public_error="移入回收站失败,请重试",
        context={"instance_id": instance_id},
    )


@instances_bp.route("/api/<int:instance_id>/restore", methods=["POST"])
@login_required
@update_required
@require_csrf
def restore(instance_id: int) -> tuple[Response, int]:
    """恢复实例.

    将已删除（deleted_at 非空）的实例恢复为可用状态。

    Args:
        instance_id: 实例 ID.

    Returns:
        Response: 恢复结果的统一 JSON 响应.

    """
    instance = Instance.query.get_or_404(instance_id)

    def _execute() -> tuple[Response, int]:
        if not instance.deleted_at:
            return jsonify_unified_success(
                data={"instance": instance.to_dict()},
                message="实例未删除，无需恢复",
            )

        instance.deleted_at = None
        db.session.add(instance)

        log_info(
            "恢复数据库实例",
            module="instances",
            user_id=current_user.id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
        )

        return jsonify_unified_success(
            data={"instance": instance.to_dict()},
            message="实例恢复成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="restore_instance",
        public_error="恢复实例失败,请重试",
        context={"instance_id": instance_id},
    )


# API路由
@instances_bp.route("/api/instances", methods=["GET"])
@login_required
@view_required
def list_instances_data() -> tuple[Response, int]:
    """Grid.js 实例列表 API.

    Returns:
        Response: 包含分页实例数据的 JSON.

    Raises:
        SystemError: 查询或序列化失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        filters = _parse_instance_filters(request.args)
        result = InstanceListService().list_instances(filters)
        items = marshal(result.items, INSTANCE_LIST_ITEM_FIELDS)

        return jsonify_unified_success(
            data={
                "items": items,
                "total": result.total,
                "page": result.page,
                "pages": result.pages,
                "limit": result.limit,
            },
            message="获取实例列表成功",
        )

    return safe_route_call(
        _execute,
        module="instances",
        action="list_instances_data",
        public_error="获取实例列表失败",
        context={
            "endpoint": "instances_list",
            "search": request.args.get("search"),
            "status": request.args.get("status"),
            "include_deleted": request.args.get("include_deleted"),
        },
    )


@instances_bp.route("/api/<int:instance_id>")
@login_required
@view_required
def get_instance_detail(instance_id: int) -> tuple[Response, int]:
    """获取实例详情 API.

    Args:
        instance_id: 实例 ID.

    Returns:
        Response: 包含实例详细信息的 JSON.

    """
    instance = (
        Instance.query.filter(
            Instance.id == instance_id,
            cast(Any, Instance.deleted_at).is_(None),
        )
        .first_or_404()
    )
    return jsonify_unified_success(
        data={"instance": instance.to_dict()},
        message="获取实例详情成功",
    )


# 注册额外路由模块
def _load_related_blueprints() -> None:
    """确保实例管理相关蓝图被导入注册."""
    from . import (  # noqa: F401, PLC0415
        detail,
        statistics,
    )


_load_related_blueprints()
