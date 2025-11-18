
"""
鲸落 - 标签管理路由
"""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models.tag import Tag
from app.constants import FlashCategory, HttpMethod
from app.errors import ConflictError, ValidationError, NotFoundError
from app.utils.decorators import create_required, delete_required, require_csrf, update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.constants.filter_options import STATUS_ACTIVE_OPTIONS
from app.utils.query_filter_utils import get_tag_categories
from app.services.form_service.tags_form_service import TagFormService
from app.utils.data_validator import sanitize_form_data

# 创建蓝图
tags_bp = Blueprint("tags", __name__)
_tag_form_service = TagFormService()


@tags_bp.route("/")
@login_required
@view_required
def index() -> str:
    """标签管理首页"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    status_param = request.args.get("status", "all", type=str)
    status_filter = status_param if status_param not in {"", "all"} else ""

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

    if status_filter == "active":
        query = query.filter_by(is_active=True)
    elif status_filter == "inactive":
        query = query.filter_by(is_active=False)
    # 移除软删除相关逻辑，因为现在使用硬删除

    # 排序
    query = query.order_by(Tag.category, Tag.sort_order, Tag.name)

    # 分页
    tags = query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    # 获取分类选项
    category_options = [{"value": "", "label": "全部分类"}] + get_tag_categories()
    status_options = STATUS_ACTIVE_OPTIONS

    return render_template(
        "tags/index.html",
        tags=tags,
        search=search,
        category=category,
        status=status_param,
        category_options=category_options,
        status_options=status_options,
    )


@tags_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_api() -> tuple[Response, int]:
    """创建标签API"""
    payload = sanitize_form_data(request.get_json(silent=True) if request.is_json else request.form or {})
    result = _tag_form_service.upsert(payload)
    if not result.success or not result.data:
        raise ValidationError(result.message or "标签创建失败", message_key="VALIDATION_ERROR")
    tag = result.data

    return jsonify_unified_success(
        data={"tag": tag.to_dict()},
        message="标签创建成功",
        status=HttpStatus.CREATED,
    )


@tags_bp.route("/api/edit/<int:tag_id>", methods=["POST"])
@login_required
@update_required
@require_csrf
def edit_api(tag_id: int) -> tuple[Response, int]:
    """编辑标签API"""
    tag = Tag.query.get_or_404(tag_id)
    payload = sanitize_form_data(request.get_json(silent=True) if request.is_json else request.form or {})
    result = _tag_form_service.upsert(payload, tag)
    if not result.success or not result.data:
        raise ValidationError(result.message or "标签更新失败", message_key="VALIDATION_ERROR")
    tag = result.data

    return jsonify_unified_success(
        data={"tag": tag.to_dict()},
        message="标签更新成功",
    )


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
            flash(f"无法删除标签 '{tag.display_name}'，还有 {instance_count} 个实例正在使用", FlashCategory.ERROR)
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

        flash("标签删除成功", FlashCategory.SUCCESS)
        return redirect(url_for("tags.index"))

    except Exception as e:
        db.session.rollback()
        log_error(
            "标签删除失败",
            module="tags",
            tag_id=tag_id,
            error=str(e),
        )
        flash(f"标签删除失败: {str(e)}", FlashCategory.ERROR)
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


# ---------------------------------------------------------------------------
# 表单页面已退役，全部通过列表页模态 + API 处理
