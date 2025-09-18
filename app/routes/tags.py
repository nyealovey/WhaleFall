"""
鲸落 - 标签管理路由
"""

from typing import Any

from flask import (
    Blueprint,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.models.tag import Tag
from app.utils.decorators import (
    create_required,
    delete_required,
    update_required,
    view_required,
)
from app.utils.security import sanitize_form_data, validate_required_fields
from app.utils.structlog_config import get_api_logger, get_system_logger, log_error, log_info

logger = get_system_logger()

# 创建蓝图
tags_bp = Blueprint("tags", __name__, url_prefix="/tags")


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
        category=category,
        status=status,
        categories=categories,
    )


@tags_bp.route("/create", methods=["GET", "POST"])
@login_required
@create_required
def create() -> str | Response:
    """创建标签"""
    if request.method == "POST":
        try:
            # 验证必填字段
            required_fields = ["name", "display_name", "category"]
            validation_error = validate_required_fields(request.form, required_fields)
            if validation_error:
                flash(validation_error, "error")
                return render_template("tags/create.html")

            # 获取表单数据
            name = request.form.get("name", "").strip()
            display_name = request.form.get("display_name", "").strip()
            category = request.form.get("category", "").strip()
            color = request.form.get("color", "primary").strip()
            description = request.form.get("description", "").strip()
            sort_order = request.form.get("sort_order", 0, type=int)
            is_active = request.form.get("is_active") == "on"

            # 检查名称是否已存在
            existing_tag = Tag.query.filter_by(name=name).first()
            if existing_tag:
                flash(f"标签代码 '{name}' 已存在", "error")
                return render_template("tags/create.html")

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

    return render_template("tags/create.html")


@tags_bp.route("/edit/<int:tag_id>", methods=["GET", "POST"])
@login_required
@update_required
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
                return render_template("tags/edit.html", tag=tag)

            # 获取表单数据
            name = request.form.get("name", "").strip()
            display_name = request.form.get("display_name", "").strip()
            category = request.form.get("category", "").strip()
            color = request.form.get("color", "primary").strip()
            description = request.form.get("description", "").strip()
            sort_order = request.form.get("sort_order", 0, type=int)
            is_active = request.form.get("is_active") == "on"

            # 检查名称是否已存在（排除当前记录）
            existing_tag = Tag.query.filter(
                Tag.name == name,
                Tag.id != tag_id
            ).first()
            if existing_tag:
                flash(f"标签代码 '{name}' 已存在", "error")
                return render_template("tags/edit.html", tag=tag)

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

    return render_template("tags/edit.html", tag=tag)


@tags_bp.route("/delete/<int:tag_id>", methods=["POST"])
@login_required
@delete_required
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
def api_tags() -> Response:
    """获取标签列表API"""
    try:
        category = request.args.get("category", "", type=str)
        if category:
            tags = Tag.get_tags_by_category(category)
        else:
            tags = Tag.get_active_tags()
        
        tags_data = [tag.to_dict() for tag in tags]

        return jsonify({
            "success": True,
            "tags": tags_data,
        })

    except Exception as e:
        log_error(
            "获取标签列表失败",
            module="tags",
            error=str(e),
        )
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@tags_bp.route("/api/tags/<tag_name>")
@login_required
@view_required
def api_tag_detail(tag_name: str) -> Response:
    """获取标签详情API"""
    try:
        tag = Tag.get_tag_by_name(tag_name)
        if not tag:
            return jsonify({
                "success": False,
                "error": "标签不存在",
            }), 404

        return jsonify({
            "success": True,
            "tag": tag.to_dict(),
        })

    except Exception as e:
        log_error(
            "获取标签详情失败",
            module="tags",
            tag_name=tag_name,
            error=str(e),
        )
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500
