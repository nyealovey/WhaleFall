"""鲸落 - 凭据管理路由."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_restx import marshal
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.constants import (
    CREDENTIAL_TYPES,
    DATABASE_TYPES,
    STATUS_ACTIVE_OPTIONS,
    FlashCategory,
    HttpStatus,
)
from app.constants.system_constants import SuccessMessages
from app.errors import DatabaseError, NotFoundError, ValidationError
from app.models.credential import Credential
from app.routes.credentials_restx_models import CREDENTIAL_LIST_ITEM_FIELDS
from app.services.common.filter_options_service import FilterOptionsService
from app.services.credentials import CredentialsListService
from app.services.form_service.credential_service import CredentialFormService
from app.types.credentials import CredentialListFilters
from app.utils.data_validator import DataValidator
from app.utils.decorators import (
    create_required,
    delete_required,
    require_csrf,
    update_required,
    view_required,
)
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from werkzeug.datastructures import MultiDict

# 创建蓝图
credentials_bp = Blueprint("credentials", __name__)
_credential_form_service = CredentialFormService()
_credential_list_service = CredentialsListService()
_filter_options_service = FilterOptionsService()


def _parse_payload() -> dict:
    """解析并清理请求负载.

    从 JSON 或表单数据中提取并清理数据.

    Returns:
        清理后的数据字典.

    """
    data = request.get_json(silent=True) if request.is_json else request.form
    return DataValidator.sanitize_form_data(data or {})


def _normalize_db_error(action: str, error: Exception) -> str:
    """根据数据库异常内容构建用户友好的提示.

    Args:
        action: 当前执行动作描述,如"创建凭据".
        error: 捕获到的异常.

    Returns:
        str: 可展示给用户的错误消息.

    """
    message = str(error)
    lowered = message.lower()
    if "unique constraint failed" in lowered or "duplicate key value" in lowered:
        return "凭据名称已存在,请使用其他名称"
    if "not null constraint failed" in lowered:
        return "必填字段不能为空"
    return f"{action}失败,请稍后重试"


def _handle_db_exception(action: str, error: Exception) -> None:
    """统一处理数据库异常并转换为业务错误.

    Args:
        action: 执行的动作名,用于日志.
        error: 捕获到的原始异常.

    Returns:
        None: 回滚并抛出标准化异常后返回.

    Raises:
        DatabaseError: 包含标准化消息的异常.

    """
    db.session.rollback()
    normalized_message = _normalize_db_error(action, error)
    log_with_context(
        "error",
        "凭据数据库操作异常",
        module="credentials",
        action=action,
        extra={"error_message": str(error)},
    )
    raise DatabaseError(message=normalized_message) from error


def _get_credential_or_error(credential_id: int) -> Credential:
    """获取凭据或抛出错误.

    Args:
        credential_id: 凭据 ID.

    Returns:
        凭据对象.

    Raises:
        NotFoundError: 当凭据不存在时抛出.

    """
    credential = Credential.query.filter_by(id=credential_id).first()
    if credential is None:
        raise NotFoundError(message="凭据不存在")
    return credential


def _save_via_service(data: dict, credential: Credential | None = None) -> Credential:
    """通过表单服务创建或更新凭据.

    Args:
        data: 经过清洗的表单数据.
        credential: 现有凭据实例(更新时传入).

    Returns:
        Credential: 保存后的凭据实例.

    Raises:
        ValidationError: 当表单校验失败时抛出.

    """
    result = _credential_form_service.upsert(data, credential)
    if not result.success or not result.data:
        raise ValidationError(message=result.message or "凭据保存失败")
    return result.data


def _build_create_response(payload: dict) -> tuple[Response, int]:
    credential = _save_via_service(payload)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.DATA_SAVED,
        status=HttpStatus.CREATED,
    )


def _build_update_response(credential_id: int, payload: dict) -> tuple[Response, int]:
    credential = _get_credential_or_error(credential_id)
    credential = _save_via_service(payload, credential)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.DATA_UPDATED,
    )


def _build_credential_filters(
    *,
    default_page: int,
    default_limit: int,
    allow_sort: bool,
) -> CredentialListFilters:
    """从请求参数构建筛选对象."""
    args = request.args
    page = resolve_page(args, default=default_page, minimum=1)
    limit = resolve_page_size(
        args,
        default=default_limit,
        minimum=1,
        maximum=200,
        module="credentials",
        action="list_credentials",
    )

    search = (args.get("search") or "").strip()
    credential_type = _normalize_filter_choice(args.get("credential_type", "", type=str))
    db_type = _normalize_filter_choice(args.get("db_type", "", type=str))
    status = _normalize_status_choice(args.get("status", "", type=str))
    tags = _extract_tags(args)

    sort_field = "created_at"
    sort_order = "desc"
    if allow_sort:
        sort_field = (args.get("sort", "created_at", type=str) or "created_at").lower()
        sort_order_candidate = (args.get("order", "desc", type=str) or "desc").lower()
        sort_order = sort_order_candidate if sort_order_candidate in {"asc", "desc"} else "desc"

    return CredentialListFilters(
        page=page,
        limit=limit,
        search=search,
        credential_type=credential_type,
        db_type=db_type,
        status=status,
        tags=tags,
        sort_field=sort_field,
        sort_order=sort_order,
    )


def _normalize_filter_choice(raw_value: str) -> str | None:
    """过滤值若为 all/空则返回 None."""
    value = (raw_value or "").strip()
    if not value or value.lower() == "all":
        return None
    return value


def _normalize_status_choice(raw_value: str) -> str | None:
    """规范化状态参数."""
    value = (raw_value or "").strip().lower()
    if value in {"active", "inactive"}:
        return value
    return None


def _extract_tags(args: MultiDict[str, str]) -> list[str]:
    """解析标签筛选."""
    return [tag.strip() for tag in args.getlist("tags") if tag and tag.strip()]


def _build_filter_options() -> dict[str, Any]:
    """构造下拉筛选选项."""
    credential_type_options = [{"value": "all", "label": "全部类型"}, *CREDENTIAL_TYPES]
    db_type_options = [
        {
            "value": item["name"],
            "label": item["display_name"],
            "icon": item.get("icon", "fa-database"),
            "color": item.get("color", "primary"),
        }
        for item in DATABASE_TYPES
    ]
    status_options = STATUS_ACTIVE_OPTIONS
    tag_options = _filter_options_service.list_active_tag_options()
    return {
        "credential_types": credential_type_options,
        "db_types": db_type_options,
        "status": status_options,
        "tags": tag_options,
    }


@credentials_bp.route("/")
@login_required
@view_required
def index() -> str | tuple[Response, int]:
    """凭据管理首页.

    渲染凭据管理页面,支持搜索、类型、数据库类型、状态和标签筛选.

    Returns:
        渲染后的 HTML 页面.

    Query Parameters:
        page: 页码,默认 1.
        page_size: 每页数量,默认 10(兼容 limit/pageSize).
        search: 搜索关键词,可选.
        credential_type: 凭据类型筛选,可选.
        db_type: 数据库类型筛选,可选.
        status: 状态筛选,可选.
        tags: 标签筛选(多值),可选.

    """
    filters = _build_credential_filters(
        default_page=1,
        default_limit=10,
        allow_sort=False,
    )
    credential_type_param = request.args.get("credential_type", "", type=str)
    db_type_param = request.args.get("db_type", "", type=str)
    status_param = request.args.get("status", "", type=str)

    def _execute() -> str:
        filter_options = _build_filter_options()
        return render_template(
            "credentials/list.html",
            search=request.args.get("search", "", type=str),
            credential_type=credential_type_param,
            db_type=db_type_param,
            status=status_param,
            selected_tags=filters.tags,
            credential_type_options=filter_options["credential_types"],
            db_type_options=filter_options["db_types"],
            status_options=filter_options["status"],
            tag_options=filter_options["tags"],
        )

    return safe_route_call(
        _execute,
        module="credentials",
        action="index",
        public_error="加载凭据管理页面失败",
        context={
            "search": filters.search,
            "credential_type": filters.credential_type,
            "db_type": filters.db_type,
            "status": filters.status,
            "tags_count": len(filters.tags),
        },
    )


@credentials_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_credential() -> tuple[Response, int]:
    """创建凭据 API.

    Returns:
        JSON 响应,包含创建的凭据信息.

    Raises:
        ValidationError: 当表单验证失败时抛出.
        DatabaseError: 当数据库操作失败时抛出.

    """
    payload = _parse_payload()

    def _execute() -> tuple[Response, int]:
        return _build_create_response(payload)

    return safe_route_call(
        _execute,
        module="credentials",
        action="create_credential",
        public_error="创建凭据失败",
        context={"credential_name": payload.get("name")},
    )


@credentials_bp.route("/api/credentials", methods=["POST"], endpoint="create_credential_rest")
@login_required
@create_required
@require_csrf
def create_credential_rest() -> tuple[Response, int]:
    """RESTful 创建凭据 API,供前端 CredentialsService 使用."""
    payload = _parse_payload()

    def _execute() -> tuple[Response, int]:
        return _build_create_response(payload)

    return safe_route_call(
        _execute,
        module="credentials",
        action="create_credential_rest",
        public_error="创建凭据失败",
        context={"credential_name": payload.get("name")},
    )


@credentials_bp.route("/api/<int:credential_id>/edit", methods=["POST"])
@login_required
@update_required
@require_csrf
def update_credential(credential_id: int) -> tuple[Response, int]:
    """编辑凭据 API.

    Args:
        credential_id: 待更新的凭据 ID.

    Returns:
        Response: 统一 JSON 响应.

    """
    payload = _parse_payload()

    def _execute() -> tuple[Response, int]:
        return _build_update_response(credential_id, payload)

    return safe_route_call(
        _execute,
        module="credentials",
        action="update_credential",
        public_error="更新凭据失败",
        context={"credential_id": credential_id},
    )


@credentials_bp.route("/api/credentials/<int:credential_id>", methods=["PUT"], endpoint="update_credential_rest")
@login_required
@update_required
@require_csrf
def update_credential_rest(credential_id: int) -> tuple[Response, int]:
    """RESTful 更新凭据 API."""
    payload = _parse_payload()

    def _execute() -> tuple[Response, int]:
        return _build_update_response(credential_id, payload)

    return safe_route_call(
        _execute,
        module="credentials",
        action="update_credential_rest",
        public_error="更新凭据失败",
        context={"credential_id": credential_id},
    )


@credentials_bp.route("/api/credentials/<int:credential_id>/delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete(credential_id: int) -> tuple[Response, int] | Response:
    """删除凭据.

    Args:
        credential_id: 凭据 ID.

    Returns:
        JSON 响应或重定向.

    Raises:
        NotFoundError: 当凭据不存在时抛出.
        DatabaseError: 当数据库操作失败时抛出.

    """
    credential = _get_credential_or_error(credential_id)

    credential_name = credential.name
    credential_type = credential.credential_type

    try:
        def _execute() -> None:
            try:
                db.session.delete(credential)
                db.session.flush()
            except SQLAlchemyError as exc:
                _handle_db_exception("删除凭据", exc)

        safe_route_call(
            _execute,
            module="credentials",
            action="delete_credential",
            public_error="删除凭据失败",
            context={
                "credential_id": credential_id,
                "credential_name": credential_name,
                "credential_type": credential_type,
            },
        )
    except DatabaseError as exc:
        if request.is_json:
            raise
        flash(exc.message, FlashCategory.ERROR)
        return cast(Response, redirect(url_for("credentials.index")))

    log_info(
        "删除数据库凭据",
        module="credentials",
        user_id=current_user.id,
        credential_id=credential_id,
        credential_name=credential_name,
        credential_type=credential_type,
    )

    if request.is_json:
        return jsonify_unified_success(
            data={"credential_id": credential_id},
            message=SuccessMessages.DATA_DELETED,
        )

    flash("凭据删除成功!", FlashCategory.SUCCESS)
    return cast(Response, redirect(url_for("credentials.index")))


# API路由
@credentials_bp.route("/api/credentials")
@login_required
@view_required
def list_credentials() -> tuple[Response, int]:
    """获取凭据列表 API.

    支持分页、排序、搜索和筛选,返回凭据列表及实例数量统计.

    Returns:
        JSON 响应.

    Query Parameters:
        page: 页码,默认 1.
        page_size: 每页数量,默认 20(兼容 limit/pageSize).
        sort: 排序字段,默认 'created_at'.
        order: 排序方向('asc'、'desc'),默认 'desc'.
        search: 搜索关键词,可选.
        credential_type: 凭据类型筛选,可选.
        db_type: 数据库类型筛选,可选.
        status: 状态筛选,可选.
        tags: 标签筛选(多值),可选.

    """
    filters = _build_credential_filters(default_page=1, default_limit=20, allow_sort=True)

    def _execute() -> tuple[Response, int]:
        result = _credential_list_service.list_credentials(filters)
        items = marshal(result.items, CREDENTIAL_LIST_ITEM_FIELDS)
        return jsonify_unified_success(
            data={
                "items": items,
                "total": result.total,
                "page": result.page,
                "pages": result.pages,
                "limit": result.limit,
            },
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return safe_route_call(
        _execute,
        module="credentials",
        action="list_credentials",
        public_error="获取凭据列表失败",
        context={
            "search": filters.search,
            "credential_type": filters.credential_type,
            "db_type": filters.db_type,
            "status": filters.status,
            "tags": filters.tags,
            "sort": filters.sort_field,
            "order": filters.sort_order,
            "page": filters.page,
            "limit": filters.limit,
        },
    )


@credentials_bp.route("/<int:credential_id>")
@login_required
@view_required
def detail(credential_id: int) -> str:
    """查看凭据详情.

    Args:
        credential_id: 凭据 ID.

    Returns:
        str: 渲染后的详情页面.

    """
    credential = Credential.query.get_or_404(credential_id)
    return render_template("credentials/detail.html", credential=credential)


@credentials_bp.route("/api/credentials/<int:credential_id>")
@login_required
@view_required
def get_credential(credential_id: int) -> tuple[Response, int]:
    """获取凭据详情 API.

    Args:
        credential_id: 凭据 ID.

    Returns:
        Response: JSON 结构的凭据详情.

    """
    credential = _get_credential_or_error(credential_id)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.OPERATION_SUCCESS,
    )


# ---------------------------------------------------------------------------
# 表单路由已由前端模态替代,不再暴露独立页面入口
