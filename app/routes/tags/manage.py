"""鲸落 - 标签管理路由."""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.constants import STATUS_ACTIVE_OPTIONS, FlashCategory, HttpStatus
from app.errors import NotFoundError, SystemError, ValidationError
from app.models.tag import Tag, instance_tags
from app.services.form_service.tag_service import TagFormService
from app.utils.data_validator import sanitize_form_data
from app.utils.decorators import create_required, delete_required, require_csrf, update_required, view_required
from app.utils.query_filter_utils import get_tag_categories
from app.utils.response_utils import jsonify_unified_error_message, jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.structlog_config import log_info

# 创建蓝图
tags_bp = Blueprint("tags", __name__)
_tag_form_service = TagFormService()


def _prefers_json_response() -> bool:
    return request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _calculate_tag_stats() -> dict[str, int]:
    """统计标签总数、启用/停用数量以及分类数量.

    Returns:
        dict[str, int]: 标签统计数据.

    """
    total_tags = db.session.query(db.func.count(Tag.id)).scalar() or 0
    active_tags = db.session.query(db.func.count(Tag.id)).filter(Tag.is_active.is_(True)).scalar() or 0
    inactive_tags = db.session.query(db.func.count(Tag.id)).filter(Tag.is_active.is_(False)).scalar() or 0
    category_count = db.session.query(db.func.count(db.func.distinct(Tag.category))).scalar() or 0
    return {
        "total": total_tags,
        "active": active_tags,
        "inactive": inactive_tags,
        "category_count": category_count,
    }


def _delete_tag_record(tag: Tag, operator_id: int | None = None) -> None:
    with db.session.begin():
        db.session.execute(instance_tags.delete().where(instance_tags.c.tag_id == tag.id))
        db.session.delete(tag)
    log_info(
        "标签删除成功",
        module="tags",
        user_id=operator_id,
        tag_id=tag.id,
        name=tag.name,
        display_name=tag.display_name,
    )


@tags_bp.route("/")
@login_required
@view_required
def index() -> str:
    """标签管理首页.

    渲染标签管理页面,支持搜索、分类和状态筛选.

    Returns:
        渲染后的 HTML 页面.

    Query Parameters:
        search: 搜索关键词,可选.
        category: 标签分类,可选.
        status: 状态筛选('all'、'active'、'inactive'),默认 'all'.

    """
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    status_param = request.args.get("status", "all", type=str)

    # 获取分类选项
    category_options = [{"value": "", "label": "全部分类"}, *get_tag_categories()]
    status_options = STATUS_ACTIVE_OPTIONS

    return render_template(
        "tags/index.html",
        search=search,
        category=category,
        status=status_param,
        category_options=category_options,
        status_options=status_options,
        tag_stats=_calculate_tag_stats(),
    )


@tags_bp.route("/api/create", methods=["POST"])
@login_required
@create_required
@require_csrf
def create_tag() -> tuple[Response, int]:
    """创建标签 API.

    Returns:
        (JSON 响应, HTTP 状态码).

    Raises:
        ValidationError: 当表单验证失败时抛出.

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
def update_tag(tag_id: int) -> tuple[Response, int]:
    """编辑标签 API.

    Args:
        tag_id: 标签 ID.

    Returns:
        tuple[Response, int]: 更新后的标签 JSON 与状态码.

    """
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
    """删除标签.

    硬删除标签及其关联关系.如果标签正在被实例使用,则拒绝删除.

    Args:
        tag_id: 标签 ID.

    Returns:
        JSON 响应或重定向.

    Raises:
        NotFoundError: 当标签不存在时抛出.

    """
    tag = Tag.query.get_or_404(tag_id)
    prefers_json = _prefers_json_response()

    def _execute() -> Response:
        instance_count = len(tag.instances)
        if instance_count > 0:
            if prefers_json:
                return jsonify_unified_error_message(
                    f"标签 '{tag.display_name}' 仍被 {instance_count} 个实例使用,无法删除",
                    status_code=HttpStatus.CONFLICT,
                    message_key="TAG_IN_USE",
                    extra={"tag_id": tag_id, "instance_count": instance_count},
                )
            flash(
                f"无法删除标签 '{tag.display_name}',还有 {instance_count} 个实例正在使用",
                FlashCategory.ERROR,
            )
            return redirect(url_for("tags.index"))

        _delete_tag_record(tag, operator_id=getattr(current_user, "id", None))

        if prefers_json:
            return jsonify_unified_success(
                data={"tag_id": tag_id},
                message="标签删除成功",
            )

        flash("标签删除成功", FlashCategory.SUCCESS)
        return redirect(url_for("tags.index"))

    try:
        return safe_route_call(
            _execute,
            module="tags",
            action="delete_tag",
            public_error="删除标签失败",
            context={"tag_id": tag_id, "prefers_json": prefers_json},
        )
    except SystemError as exc:
        if prefers_json:
            raise
        flash(f"标签删除失败: {exc!s}", FlashCategory.ERROR)
        return redirect(url_for("tags.index"))


@tags_bp.route("/api/batch_delete", methods=["POST"])
@login_required
@delete_required
@require_csrf
def batch_delete_tags() -> tuple[Response, int]:
    """批量删除标签 API,返回每个标签的处理结果."""
    payload = request.get_json(silent=True) or {}

    def _execute() -> tuple[Response, int]:
        tag_ids = payload.get("tag_ids") or []
        if not isinstance(tag_ids, list) or not tag_ids:
            msg = "tag_ids 不能为空"
            raise ValidationError(msg)

        results: list[dict[str, object]] = []
        has_failure = False
        operator_id = getattr(current_user, "id", None)

        for raw_id in tag_ids:
            try:
                tag_id = int(raw_id)
            except (ValueError, TypeError):
                has_failure = True
                results.append({"tag_id": raw_id, "status": "invalid_id"})
                continue

            tag = Tag.query.get(tag_id)
            if not tag:
                has_failure = True
                results.append({"tag_id": tag_id, "status": "not_found"})
                continue

            instance_count = len(tag.instances)
            if instance_count > 0:
                has_failure = True
                results.append(
                    {
                        "tag_id": tag_id,
                        "status": "in_use",
                        "instance_count": instance_count,
                    },
                )
                continue

            try:
                _delete_tag_record(tag, operator_id=operator_id)
                results.append({"tag_id": tag_id, "status": "deleted"})
            except SQLAlchemyError as exc:  # pragma: no cover - 逐条记录方便排查
                db.session.rollback()
                has_failure = True
                log_with_context(
                    "warning",
                    "批量删除标签失败",
                    module="tags",
                    action="batch_delete_tags",
                    context={"tag_id": tag_id},
                    extra={"error_message": str(exc)},
                    include_actor=True,
                )
                results.append({"tag_id": tag_id, "status": "error", "message": str(exc)})

        status = HttpStatus.MULTI_STATUS if has_failure else HttpStatus.OK
        message = "部分标签未能删除" if has_failure else "标签批量删除成功"
        return jsonify_unified_success(data={"results": results}, message=message, status=status)

    return safe_route_call(
        _execute,
        module="tags",
        action="batch_delete_tags",
        public_error="批量删除标签失败",
        context={"count": len(payload.get("tag_ids") or [])},
        expected_exceptions=(ValidationError,),
    )


@tags_bp.route("/api/list")
@login_required
@view_required
def list_tags() -> tuple[Response, int]:
    """Grid.js 标签列表 API.

    支持分页、搜索和筛选,返回标签列表及实例数量统计.

    Returns:
        (JSON 响应, HTTP 状态码).

    Query Parameters:
        page: 页码,默认 1.
        limit: 每页数量,默认 20.
        search: 搜索关键词,可选.
        category: 分类筛选,可选.
        status: 状态筛选,可选.

    """
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    search = request.args.get("search", "", type=str)
    category = request.args.get("category", "", type=str)
    status_param = request.args.get("status", "all", type=str)
    status_filter = status_param if status_param not in {"", "all"} else ""

    instance_count_expr = db.func.count(instance_tags.c.instance_id)
    query = db.session.query(Tag, instance_count_expr.label("instance_count")).outerjoin(
        instance_tags, Tag.id == instance_tags.c.tag_id
    )

    if search:
        query = query.filter(
            db.or_(
                Tag.name.contains(search),
                Tag.display_name.contains(search),
                Tag.category.contains(search),
            ),
        )

    if category:
        query = query.filter(Tag.category == category)

    if status_filter == "active":
        query = query.filter(Tag.is_active.is_(True))
    elif status_filter == "inactive":
        query = query.filter(Tag.is_active.is_(False))

    query = query.group_by(Tag.id).order_by(
        Tag.category.asc(),
        Tag.display_name.asc(),
        Tag.name.asc(),
        Tag.created_at.desc(),
    )

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    items = []
    for tag, instance_count in pagination.items:
        payload = tag.to_dict()
        payload["instance_count"] = instance_count or 0
        items.append(payload)

    return jsonify_unified_success(
        data={
            "items": items,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "stats": _calculate_tag_stats(),
        },
    )


@tags_bp.route("/api/tags")
@login_required
@view_required
def list_tag_options() -> tuple[Response, int]:
    """获取标签列表 API.

    Returns:
        tuple[Response, int]: 标签列表 JSON 与状态码.

    """
    category = request.args.get("category", "", type=str)
    tags = Tag.get_tags_by_category(category) if category else Tag.get_active_tags()

    tags_data = [tag.to_dict() for tag in tags]

    return jsonify_unified_success(
        data={
            "tags": tags_data,
            "category": category or None,
        },
    )


@tags_bp.route("/api/categories")
@login_required
@view_required
def list_tag_categories() -> tuple[Response, int]:
    """获取标签分类列表 API.

    Returns:
        tuple[Response, int]: 分类列表 JSON 与状态码.

    """
    categories = Tag.get_category_choices()
    return jsonify_unified_success(data={"categories": categories})


@tags_bp.route("/api/tags/<tag_name>")
@login_required
@view_required
def get_tag_by_name(tag_name: str) -> tuple[Response, int]:
    """获取标签详情 API.

    Args:
        tag_name: 标签名称.

    Returns:
        tuple[Response, int]: 标签详情 JSON 与状态码.

    """
    tag = Tag.get_tag_by_name(tag_name)
    if not tag:
        msg = "标签不存在"
        raise NotFoundError(
            msg,
            extra={"tag_name": tag_name},
        )

    return jsonify_unified_success(
        data={"tag": tag.to_dict()},
        message="获取标签详情成功",
    )


@tags_bp.route("/api/<int:tag_id>")
@login_required
@view_required
def get_tag_by_id(tag_id: int) -> tuple[Response, int]:
    """根据 ID 获取标签详情.

    Args:
        tag_id: 标签 ID.

    Returns:
        tuple[Response, int]: 标签详情 JSON 与状态码.

    """
    tag = Tag.query.get_or_404(tag_id)
    return jsonify_unified_success(
        data={"tag": tag.to_dict()},
        message="获取标签详情成功",
    )


# ---------------------------------------------------------------------------
# 表单页面已退役,全部通过列表页模态 + API 处理
