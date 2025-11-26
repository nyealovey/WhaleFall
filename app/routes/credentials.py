
"""
鲸落 - 凭据管理路由
"""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from typing import Optional

from app import db
from app.constants.system_constants import SuccessMessages
from app.constants import (
    CREDENTIAL_TYPES,
    DATABASE_TYPES,
    FlashCategory,
    HttpMethod,
    STATUS_ACTIVE_OPTIONS,
    TaskStatus,
)
from app.errors import DatabaseError, NotFoundError, AppValidationError
from app.models.credential import Credential
from app.models.instance import Instance
from app.utils.decorators import (
    create_required,
    delete_required,
    require_csrf,
    update_required,
    view_required,
)
from app.utils.data_validator import sanitize_form_data
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.utils.query_filter_utils import get_active_tag_options
from app.utils.time_utils import time_utils
from app.services.form_service.credentials_form_service import CredentialFormService

# 创建蓝图
credentials_bp = Blueprint("credentials", __name__)
_credential_form_service = CredentialFormService()


def _parse_payload() -> dict:
    """解析并清理请求负载。

    从 JSON 或表单数据中提取并清理数据。

    Returns:
        清理后的数据字典。
    """
    data = request.get_json(silent=True) if request.is_json else request.form
    return sanitize_form_data(data or {})


def _normalize_db_error(action: str, error: Exception) -> str:
    """根据数据库异常内容构建用户友好的提示。

    Args:
        action: 当前执行动作描述，如“创建凭据”。
        error: 捕获到的异常。

    Returns:
        str: 可展示给用户的错误消息。
    """
    message = str(error)
    lowered = message.lower()
    if "unique constraint failed" in lowered or "duplicate key value" in lowered:
        return "凭据名称已存在，请使用其他名称"
    if "not null constraint failed" in lowered:
        return "必填字段不能为空"
    return f"{action}失败，请稍后重试"


def _handle_db_exception(action: str, error: Exception) -> None:
    """统一处理数据库异常并转换为业务错误。

    Args:
        action: 执行的动作名，用于日志。
        error: 捕获到的原始异常。

    Returns:
        None: 回滚并抛出标准化异常后返回。

    Raises:
        DatabaseError: 包含标准化消息的异常。
    """
    db.session.rollback()
    normalized_message = _normalize_db_error(action, error)
    log_error(f"{action}异常: {error}", module="credentials", exc_info=True)
    raise DatabaseError(message=normalized_message) from error


def _get_credential_or_error(credential_id: int) -> Credential:
    """获取凭据或抛出错误。

    Args:
        credential_id: 凭据 ID。

    Returns:
        凭据对象。

    Raises:
        NotFoundError: 当凭据不存在时抛出。
    """
    credential = Credential.query.filter_by(id=credential_id).first()
    if credential is None:
        raise NotFoundError(message="凭据不存在")
    return credential


def _save_via_service(data: dict, credential: Credential | None = None) -> Credential:
    """通过表单服务创建或更新凭据。

    Args:
        data: 经过清洗的表单数据。
        credential: 现有凭据实例（更新时传入）。

    Returns:
        Credential: 保存后的凭据实例。

    Raises:
        AppValidationError: 当表单校验失败时抛出。
    """
    result = _credential_form_service.upsert(data, credential)
    if not result.success or not result.data:
        raise AppValidationError(message=result.message or "凭据保存失败")
    return result.data


@credentials_bp.route("/")
@login_required
@view_required
def index() -> str:
    """凭据管理首页。

    渲染凭据管理页面，支持搜索、类型、数据库类型、状态和标签筛选。

    Returns:
        渲染后的 HTML 页面或 JSON 响应（当请求为 JSON 时）。

    Query Parameters:
        page: 页码，默认 1。
        per_page: 每页数量，默认 10。
        search: 搜索关键词，可选。
        credential_type: 凭据类型筛选，可选。
        db_type: 数据库类型筛选，可选。
        status: 状态筛选，可选。
        tags: 标签筛选（逗号分隔或数组），可选。
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    credential_type_param = request.args.get("credential_type", "", type=str)
    credential_type_filter = credential_type_param if credential_type_param not in {"", "all"} else ""
    db_type_param = request.args.get("db_type", "", type=str)
    db_type_filter = db_type_param if db_type_param not in {"", "all"} else ""
    status_param = request.args.get("status", "", type=str)
    status_filter = status_param if status_param not in {"", "all"} else ""
    tags = [tag for tag in request.args.getlist("tags") if tag.strip()]
    if not tags:
        tags_str = request.args.get("tags", "", type=str)
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    # 构建查询，包含实例数量统计
    query = db.session.query(Credential, db.func.count(Instance.id).label("instance_count")).outerjoin(
        Instance, Credential.id == Instance.credential_id
    )

    if search:
        query = query.filter(
            db.or_(
                Credential.name.contains(search),
                Credential.username.contains(search),
                Credential.description.contains(search),
            )
        )

    if credential_type_filter:
        query = query.filter(Credential.credential_type == credential_type_filter)
    
    if db_type_filter:
        query = query.filter(Credential.db_type == db_type_filter)
    
    if status_filter:
        if status_filter == 'active':
            query = query.filter(Credential.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(Credential.is_active == False)
    
    # 标签筛选
    if tags:
        from app.models.tag import Tag
        query = query.join(Credential.tags).filter(Tag.name.in_(tags))

    # 按凭据分组并排序
    query = query.group_by(Credential.id).order_by(Credential.created_at.desc())

    # 分页查询
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 处理结果，添加实例数量到凭据对象
    credentials_with_count = []
    for cred, instance_count in pagination.items:
        cred.instance_count = instance_count
        credentials_with_count.append(cred)

    # 创建分页对象
    credentials = type(
        "obj",
        (object,),
        {
            "items": credentials_with_count,
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
            "prev_num": pagination.prev_num,
            "next_num": pagination.next_num,
            "iter_pages": pagination.iter_pages,
        },
    )()

    credential_type_options = [{"value": "all", "label": "全部类型"}] + CREDENTIAL_TYPES
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

    if request.is_json:
        return jsonify_unified_success(
            data={
                "credentials": [cred.to_dict() for cred in credentials.items],
                "pagination": {
                    "page": credentials.page,
                    "pages": credentials.pages,
                    "per_page": credentials.per_page,
                    "total": credentials.total,
                    "has_next": credentials.has_next,
                    "has_prev": credentials.has_prev,
                },
                "filter_options": {
                    "credential_types": credential_type_options,
                    "db_types": db_type_options,
                    "status": status_options,
                    "tags": tag_options,
                },
            },
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return render_template(
        "credentials/list.html",
        credentials=credentials,
        search=search,
        credential_type=credential_type_param,
        db_type=db_type_param,
        status=status_param,
        selected_tags=tags,
        credential_type_options=credential_type_options,
        db_type_options=db_type_options,
        status_options=status_options,
        tag_options=tag_options,
    )


@credentials_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_api() -> "Response":
    """创建凭据 API。

    Returns:
        JSON 响应，包含创建的凭据信息。

    Raises:
        AppValidationError: 当表单验证失败时抛出。
        DatabaseError: 当数据库操作失败时抛出。
    """
    payload = _parse_payload()
    credential = _save_via_service(payload)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.DATA_SAVED,
        status=HttpStatus.CREATED,
    )


@credentials_bp.route("/api/<int:credential_id>/edit", methods=["POST"])
@login_required
@update_required
@require_csrf
def edit_api(credential_id: int) -> "Response":
    """编辑凭据 API。

    Args:
        credential_id: 待更新的凭据 ID。

    Returns:
        Response: 统一 JSON 响应。
    """
    credential = _get_credential_or_error(credential_id)
    payload = _parse_payload()
    credential = _save_via_service(payload, credential)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.DATA_UPDATED,
    )


@credentials_bp.route("/api/credentials/<int:credential_id>/delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete(credential_id: int) -> "Response":
    """删除凭据。

    Args:
        credential_id: 凭据 ID。

    Returns:
        JSON 响应或重定向。

    Raises:
        NotFoundError: 当凭据不存在时抛出。
        DatabaseError: 当数据库操作失败时抛出。
    """
    credential = _get_credential_or_error(credential_id)

    credential_name = credential.name
    credential_type = credential.credential_type

    try:
        try:
            db.session.delete(credential)
            db.session.commit()
        except Exception as exc:
            _handle_db_exception("删除凭据", exc)
    except DatabaseError as exc:
        if request.is_json:
            raise
        flash(exc.message, FlashCategory.ERROR)
        return redirect(url_for("credentials.index"))

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

    flash("凭据删除成功！", FlashCategory.SUCCESS)
    return redirect(url_for("credentials.index"))


# API路由
@credentials_bp.route("/api/credentials")
@login_required
@view_required
def api_list() -> "Response":
    """获取凭据列表 API。

    支持分页、排序、搜索和筛选，返回凭据列表及实例数量统计。

    Returns:
        JSON 响应。

    Query Parameters:
        page: 页码，默认 1。
        limit: 每页数量，默认 20。
        sort: 排序字段，默认 'created_at'。
        order: 排序方向（'asc'、'desc'），默认 'desc'。
        search: 搜索关键词，可选。
        credential_type: 凭据类型筛选，可选。
        db_type: 数据库类型筛选，可选。
        status: 状态筛选，可选。
        tags: 标签筛选（逗号分隔或数组），可选。
    """
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    sort_field = request.args.get("sort", "created_at")
    sort_order = request.args.get("order", "desc")
    search = request.args.get("search", "", type=str).strip()
    credential_type = request.args.get("credential_type", "", type=str).strip()
    db_type = request.args.get("db_type", "", type=str).strip()
    status = request.args.get("status", "", type=str).strip()
    tag_params = request.args.getlist("tags")
    if not tag_params:
        tags_str = request.args.get("tags", "", type=str)
        if tags_str:
            tag_params = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    query = db.session.query(Credential, db.func.count(Instance.id).label("instance_count")).outerjoin(
        Instance, Credential.id == Instance.credential_id
    )

    if search:
        query = query.filter(
            db.or_(
                Credential.name.contains(search),
                Credential.username.contains(search),
                Credential.description.contains(search),
            )
        )

    if credential_type and credential_type != "all":
        query = query.filter(Credential.credential_type == credential_type)

    if db_type and db_type != "all":
        query = query.filter(Credential.db_type == db_type)

    if status and status != "all":
        if status == "active":
            query = query.filter(Credential.is_active.is_(True))
        elif status == "inactive":
            query = query.filter(Credential.is_active.is_(False))

    if tag_params:
        from app.models.tag import Tag
        query = query.join(Credential.tags).filter(Tag.name.in_(tag_params))

    query = query.group_by(Credential.id)

    sortable_fields = {
        "id": Credential.id,
        "name": Credential.name,
        "credential_type": Credential.credential_type,
        "db_type": Credential.db_type,
        "username": Credential.username,
        "created_at": Credential.created_at,
        "instance_count": db.func.count(Instance.id),
        "is_active": Credential.is_active,
    }
    order_column = sortable_fields.get(sort_field, Credential.created_at)
    if sort_order == "desc":
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())

    pagination = query.paginate(page=page, per_page=limit, error_out=False)

    items = []
    for credential, instance_count in pagination.items:
        data = credential.to_dict()
        data.update(
            {
                "description": credential.description,
                "is_active": credential.is_active,
                "instance_count": instance_count or 0,
                "created_at_display": time_utils.format_china_time(
                    credential.created_at, "%Y-%m-%d %H:%M:%S"
                )
                if credential.created_at
                else "",
                "name": credential.name,
            }
        )
        items.append(data)

    return jsonify_unified_success(
        data={
            "items": items,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
        },
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@credentials_bp.route("/<int:credential_id>")
@login_required
@view_required
def detail(credential_id: int) -> str:
    """查看凭据详情。

    Args:
        credential_id: 凭据 ID。

    Returns:
        str: 渲染后的详情页面。
    """
    credential = Credential.query.get_or_404(credential_id)
    return render_template("credentials/detail.html", credential=credential)


@credentials_bp.route("/api/credentials/<int:credential_id>")
@login_required
@view_required
def api_detail(credential_id: int) -> "Response":
    """获取凭据详情 API。

    Args:
        credential_id: 凭据 ID。

    Returns:
        Response: JSON 结构的凭据详情。
    """
    credential = _get_credential_or_error(credential_id)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.OPERATION_SUCCESS,
    )


# ---------------------------------------------------------------------------
# 表单路由已由前端模态替代，不再暴露独立页面入口
