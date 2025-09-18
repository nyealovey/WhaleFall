"""
鲸落 - 凭据管理路由
"""

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models.credential import Credential
from app.models.instance import Instance
from app.utils.decorators import (
    create_required,
    delete_required,
    update_required,
    view_required,
)
from app.utils.security import (
    sanitize_form_data,
    validate_credential_type,
    validate_db_type,
    validate_password,
    validate_required_fields,
    validate_username,
)
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
credentials_bp = Blueprint("credentials", __name__)


@credentials_bp.route("/")
@login_required
@view_required
def index() -> str:
    """凭据管理首页"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    credential_type = request.args.get("credential_type", "", type=str)

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
        return jsonify(
            {
                "credentials": [cred.to_dict() for cred in credentials.items],
                "pagination": {
                    "page": credentials.page,
                    "pages": credentials.pages,
                    "per_page": credentials.per_page,
                    "total": credentials.total,
                    "has_next": credentials.has_next,
                    "has_prev": credentials.has_prev,
                },
            }
        )

    return render_template(
        "credentials/list.html",
        credentials=credentials,
        search=search,
        credential_type=credential_type,
    )


@credentials_bp.route("/create", methods=["GET", "POST"])
@login_required
@create_required
def create() -> "str | Response":
    """创建凭据"""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form

        # 清理输入数据
        data = sanitize_form_data(data)

        # 输入验证
        required_fields = ["name", "credential_type", "username", "password"]
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            if request.is_json:
                return jsonify({"error": validation_error}), 400
            flash(validation_error, "error")
            return render_template("credentials/create.html")

        # 验证用户名格式
        username_error = validate_username(data.get("username"))
        if username_error:
            if request.is_json:
                return jsonify({"error": username_error}), 400
            flash(username_error, "error")
            return render_template("credentials/create.html")

        # 验证密码强度
        password_error = validate_password(data.get("password"))
        if password_error:
            if request.is_json:
                return jsonify({"error": password_error}), 400
            flash(password_error, "error")
            return render_template("credentials/create.html")

        # 验证数据库类型
        if data.get("db_type"):
            db_type_error = validate_db_type(data.get("db_type"))
            if db_type_error:
                if request.is_json:
                    return jsonify({"error": db_type_error}), 400
                flash(db_type_error, "error")
                return render_template("credentials/create.html")

        # 验证凭据类型
        credential_type_error = validate_credential_type(data.get("credential_type"))
        if credential_type_error:
            if request.is_json:
                return jsonify({"error": credential_type_error}), 400
            flash(credential_type_error, "error")
            return render_template("credentials/create.html")

        # 验证凭据名称唯一性
        existing_credential = Credential.query.filter_by(name=data.get("name")).first()
        if existing_credential:
            error_msg = "凭据名称已存在"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, "error")
            return render_template("credentials/create.html")

        try:
            # 创建新凭据
            credential = Credential(
                name=data.get("name").strip(),
                credential_type=data.get("credential_type"),
                username=data.get("username").strip(),
                password=data.get("password"),
                db_type=data.get("db_type"),
                description=data.get("description", "").strip(),
            )

            db.session.add(credential)
            db.session.commit()

            # 记录操作日志
            log_info(
                "创建数据库凭据",
                module="credentials",
                user_id=current_user.id,
                credential_id=credential.id,
                credential_name=credential.name,
                credential_type=credential.credential_type,
                db_type=credential.db_type,
            )

            if request.is_json:
                return (
                    jsonify({"message": "凭据创建成功", "credential": credential.to_dict()}),
                    201,
                )

            flash("凭据创建成功！", "success")
            return redirect(url_for("credentials.index"))

        except Exception as e:
            db.session.rollback()
            log_error(f"创建凭据失败: {e}", module="credentials", exc_info=True)

            # 根据错误类型提供更具体的错误信息
            if "UNIQUE constraint failed" in str(e):
                error_msg = "凭据名称已存在，请使用其他名称"
            elif "NOT NULL constraint failed" in str(e):
                error_msg = "必填字段不能为空"
            else:
                error_msg = f"创建凭据失败: {str(e)}"

            if request.is_json:
                return jsonify({"error": error_msg}), 500

            flash(error_msg, "error")

    # GET请求，显示创建表单
    if request.is_json:
        return jsonify({})

    return render_template("credentials/create.html")


@credentials_bp.route("/<int:credential_id>")
@login_required
@view_required
def detail(credential_id: int) -> str:
    """凭据详情"""
    credential = Credential.query.get_or_404(credential_id)

    if request.is_json:
        return jsonify(credential.to_dict())

    return render_template("credentials/detail.html", credential=credential)


@credentials_bp.route("/<int:credential_id>/edit", methods=["GET", "POST"])
@login_required
@update_required
def edit(credential_id: int) -> "str | Response":
    """编辑凭据"""
    credential = Credential.query.get_or_404(credential_id)

    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form

        # 清理输入数据
        data = sanitize_form_data(data)

        # 输入验证
        required_fields = ["name", "credential_type", "username"]
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            if request.is_json:
                return jsonify({"error": validation_error}), 400
            flash(validation_error, "error")
            return render_template("credentials/edit.html", credential=credential)

        # 验证用户名格式
        username_error = validate_username(data.get("username"))
        if username_error:
            if request.is_json:
                return jsonify({"error": username_error}), 400
            flash(username_error, "error")
            return render_template("credentials/edit.html", credential=credential)

        # 验证密码强度（如果提供了新密码）
        if data.get("password"):
            password_error = validate_password(data.get("password"))
            if password_error:
                if request.is_json:
                    return jsonify({"error": password_error}), 400
                flash(password_error, "error")
                return render_template("credentials/edit.html", credential=credential)

        # 验证数据库类型
        if data.get("db_type"):
            db_type_error = validate_db_type(data.get("db_type"))
            if db_type_error:
                if request.is_json:
                    return jsonify({"error": db_type_error}), 400
                flash(db_type_error, "error")
                return render_template("credentials/edit.html", credential=credential)

        # 验证凭据类型
        credential_type_error = validate_credential_type(data.get("credential_type"))
        if credential_type_error:
            if request.is_json:
                return jsonify({"error": credential_type_error}), 400
            flash(credential_type_error, "error")
            return render_template("credentials/edit.html", credential=credential)

        # 验证凭据名称唯一性（排除当前凭据）
        existing_credential = Credential.query.filter(
            Credential.name == data.get("name"), Credential.id != credential_id
        ).first()
        if existing_credential:
            error_msg = "凭据名称已存在"
            if request.is_json:
                return jsonify({"error": error_msg}), 400
            flash(error_msg, "error")
            return render_template("credentials/edit.html", credential=credential)

        try:
            # 更新凭据信息
            credential.name = data.get("name", credential.name).strip()
            credential.credential_type = data.get("credential_type", credential.credential_type)
            credential.db_type = data.get("db_type", credential.db_type)
            credential.username = data.get("username", credential.username).strip()
            credential.description = data.get("description", credential.description)
            if data.get("description"):
                credential.description = data.get("description").strip()

            # 正确处理布尔值
            is_active_value = data.get("is_active", credential.is_active)
            if isinstance(is_active_value, str):
                credential.is_active = is_active_value in ["on", "true", "1", "yes"]
            else:
                credential.is_active = bool(is_active_value)

            # 如果提供了新密码，则更新密码
            if data.get("password"):
                credential.set_password(data.get("password"))

            db.session.commit()

            # 记录操作成功日志
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

            if request.is_json:
                return jsonify({"message": "凭据更新成功", "credential": credential.to_dict()})

            flash("凭据更新成功！", "success")
            return redirect(url_for("credentials.detail", credential_id=credential_id))

        except Exception as e:
            db.session.rollback()
            log_error(f"更新凭据失败: {e}", module="credentials", exc_info=True)

            # 根据错误类型提供更具体的错误信息
            if "UNIQUE constraint failed" in str(e):
                error_msg = "凭据名称已存在，请使用其他名称"
            elif "NOT NULL constraint failed" in str(e):
                error_msg = "必填字段不能为空"
            else:
                error_msg = f"更新凭据失败: {str(e)}"

            if request.is_json:
                return jsonify({"error": error_msg}), 500

            flash(error_msg, "error")

    # GET请求，显示编辑表单
    if request.is_json:
        return jsonify({"credential": credential.to_dict()})

    return render_template("credentials/edit.html", credential=credential)


@credentials_bp.route("/<int:credential_id>/toggle", methods=["POST"])
@login_required
@update_required
def toggle(credential_id: int) -> "Response":
    """启用/禁用凭据"""
    credential = Credential.query.get_or_404(credential_id)
    data = request.get_json()

    try:
        is_active = data.get("is_active", False)
        credential.is_active = is_active
        db.session.commit()

        # 记录操作日志
        log_info(
            "切换凭据状态",
            module="credentials",
            user_id=current_user.id,
            credential_id=credential.id,
            credential_name=credential.name,
            is_active=is_active,
        )

        action = "启用" if is_active else "禁用"
        message = f"凭据{action}成功"

        if request.is_json:
            return jsonify({"message": message})

        flash(message, "success")
        return redirect(url_for("credentials.index"))

    except Exception as e:
        db.session.rollback()
        log_error(f"切换凭据状态失败: {e}", module="credentials", exc_info=True)

        error_msg = f"切换凭据状态失败: {str(e)}"

        if request.is_json:
            return jsonify({"error": error_msg}), 500

        flash(error_msg, "error")
        return redirect(url_for("credentials.index"))


@credentials_bp.route("/<int:credential_id>/delete", methods=["POST"])
@login_required
@delete_required
def delete(credential_id: int) -> "Response":
    """删除凭据"""
    credential = Credential.query.get_or_404(credential_id)

    try:
        # 记录删除前的凭据信息
        credential_name = credential.name
        credential_type = credential.credential_type
        credential_id = credential.id

        db.session.delete(credential)
        db.session.commit()

        # 记录操作成功日志
        log_info(
            "删除数据库凭据",
            module="credentials",
            user_id=current_user.id,
            credential_id=credential_id,
            credential_name=credential_name,
            credential_type=credential_type,
        )

        if request.is_json:
            return jsonify({"message": "凭据删除成功"})

        flash("凭据删除成功！", "success")
        return redirect(url_for("credentials.index"))

    except Exception as e:
        db.session.rollback()
        log_error(f"删除凭据失败: {e}", module="credentials")

        if request.is_json:
            return jsonify({"error": "删除凭据失败，请重试"}), 500

        flash("删除凭据失败，请重试", "error")
        return redirect(url_for("credentials.index"))


# API路由
@credentials_bp.route("/api/credentials")
@login_required
@view_required
def api_list() -> "Response":
    """获取凭据列表API"""
    credentials = Credential.query.filter_by(is_active=True).all()
    return jsonify([cred.to_dict() for cred in credentials])


@credentials_bp.route("/api/credentials/<int:credential_id>")
@login_required
@view_required
def api_detail(credential_id: int) -> "Response":
    """获取凭据详情API"""
    credential = Credential.query.get_or_404(credential_id)
    return jsonify(credential.to_dict())
