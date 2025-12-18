"""鲸落 - 凭据管理路由."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
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
from app.errors import AppValidationError, DatabaseError, NotFoundError
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.tag import Tag
from app.services.form_service.credential_service import CredentialFormService
from app.utils.data_validator import DataValidator
from app.utils.decorators import (
    create_required,
    delete_required,
    require_csrf,
    update_required,
    view_required,
)
from app.utils.query_filter_utils import get_active_tag_options
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import log_with_context
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from flask_sqlalchemy.pagination import Pagination
    from sqlalchemy.orm import Query
    from werkzeug.datastructures import MultiDict

# 创建蓝图
credentials_bp = Blueprint("credentials", __name__)
_credential_form_service = CredentialFormService()


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
        AppValidationError: 当表单校验失败时抛出.

    """
    result = _credential_form_service.upsert(data, credential)
    if not result.success or not result.data:
        raise AppValidationError(message=result.message or "凭据保存失败")
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


@dataclass(slots=True)
class CredentialFilterParams:
    """凭据列表筛选参数."""

    page: int
    limit: int
    search: str
    credential_type: str | None
    db_type: str | None
    status: str | None
    tags: list[str]
    sort_field: str
    sort_order: str


ALLOWED_SORT_FIELDS = {
    "id": Credential.id,
    "name": Credential.name,
    "credential_type": Credential.credential_type,
    "db_type": Credential.db_type,
    "username": Credential.username,
    "created_at": Credential.created_at,
    "instance_count": db.func.count(Instance.id),
    "is_active": Credential.is_active,
}


def _build_credential_filters(
    *,
    default_page: int,
    default_limit: int,
    allow_sort: bool,
) -> CredentialFilterParams:
    """从请求参数构建筛选对象."""
    args = request.args
    page = args.get("page", default_page, type=int)
    limit = args.get("limit", default_limit, type=int)
    limit = max(1, min(limit, 200))

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

    return CredentialFilterParams(
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


def _build_credential_query(filters: CredentialFilterParams) -> Query:
    """基于筛选参数构建查询."""
    query: Query = db.session.query(Credential, db.func.count(Instance.id).label("instance_count")).outerjoin(
        Instance,
        Credential.id == Instance.credential_id,
    )
    if filters.search:
        query = cast("Query", query).filter(
            or_(
                Credential.name.contains(filters.search),
                Credential.username.contains(filters.search),
                Credential.description.contains(filters.search),
            ),
        )
    if filters.credential_type:
        query = cast("Query", query).filter(Credential.credential_type == filters.credential_type)
    if filters.db_type:
        query = cast("Query", query).filter(Credential.db_type == filters.db_type)
    if filters.status:
        if filters.status == "active":
            query = cast("Query", query).filter(cast(Any, Credential.is_active).is_(True))
        else:
            query = cast("Query", query).filter(cast(Any, Credential.is_active).is_(False))
    if filters.tags:
        tag_name_in = cast(Any, Tag.name).in_(filters.tags)
        query = cast("Query", query).join(cast(Any, Instance.tags)).filter(tag_name_in)

    query = cast("Query", query).group_by(Credential.id)
    return _apply_sorting(query, filters)


def _apply_sorting(query: Query, filters: CredentialFilterParams) -> Query:
    """根据排序字段排序."""
    sort_field = filters.sort_field if filters.sort_field in ALLOWED_SORT_FIELDS else "created_at"
    column = ALLOWED_SORT_FIELDS[sort_field]
    ordered = column.desc() if filters.sort_order == "desc" else column.asc()
    return query.order_by(ordered)


def _hydrate_credentials(pagination: Pagination) -> list[Credential]:
    """将实例数量注入凭据对象,方便模板与序列化."""
    enriched: list[Credential] = []
    for credential, instance_count in pagination.items:
        credential.instance_count = instance_count
        enriched.append(credential)
    return enriched


def _build_template_pagination(pagination: Pagination, credentials: list[Credential]) -> object:
    """构造模板期望的分页对象."""
    return type(
        "CredentialPagination",
        (object,),
        {
            "items": credentials,
            "page": pagination.page,
            "pages": pagination.pages,
            "limit": pagination.per_page,
            "total": pagination.total,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
            "prev_num": pagination.prev_num,
            "next_num": pagination.next_num,
            "iter_pages": pagination.iter_pages,
        },
    )()


def _build_pagination_payload(pagination: Pagination) -> dict[str, Any]:
    """构造统一的分页结构."""
    return {
        "page": pagination.page,
        "pages": pagination.pages,
        "limit": pagination.per_page,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


def _serialize_credentials(credentials: list[Credential]) -> list[dict[str, Any]]:
    """序列化凭据列表."""
    serialized: list[dict[str, Any]] = []
    for credential in credentials:
        data = credential.to_dict()
        data.update(
            {
                "description": credential.description,
                "is_active": credential.is_active,
                "instance_count": getattr(credential, "instance_count", 0) or 0,
                "created_at_display": (
                    time_utils.format_china_time(credential.created_at, "%Y-%m-%d %H:%M:%S")
                    if credential.created_at
                    else ""
                ),
                "name": credential.name,
            },
        )
        serialized.append(data)
    return serialized


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
    tag_options = get_active_tag_options()
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
        渲染后的 HTML 页面或 JSON 响应(当请求为 JSON 时).

    Query Parameters:
        page: 页码,默认 1.
        limit: 每页数量,默认 10.
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
    query = _build_credential_query(filters)
    pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
    credentials = _hydrate_credentials(pagination)
    template_pagination = _build_template_pagination(pagination, credentials)

    if request.is_json:
        return jsonify_unified_success(
            data={
                "items": [cred.to_dict() for cred in credentials],
                "total": pagination.total,
                "page": pagination.page,
                "pages": pagination.pages,
                "limit": pagination.per_page,
                "filter_options": _build_filter_options(),
            },
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    credential_type_param = request.args.get("credential_type", "", type=str)
    db_type_param = request.args.get("db_type", "", type=str)
    status_param = request.args.get("status", "", type=str)
    filter_options = _build_filter_options()

    return render_template(
        "credentials/list.html",
        credentials=template_pagination,
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


@credentials_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_credential() -> tuple[Response, int]:
    """创建凭据 API.

    Returns:
        JSON 响应,包含创建的凭据信息.

    Raises:
        AppValidationError: 当表单验证失败时抛出.
        DatabaseError: 当数据库操作失败时抛出.

    """
    payload = _parse_payload()
    return _build_create_response(payload)


@credentials_bp.route("/api/credentials", methods=["POST"], endpoint="create_credential_rest")
@login_required
@create_required
@require_csrf
def create_credential_rest() -> tuple[Response, int]:
    """RESTful 创建凭据 API,供前端 CredentialsService 使用."""
    payload = _parse_payload()
    return _build_create_response(payload)


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
    return _build_update_response(credential_id, payload)


@credentials_bp.route("/api/credentials/<int:credential_id>", methods=["PUT"], endpoint="update_credential_rest")
@login_required
@update_required
@require_csrf
def update_credential_rest(credential_id: int) -> tuple[Response, int]:
    """RESTful 更新凭据 API."""
    payload = _parse_payload()
    return _build_update_response(credential_id, payload)


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
        try:
            db.session.delete(credential)
            db.session.commit()
        except SQLAlchemyError as exc:
            _handle_db_exception("删除凭据", exc)
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
        limit: 每页数量,默认 20.
        sort: 排序字段,默认 'created_at'.
        order: 排序方向('asc'、'desc'),默认 'desc'.
        search: 搜索关键词,可选.
        credential_type: 凭据类型筛选,可选.
        db_type: 数据库类型筛选,可选.
        status: 状态筛选,可选.
        tags: 标签筛选(多值),可选.

    """
    filters = _build_credential_filters(
        default_page=1,
        default_limit=20,
        allow_sort=True,
    )
    query = _build_credential_query(filters)
    pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
    credentials = _hydrate_credentials(pagination)
    items = _serialize_credentials(credentials)

    return jsonify_unified_success(
        data={
            "items": items,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "limit": pagination.per_page,
        },
        message=SuccessMessages.OPERATION_SUCCESS,
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
