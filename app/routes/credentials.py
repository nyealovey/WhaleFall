
"""
鲸落 - 凭据管理路由
"""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from typing import Optional

from app import db
from app.constants.system_constants import SuccessMessages
from app.errors import (
    AppValidationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
)
from app.models.credential import Credential
from app.models.instance import Instance
from app.utils.decorators import (
    create_required,
    delete_required,
    update_required,
    view_required,
)
from app.utils.data_validator import (
    sanitize_form_data,
    validate_credential_type,
    validate_db_type,
    validate_password,
    validate_required_fields,
    validate_username,
)
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
credentials_bp = Blueprint("credentials", __name__)


def _parse_payload() -> dict:
    data = request.get_json(silent=True) if request.is_json else request.form
    return sanitize_form_data(data or {})


def _coerce_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"true", "1", "yes", "on"}
    return default


def _validate_credential_input(data: dict, *, require_password: bool) -> None:
    required_fields = ["name", "credential_type", "username"]
    if require_password:
        required_fields.append("password")

    validation_error = validate_required_fields(data, required_fields)
    if validation_error:
        raise AppValidationError(message=validation_error)

    username_error = validate_username(data.get("username"))
    if username_error:
        raise AppValidationError(message=username_error)

    if require_password or data.get("password"):
        password_error = validate_password(data.get("password"))
        if password_error:
            raise AppValidationError(message=password_error)

    if data.get("db_type"):
        db_type_error = validate_db_type(data.get("db_type"))
        if db_type_error:
            raise AppValidationError(message=db_type_error)

    credential_type_error = validate_credential_type(data.get("credential_type"))
    if credential_type_error:
        raise AppValidationError(message=credential_type_error)


def _ensure_unique_name(name: str, *, exclude_id: Optional[int] = None) -> None:
    query = Credential.query.filter(Credential.name == name.strip())
    if exclude_id is not None:
        query = query.filter(Credential.id != exclude_id)
    if query.first():
        raise ConflictError(message="凭据名称已存在，请使用其他名称")


def _normalize_db_error(action: str, error: Exception) -> str:
    message = str(error)
    lowered = message.lower()
    if "unique constraint failed" in lowered or "duplicate key value" in lowered:
        return "凭据名称已存在，请使用其他名称"
    if "not null constraint failed" in lowered:
        return "必填字段不能为空"
    return f"{action}失败，请稍后重试"


def _handle_db_exception(action: str, error: Exception) -> None:
    db.session.rollback()
    normalized_message = _normalize_db_error(action, error)
    log_error(f"{action}异常: {error}", module="credentials", exc_info=True)
    raise DatabaseError(message=normalized_message) from error


def _create_credential_record(data: dict) -> Credential:
    _validate_credential_input(data, require_password=True)
    name = (data.get("name") or "").strip()
    _ensure_unique_name(name)

    credential = Credential(
        name=name,
        credential_type=data.get("credential_type"),
        username=(data.get("username") or "").strip(),
        password=data.get("password"),
        db_type=data.get("db_type"),
        description=((data.get("description") or "").strip() or None),
    )
    credential.is_active = _coerce_bool(data.get("is_active"), default=True)

    try:
        db.session.add(credential)
        db.session.commit()
    except Exception as exc:
        _handle_db_exception("创建凭据", exc)

    log_info(
        "创建数据库凭据",
        module="credentials",
        user_id=current_user.id,
        credential_id=credential.id,
        credential_name=credential.name,
        credential_type=credential.credential_type,
        db_type=credential.db_type,
        is_active=credential.is_active,
    )
    return credential


def _update_credential_record(credential: Credential, data: dict) -> Credential:
    _validate_credential_input(data, require_password=False)
    name = (data.get("name") or credential.name).strip()
    _ensure_unique_name(name, exclude_id=credential.id)

    credential.name = name
    credential.credential_type = data.get("credential_type", credential.credential_type)
    credential.db_type = data.get("db_type", credential.db_type)
    credential.username = (data.get("username") or credential.username).strip()

    if "description" in data:
        description_value = data.get("description")
        credential.description = (description_value or "").strip() or None

    if data.get("password"):
        credential.set_password(data["password"])

    if "is_active" in data:
        credential.is_active = _coerce_bool(data.get("is_active"), default=credential.is_active)

    try:
        db.session.commit()
    except Exception as exc:
        _handle_db_exception("更新凭据", exc)

    log_info(
        "更新数据库凭据",
        module="credentials",
        user_id=current_user.id,
        credential_id=credential.id,
        credential_name=credential.name,
        credential_type=credential.credential_type,
        db_type=credential.db_type,
        is_active=credential.is_active,
    )
    return credential


def _get_credential_or_error(credential_id: int) -> Credential:
    credential = Credential.query.filter_by(id=credential_id).first()
    if credential is None:
        raise NotFoundError(message="凭据不存在")
    return credential


@credentials_bp.route("/")
@login_required
@view_required
def index() -> str:
    """凭据管理首页"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    credential_type = request.args.get("credential_type", "", type=str)
    db_type = request.args.get("db_type", "", type=str)
    status = request.args.get("status", "", type=str)
    tags_str = request.args.get("tags", "", type=str)
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

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

    if credential_type:
        query = query.filter(Credential.credential_type == credential_type)
    
    if db_type:
        query = query.filter(Credential.db_type == db_type)
    
    if status:
        if status == 'active':
            query = query.filter(Credential.is_active == True)
        elif status == 'inactive':
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
            },
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return render_template(
        "credentials/list.html",
        credentials=credentials,
        search=search,
        search_value=search,
        credential_type=credential_type,
        db_type=db_type,
        status=status,
        tags=tags,
        selected_tags=tags,
    )


@credentials_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
def create_api() -> "Response":
    """创建凭据API"""
    payload = _parse_payload()
    credential = _create_credential_record(payload)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.DATA_SAVED,
        status=201,
    )


@credentials_bp.route("/create", methods=["GET", "POST"])
@login_required
@create_required
def create() -> "str | Response":
    """创建凭据"""
    if request.method == "POST":
        payload = _parse_payload()
        try:
            credential = _create_credential_record(payload)
        except (AppValidationError, ConflictError) as exc:
            if request.is_json:
                raise
            flash(exc.message, "error")
            return render_template("credentials/create.html")
        except DatabaseError as exc:
            if request.is_json:
                raise
            flash(exc.message, "error")
            return render_template("credentials/create.html")

        if request.is_json:
            return jsonify_unified_success(
                data={"credential": credential.to_dict()},
                message=SuccessMessages.DATA_SAVED,
                status=201,
            )

        flash("凭据创建成功！", "success")
        return redirect(url_for("credentials.index"))

    # GET请求，显示创建表单
    if request.is_json:
        return jsonify_unified_success(data={}, message=SuccessMessages.OPERATION_SUCCESS)

    return render_template("credentials/create.html")


@credentials_bp.route("/api/<int:credential_id>/edit", methods=["POST"])
@login_required
@update_required
def edit_api(credential_id: int) -> "Response":
    """编辑凭据API"""
    credential = _get_credential_or_error(credential_id)
    payload = _parse_payload()
    credential = _update_credential_record(credential, payload)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.DATA_UPDATED,
    )


@credentials_bp.route("/<int:credential_id>/edit", methods=["GET", "POST"])
@login_required
@update_required
def edit(credential_id: int) -> "str | Response":
    """编辑凭据"""
    credential = Credential.query.get_or_404(credential_id)

    if request.method == "POST":
        payload = _parse_payload()
        try:
            credential = _update_credential_record(credential, payload)
        except (AppValidationError, ConflictError) as exc:
            if request.is_json:
                raise
            flash(exc.message, "error")
            return render_template("credentials/edit.html", credential=credential)
        except DatabaseError as exc:
            if request.is_json:
                raise
            flash(exc.message, "error")
            return render_template("credentials/edit.html", credential=credential)

        if request.is_json:
            return jsonify_unified_success(
                data={"credential": credential.to_dict()},
                message=SuccessMessages.DATA_UPDATED,
            )

        flash("凭据更新成功！", "success")
        return redirect(url_for("credentials.index"))

    # GET请求，显示编辑表单
    if request.is_json:
        return jsonify_unified_success(
            data={"credential": credential.to_dict()},
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return render_template("credentials/edit.html", credential=credential)


@credentials_bp.route("/api/credentials/<int:credential_id>/toggle", methods=["POST"])
@login_required
@update_required
def toggle(credential_id: int) -> "Response":
    """启用/禁用凭据"""
    credential = _get_credential_or_error(credential_id)
    payload = _parse_payload()

    is_active = _coerce_bool(payload.get("is_active"), default=credential.is_active)
    credential.is_active = is_active

    try:
        try:
            db.session.commit()
        except Exception as exc:
            _handle_db_exception("切换凭据状态", exc)
    except DatabaseError as exc:
        if request.is_json:
            raise
        flash(exc.message, "error")
        return redirect(url_for("credentials.index"))

    log_info(
        "切换凭据状态",
        module="credentials",
        user_id=current_user.id,
        credential_id=credential.id,
        credential_name=credential.name,
        is_active=is_active,
    )

    message = "凭据启用成功" if is_active else "凭据禁用成功"

    if request.is_json:
        return jsonify_unified_success(
            data={"credential": credential.to_dict(), "is_active": is_active},
            message=message,
        )

    flash(message, "success")
    return redirect(url_for("credentials.index"))


@credentials_bp.route("/api/credentials/<int:credential_id>/delete", methods=["POST"])
@login_required
@delete_required
def delete(credential_id: int) -> "Response":
    """删除凭据"""
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
        flash(exc.message, "error")
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

    flash("凭据删除成功！", "success")
    return redirect(url_for("credentials.index"))


# API路由
@credentials_bp.route("/api/credentials")
@login_required
@view_required
def api_list() -> "Response":
    """获取凭据列表API"""
    credentials = Credential.query.filter_by(is_active=True).all()
    return jsonify_unified_success(
        data={"credentials": [cred.to_dict() for cred in credentials]},
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@credentials_bp.route("/<int:credential_id>")
@login_required
@view_required
def detail(credential_id: int) -> str:
    """查看凭据详情"""
    credential = Credential.query.get_or_404(credential_id)
    return render_template("credentials/detail.html", credential=credential)


@credentials_bp.route("/api/credentials/<int:credential_id>")
@login_required
@view_required
def api_detail(credential_id: int) -> "Response":
    """获取凭据详情API"""
    credential = _get_credential_or_error(credential_id)
    return jsonify_unified_success(
        data={"credential": credential.to_dict()},
        message=SuccessMessages.OPERATION_SUCCESS,
    )
