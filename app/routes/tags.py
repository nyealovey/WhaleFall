
"""
鲸落 - 标签管理路由
"""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models.tag import Tag, instance_tags
from app.constants import FlashCategory, HttpMethod, HttpStatus, STATUS_ACTIVE_OPTIONS
from app.errors import ConflictError, ValidationError, NotFoundError
from app.utils.decorators import create_required, delete_required, require_csrf, update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
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
    """标签管理首页。

    渲染标签管理页面，支持搜索、分类和状态筛选。

    Returns:
        渲染后的 HTML 页面。

    Query Parameters:
        search: 搜索关键词，可选。
        category: 标签分类，可选。
        status: 状态筛选（'all'、'active'、'inactive'），默认 'all'。
    """
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    status_param = request.args.get("status", "all", type=str)
    status_filter = status_param if status_param not in {"", "all"} else ""

    # 获取分类选项
    category_options = [{"value": "", "label": "全部分类"}] + get_tag_categories()
    status_options = STATUS_ACTIVE_OPTIONS

    return render_template(
        "tags/index.html",
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
    """创建标签 API。

    Returns:
        (JSON 响应, HTTP 状态码)。

    Raises:
        ValidationError: 当表单验证失败时抛出。
    """
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
    """删除标签。

    硬删除标签及其关联关系。如果标签正在被实例使用，则拒绝删除。

    Args:
        tag_id: 标签 ID。

    Returns:
        JSON 响应或重定向。

    Raises:
        NotFoundError: 当标签不存在时抛出。
    """
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

        prefers_json = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if prefers_json:
            return jsonify_unified_success(
                data={"tag_id": tag_id},
                message="标签删除成功",
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
        prefers_json = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        if prefers_json:
            raise
        flash(f"标签删除失败: {str(e)}", FlashCategory.ERROR)
        return redirect(url_for("tags.index"))


@tags_bp.route("/api/list")
@login_required
@view_required
def list_tags_api() -> tuple[Response, int]:
    """Grid.js 标签列表 API。

    支持分页、排序、搜索和筛选，返回标签列表及实例数量统计。

    Returns:
        (JSON 响应, HTTP 状态码)。

    Query Parameters:
        page: 页码，默认 1。
        limit: 每页数量，默认 20。
        sort: 排序字段，默认 'sort_order'。
        order: 排序方向（'asc'、'desc'），默认 'asc'。
        search: 搜索关键词，可选。
        category: 分类筛选，可选。
        status: 状态筛选，可选。
    """
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    sort_field = request.args.get("sort", "sort_order")
    sort_order = request.args.get("order", "asc")
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    status_param = request.args.get("status", "all", type=str)
    status_filter = status_param if status_param not in {"", "all"} else ""

    instance_count_expr = db.func.count(instance_tags.c.instance_id)
    query = (
        db.session.query(Tag, instance_count_expr.label("instance_count"))
        .outerjoin(instance_tags, Tag.id == instance_tags.c.tag_id)
    )

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
        query = query.filter(Tag.is_active.is_(True))
    elif status_filter == "inactive":
        query = query.filter(Tag.is_active.is_(False))

    sortable_fields = {
        "sort_order": Tag.sort_order,
        "name": Tag.name,
        "display_name": Tag.display_name,
        "category": Tag.category,
        "is_active": Tag.is_active,
        "instance_count": instance_count_expr,
        "created_at": Tag.created_at,
        "updated_at": Tag.updated_at,
    }
    order_column = sortable_fields.get(sort_field, Tag.sort_order)
    if sort_order == "desc":
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())

    pagination = query.group_by(Tag.id).paginate(page=page, per_page=limit, error_out=False)
    items = []
    for tag, instance_count in pagination.items:
        payload = tag.to_dict()
        payload.update(
            {
                "instance_count": instance_count or 0,
                "sort_order": tag.sort_order,
                "category": tag.category,
            }
        )
        items.append(payload)

    return jsonify_unified_success(
        data={
            "items": items,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
        }
    )


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


@tags_bp.route("/api/<int:tag_id>")
@login_required
@view_required
def api_tag_detail_by_id(tag_id: int) -> tuple[Response, int]:
    """根据 ID 获取标签详情"""
    tag = Tag.query.get_or_404(tag_id)
    return jsonify_unified_success(
        data={"tag": tag.to_dict()},
        message="获取标签详情成功",
    )


# ---------------------------------------------------------------------------
# 表单页面已退役，全部通过列表页模态 + API 处理
