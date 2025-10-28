
"""
鲸落 - 标签管理路由
"""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models.tag import Tag
from app.constants.colors import ThemeColors
from app.errors import ConflictError, ValidationError
from app.utils.decorators import create_required, delete_required, require_csrf, update_required, view_required
from app.utils.data_validator import validate_required_fields
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
tags_bp = Blueprint("tags", __name__)


@tags_bp.route("/")
@login_required
@view_required
def index() -> str:
    """标签管理首页"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    status = request.args.get("status", "all", type=str)

    # 构建查询
    query = Tag.query

    if search:
        query = query.filter(
            db.or_(
                Tag.name.contains(search),
                Tag.display_name.contains(search),
                Tag.description.contains(search),
            )
        )

    if category:
        query = query.filter(Tag.category == category)

    if status == "active":
        query = query.filter_by(is_active=True)
    elif status == "inactive":
        query = query.filter_by(is_active=False)
    # 移除软删除相关逻辑，因为现在使用硬删除

    # 排序
    query = query.order_by(Tag.category, Tag.sort_order, Tag.name)

    # 分页
    tags = query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    # 获取分类选项
    categories = Tag.get_category_choices()

    return render_template(
        "tags/index.html",
        tags=tags,
        search=search,
        search_value=search,
        category=category,
        status=status,
        categories=categories,
    )


@tags_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_api() -> tuple[Response, int]:
    """创建标签API"""
    data = request.get_json(silent=True) if request.is_json else request.form

    # 验证必填字段
    required_fields = ["name", "display_name", "category"]
    validation_error = validate_required_fields(data, required_fields)
    if validation_error:
        raise ValidationError(
            validation_error,
            message_key="VALIDATION_ERROR",
            extra={"fields": required_fields},
        )

    # 获取表单数据
    name = (data.get("name") or "").strip()
    display_name = (data.get("display_name") or "").strip()
    category = (data.get("category") or "").strip()
    color = (data.get("color") or "primary").strip()
    description = (data.get("description") or "").strip()

    if request.is_json:
        sort_raw = data.get("sort_order", 0)
        try:
            sort_order = int(sort_raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"排序值格式错误: {exc}",
                message_key="INVALID_REQUEST",
                extra={"sort_order": sort_raw},
            ) from exc
        is_active_raw = data.get("is_active", True)
    else:
        sort_order = data.get("sort_order", type=int) or 0
        is_active_raw = data.get("is_active", "on")

    if isinstance(is_active_raw, str):
        is_active = is_active_raw.lower() in {"on", "true", "1", "yes"}
    else:
        is_active = bool(is_active_raw)

    # 验证颜色
    if not ThemeColors.is_valid_color(color):
        raise ValidationError(
            f"无效的颜色选择: {color}",
            message_key="INVALID_REQUEST",
            extra={"color": color},
        )

    # 验证标签名称唯一性
    existing_tag = Tag.query.filter_by(name=name).first()
    if existing_tag:
        raise ConflictError(
            "标签名称已存在",
            extra={"name": name},
        )

    tag = Tag(
        name=name,
        display_name=display_name,
        category=category,
        color=color,
        description=description,
        sort_order=sort_order,
        is_active=is_active,
    )

    db.session.add(tag)
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "创建标签失败",
            module="tags",
            user_id=current_user.id,
            payload={
                "name": name,
                "display_name": display_name,
                "category": category,
            },
            exception=exc,
        )
        raise

    log_info(
        "创建标签成功",
        module="tags",
        user_id=current_user.id,
        tag_id=tag.id,
        tag_name=tag.name,
        category=tag.category,
    )

    return jsonify_unified_success(
        data={"tag": tag.to_dict()},
        message="标签创建成功",
        status=HttpStatus.CREATED,
    )


@tags_bp.route("/create", methods=["GET", "POST"])
@login_required
@create_required
@require_csrf
def create() -> str | Response:
    """创建标签"""
    if request.method == "POST":
        try:
            # 验证必填字段
            required_fields = ["name", "display_name", "category"]
            validation_error = validate_required_fields(request.form, required_fields)
            if validation_error:
                flash(validation_error, "error")
                return render_template("tags/create.html", color_options=ThemeColors.COLOR_MAP)

            # 获取表单数据
            name = request.form.get("name", "").strip()
            display_name = request.form.get("display_name", "").strip()
            category = request.form.get("category", "").strip()
            color = request.form.get("color", "primary").strip()
            description = request.form.get("description", "").strip()
            sort_order = request.form.get("sort_order", 0, type=int)
            is_active = request.form.get("is_active") == "on"

            # 验证颜色
            if not ThemeColors.is_valid_color(color):
                flash(f"无效的颜色选择: {color}", "error")
                return render_template("tags/create.html", color_options=ThemeColors.COLOR_MAP)

            # 检查名称是否已存在
            existing_tag = Tag.query.filter_by(name=name).first()
            if existing_tag:
                flash(f"标签代码 '{name}' 已存在", "error")
                return render_template("tags/create.html", color_options=ThemeColors.COLOR_MAP)

            # 创建标签
            tag = Tag(
                name=name,
                display_name=display_name,
                category=category,
                color=color,
                description=description,
                sort_order=sort_order,
                is_active=is_active,
            )

            db.session.add(tag)
            db.session.commit()

            log_info(
                "标签创建成功",
                module="tags",
                tag_id=tag.id,
                name=tag.name,
                display_name=tag.display_name,
                category=tag.category,
            )

            flash("标签创建成功", "success")
            return redirect(url_for("tags.index"))

        except Exception as e:
            db.session.rollback()
            log_error(
                "标签创建失败",
                module="tags",
                error=str(e),
            )
            flash(f"标签创建失败: {str(e)}", "error")

    return render_template("tags/create.html", color_options=ThemeColors.COLOR_MAP)


@tags_bp.route("/api/edit/<int:tag_id>", methods=["POST"])
@login_required
@update_required
@require_csrf
def edit_api(tag_id: int) -> tuple[Response, int]:
    """编辑标签API"""
    tag = Tag.query.get_or_404(tag_id)
    data = request.get_json(silent=True) if request.is_json else request.form

    # 验证必填字段
    required_fields = ["name", "display_name", "category"]
    validation_error = validate_required_fields(data, required_fields)
    if validation_error:
        raise ValidationError(
            validation_error,
            message_key="VALIDATION_ERROR",
            extra={"fields": required_fields, "tag_id": tag_id},
        )

    # 获取表单数据
    name = (data.get("name") or "").strip()
    display_name = (data.get("display_name") or "").strip()
    category = (data.get("category") or "").strip()
    color = (data.get("color") or "primary").strip()
    description = (data.get("description") or "").strip()

    if request.is_json:
        sort_raw = data.get("sort_order", tag.sort_order)
        try:
            sort_order = int(sort_raw)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"排序值格式错误: {exc}",
                message_key="INVALID_REQUEST",
                extra={"sort_order": sort_raw},
            ) from exc
        is_active_raw = data.get("is_active", tag.is_active)
    else:
        sort_order = data.get("sort_order", type=int)
        sort_order = sort_order if sort_order is not None else tag.sort_order
        is_active_raw = data.get("is_active", "on" if tag.is_active else "off")

    if isinstance(is_active_raw, str):
        is_active = is_active_raw.lower() in {"on", "true", "1", "yes"}
    else:
        is_active = bool(is_active_raw)

    # 验证颜色
    if not ThemeColors.is_valid_color(color):
        raise ValidationError(
            f"无效的颜色选择: {color}",
            message_key="INVALID_REQUEST",
            extra={"color": color},
        )

    # 验证标签名称唯一性（排除当前标签）
    existing_tag = Tag.query.filter(Tag.name == name, Tag.id != tag_id).first()
    if existing_tag:
        raise ConflictError(
            "标签名称已存在",
            extra={"name": name, "tag_id": tag_id},
        )

    # 更新标签信息
    tag.name = name
    tag.display_name = display_name
    tag.category = category
    tag.color = color
    tag.description = description
    tag.sort_order = sort_order
    tag.is_active = is_active

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "更新标签失败",
            module="tags",
            user_id=current_user.id,
            tag_id=tag.id,
            payload={
                "name": name,
                "display_name": display_name,
                "category": category,
            },
            exception=exc,
        )
        raise

    log_info(
        "更新标签",
        module="tags",
        user_id=current_user.id,
        tag_id=tag.id,
        tag_name=tag.name,
        category=tag.category,
        is_active=tag.is_active,
    )

    return jsonify_unified_success(
        data={"tag": tag.to_dict()},
        message="标签更新成功",
    )


@tags_bp.route("/edit/<int:tag_id>", methods=["GET", "POST"])
@login_required
@update_required
@require_csrf
def edit(tag_id: int) -> str | Response:
    """编辑标签"""
    tag = Tag.query.get_or_404(tag_id)

    if request.method == "POST":
        try:
            # 验证必填字段
            required_fields = ["name", "display_name", "category"]
            validation_error = validate_required_fields(request.form, required_fields)
            if validation_error:
                flash(validation_error, "error")
                return render_template("tags/edit.html", tag=tag, color_options=ThemeColors.COLOR_MAP)

            # 获取表单数据
            name = request.form.get("name", "").strip()
            display_name = request.form.get("display_name", "").strip()
            category = request.form.get("category", "").strip()
            color = request.form.get("color", "primary").strip()
            description = request.form.get("description", "").strip()
            sort_order = request.form.get("sort_order", 0, type=int)
            is_active = request.form.get("is_active") == "on"

            # 验证颜色
            if not ThemeColors.is_valid_color(color):
                flash(f"无效的颜色选择: {color}", "error")
                return render_template("tags/edit.html", tag=tag, color_options=ThemeColors.COLOR_MAP)

            # 检查名称是否已存在（排除当前记录）
            existing_tag = Tag.query.filter(
                Tag.name == name,
                Tag.id != tag_id
            ).first()
            if existing_tag:
                flash(f"标签代码 '{name}' 已存在", "error")
                return render_template("tags/edit.html", tag=tag, color_options=ThemeColors.COLOR_MAP)

            # 更新标签
            tag.name = name
            tag.display_name = display_name
            tag.category = category
            tag.color = color
            tag.description = description
            tag.sort_order = sort_order
            tag.is_active = is_active

            db.session.commit()

            log_info(
                "标签更新成功",
                module="tags",
                tag_id=tag.id,
                name=tag.name,
                display_name=tag.display_name,
                category=tag.category,
            )

            flash("标签更新成功", "success")
            return redirect(url_for("tags.index"))

        except Exception as e:
            db.session.rollback()
            log_error(
                "标签更新失败",
                module="tags",
                tag_id=tag_id,
                error=str(e),
            )
            flash(f"标签更新失败: {str(e)}", "error")

    return render_template("tags/edit.html", tag=tag, color_options=ThemeColors.COLOR_MAP)


@tags_bp.route("/api/delete/<int:tag_id>", methods=["POST"])
@login_required
@delete_required
@require_csrf
def delete(tag_id: int) -> Response:
    """删除标签"""
    try:
        tag = Tag.query.get_or_404(tag_id)

        # 检查是否有实例使用此标签
        instance_count = len(tag.instances)
        if instance_count > 0:
            flash(f"无法删除标签 '{tag.display_name}'，还有 {instance_count} 个实例正在使用", "error")
            return redirect(url_for("tags.index"))

        # 硬删除标签 - 先删除关联关系，再删除标签
        # 删除实例标签关联关系
        db.session.execute(
            db.text("DELETE FROM instance_tags WHERE tag_id = :tag_id"),
            {"tag_id": tag_id}
        )
        
        # 删除标签
        db.session.delete(tag)
        db.session.commit()

        log_info(
            "标签删除成功",
            module="tags",
            tag_id=tag_id,
            name=tag.name,
            display_name=tag.display_name,
        )

        flash("标签删除成功", "success")
        return redirect(url_for("tags.index"))

    except Exception as e:
        db.session.rollback()
        log_error(
            "标签删除失败",
            module="tags",
            tag_id=tag_id,
            error=str(e),
        )
        flash(f"标签删除失败: {str(e)}", "error")
        return redirect(url_for("tags.index"))


@tags_bp.route("/api/tags")
@login_required
@view_required
def api_tags() -> tuple[Response, int]:
    """获取标签列表API"""
    category = request.args.get("category", "", type=str)
    if category:
        tags = Tag.get_tags_by_category(category)
    else:
        tags = Tag.get_active_tags()

    tags_data = [tag.to_dict() for tag in tags]

    return jsonify_unified_success(
        data={
            "tags": tags_data,
            "category": category or None,
        }
    )


@tags_bp.route("/api/categories")
@login_required
@view_required
def api_categories() -> tuple[Response, int]:
    """获取标签分类列表API"""
    categories = Tag.get_category_choices()
    return jsonify_unified_success(data={"categories": categories})


@tags_bp.route("/api/tags/<tag_name>")
@login_required
@view_required
def api_tag_detail(tag_name: str) -> tuple[Response, int]:
    """获取标签详情API"""
    tag = Tag.get_tag_by_name(tag_name)
    if not tag:
        raise NotFoundError(
            "标签不存在",
            extra={"tag_name": tag_name},
        )

    return jsonify_unified_success(
        data={"tag": tag.to_dict()},
        message="获取标签详情成功",
    )
