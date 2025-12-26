"""鲸落 - 标签批量操作路由."""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_restx import marshal

from app.constants import FlashCategory, UserRole
from app.constants.system_constants import ErrorMessages
from app.errors import NotFoundError, ValidationError
from app.models.instance import Instance
from app.models.tag import Tag
from app.routes.tags.restx_models import TAGGABLE_INSTANCE_FIELDS, TAG_OPTION_FIELDS
from app.services.tags.tag_options_service import TagOptionsService
from app.types import RouteReturn
from app.utils.decorators import create_required, require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info

# 创建蓝图
tags_bulk_bp = Blueprint("tags_bulk", __name__)


@tags_bulk_bp.route("/api/assign", methods=["POST"])
@login_required
@create_required
@require_csrf
def batch_assign_tags() -> tuple[Response, int]:
    """批量分配标签给实例.

    Returns:
        (JSON 响应, HTTP 状态码),包含分配统计.

    Raises:
        ValidationError: 当参数无效时抛出.
        NotFoundError: 当实例或标签不存在时抛出.

    """
    payload = request.get_json(silent=True) or {}

    def _execute() -> tuple[Response, int]:
        if not payload:
            raise ValidationError(
                ErrorMessages.REQUEST_DATA_EMPTY,
                message_key="REQUEST_DATA_EMPTY",
                extra={"permission_type": "create", "route": "tags_bulk.assign"},
            )

        instance_ids_raw = payload.get("instance_ids", [])
        tag_ids_raw = payload.get("tag_ids", [])

        try:
            instance_ids = [int(item) for item in instance_ids_raw]
            tag_ids = [int(item) for item in tag_ids_raw]
        except (TypeError, ValueError) as exc:
            msg = f"ID格式错误: {exc}"
            raise ValidationError(
                msg,
                message_key="INVALID_REQUEST",
                extra={"instance_ids": instance_ids_raw, "tag_ids": tag_ids_raw},
            ) from exc

        if not instance_ids or not tag_ids:
            missing_message = ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids, tag_ids")
            raise ValidationError(
                missing_message,
                message_key="MISSING_REQUIRED_FIELDS",
                extra={"instance_ids": instance_ids, "tag_ids": tag_ids},
            )

        instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()

        if not instances:
            msg = "未找到任何实例"
            raise NotFoundError(msg, extra={"instance_ids": instance_ids})
        if not tags:
            msg = "未找到任何标签"
            raise NotFoundError(msg, extra={"tag_ids": tag_ids})

        log_info(
            "开始批量分配标签",
            module="tags_bulk",
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            found_instances=len(instances),
            found_tags=len(tags),
            user_id=current_user.id,
        )

        assigned_count = 0
        for instance in instances:
            for tag in tags:
                if tag not in instance.tags:
                    instance.tags.append(tag)
                    assigned_count += 1

        log_info(
            "批量分配标签成功",
            module="tags_bulk",
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            assigned_count=assigned_count,
            user_id=current_user.id,
        )

        return jsonify_unified_success(
            data={
                "assigned_count": assigned_count,
                "instance_ids": instance_ids,
                "tag_ids": tag_ids,
            },
            message=f"标签批量分配成功,共分配 {assigned_count} 个标签关系",
        )

    return safe_route_call(
        _execute,
        module="tags_bulk",
        action="batch_assign_tags",
        public_error="批量分配标签失败",
        context={"route": "tags_bulk.assign"},
        expected_exceptions=(ValidationError, NotFoundError),
    )


@tags_bulk_bp.route("/api/remove", methods=["POST"])
@login_required
@create_required
@require_csrf
def batch_remove_tags() -> tuple[Response, int]:
    """批量移除实例的标签.

    Returns:
        (JSON 响应, HTTP 状态码),包含移除统计.

    Raises:
        ValidationError: 当参数无效时抛出.
        NotFoundError: 当实例或标签不存在时抛出.

    """
    payload = request.get_json(silent=True) or {}

    def _execute() -> tuple[Response, int]:
        if not payload:
            raise ValidationError(
                ErrorMessages.REQUEST_DATA_EMPTY,
                message_key="REQUEST_DATA_EMPTY",
                extra={"permission_type": "create", "route": "tags_bulk.remove"},
            )

        instance_ids_raw = payload.get("instance_ids", [])
        tag_ids_raw = payload.get("tag_ids", [])

        try:
            instance_ids = [int(item) for item in instance_ids_raw]
            tag_ids = [int(item) for item in tag_ids_raw]
        except (TypeError, ValueError) as exc:
            msg = f"ID格式错误: {exc}"
            raise ValidationError(
                msg,
                message_key="INVALID_REQUEST",
                extra={"instance_ids": instance_ids_raw, "tag_ids": tag_ids_raw},
            ) from exc

        if not instance_ids or not tag_ids:
            missing_message = ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids, tag_ids")
            raise ValidationError(
                missing_message,
                message_key="MISSING_REQUIRED_FIELDS",
                extra={"instance_ids": instance_ids, "tag_ids": tag_ids},
            )

        instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()

        if not instances:
            msg = "未找到任何实例"
            raise NotFoundError(msg, extra={"instance_ids": instance_ids})
        if not tags:
            msg = "未找到任何标签"
            raise NotFoundError(msg, extra={"tag_ids": tag_ids})

        log_info(
            "开始批量移除标签",
            module="tags_bulk",
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            found_instances=len(instances),
            found_tags=len(tags),
            user_id=current_user.id,
        )

        removed_count = 0
        for instance in instances:
            for tag in tags:
                if tag in instance.tags:
                    instance.tags.remove(tag)
                    removed_count += 1

        log_info(
            "批量移除标签成功",
            module="tags_bulk",
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            removed_count=removed_count,
            user_id=current_user.id,
        )

        return jsonify_unified_success(
            data={
                "removed_count": removed_count,
                "instance_ids": instance_ids,
                "tag_ids": tag_ids,
            },
            message=f"标签批量移除成功,共移除 {removed_count} 个标签关系",
        )

    return safe_route_call(
        _execute,
        module="tags_bulk",
        action="batch_remove_tags",
        public_error="批量移除标签失败",
        context={"route": "tags_bulk.remove"},
        expected_exceptions=(ValidationError, NotFoundError),
    )


@tags_bulk_bp.route("/api/instance-tags", methods=["POST"])
@login_required
@view_required
@require_csrf
def list_instance_tags() -> tuple[Response, int]:
    """获取实例的已关联标签 API.

    Returns:
        (JSON 响应, HTTP 状态码),包含标签列表和分类名称映射.

    Raises:
        ValidationError: 当参数无效时抛出.
        NotFoundError: 当实例不存在时抛出.

    """
    data = request.get_json(silent=True) or {}
    def _execute() -> tuple[Response, int]:
        if not data:
            raise ValidationError(
                ErrorMessages.REQUEST_DATA_EMPTY,
                message_key="REQUEST_DATA_EMPTY",
                extra={"route": "tags_bulk.list_instance_tags"},
            )

        instance_ids_raw = data.get("instance_ids", [])

        try:
            instance_ids = [int(item) for item in instance_ids_raw]
        except (TypeError, ValueError) as exc:
            msg = f"ID格式错误: {exc}"
            raise ValidationError(
                msg,
                message_key="INVALID_REQUEST",
                extra={"instance_ids": instance_ids_raw},
            ) from exc

        if not instance_ids:
            missing_message = ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids")
            raise ValidationError(
                missing_message,
                message_key="MISSING_REQUIRED_FIELDS",
                extra={"instance_ids": instance_ids},
            )

        instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
        if not instances:
            msg = "未找到任何实例"
            raise NotFoundError(msg, extra={"instance_ids": instance_ids})

        all_tags = set()
        for instance in instances:
            all_tags.update(instance.tags)

        tags_data = [tag.to_dict() for tag in all_tags]
        category_choices = Tag.get_category_choices()
        category_names = dict(category_choices)

        return jsonify_unified_success(
            data={
                "tags": tags_data,
                "category_names": category_names,
                "instance_ids": instance_ids,
            },
        )

    return safe_route_call(
        _execute,
        module="tags_bulk",
        action="list_instance_tags",
        public_error="获取实例标签失败",
        expected_exceptions=(ValidationError, NotFoundError),
        context={"route": "tags_bulk.list_instance_tags"},
    )


@tags_bulk_bp.route("/api/remove-all", methods=["POST"])
@login_required
@create_required
@require_csrf
def batch_remove_all_tags() -> tuple[Response, int]:
    """批量移除实例的所有标签.

    清空指定实例的所有标签关联.

    Returns:
        (JSON 响应, HTTP 状态码),包含移除统计.

    Raises:
        ValidationError: 当参数无效时抛出.
        NotFoundError: 当实例不存在时抛出.

    """
    payload = request.get_json(silent=True) or {}

    def _execute() -> tuple[Response, int]:
        if not payload:
            raise ValidationError(
                ErrorMessages.REQUEST_DATA_EMPTY,
                message_key="REQUEST_DATA_EMPTY",
                extra={"permission_type": "create", "route": "tags_bulk.remove_all"},
            )

        instance_ids_raw = payload.get("instance_ids", [])

        try:
            instance_ids = [int(item) for item in instance_ids_raw]
        except (TypeError, ValueError) as exc:
            msg = f"ID格式错误: {exc}"
            raise ValidationError(
                msg,
                message_key="INVALID_REQUEST",
                extra={"instance_ids": instance_ids_raw},
            ) from exc

        if not instance_ids:
            missing_message = ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids")
            raise ValidationError(
                missing_message,
                message_key="MISSING_REQUIRED_FIELDS",
                extra={"instance_ids": instance_ids},
            )

        instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
        if not instances:
            msg = "未找到任何实例"
            raise NotFoundError(msg, extra={"instance_ids": instance_ids})

        total_removed = 0
        for instance in instances:
            current_tags = list(instance.tags.all())
            tag_count = len(current_tags)
            log_info(
                "实例标签统计",
                module="tags_bulk",
                instance_id=instance.id,
                instance_name=instance.name,
                tag_count=tag_count,
                user_id=current_user.id,
            )

            for tag in current_tags:
                instance.tags.remove(tag)
            total_removed += tag_count

            log_info(
                "实例标签已清空",
                module="tags_bulk",
                instance_id=instance.id,
                instance_name=instance.name,
                user_id=current_user.id,
            )

        log_info(
            "批量移除所有标签成功",
            module="tags_bulk",
            instance_ids=instance_ids,
            removed_count=total_removed,
            user_id=current_user.id,
        )

        return jsonify_unified_success(
            data={
                "removed_count": total_removed,
                "instance_ids": instance_ids,
            },
            message=f"批量移除成功,共移除 {total_removed} 个标签关系",
        )

    return safe_route_call(
        _execute,
        module="tags_bulk",
        action="batch_remove_all_tags",
        public_error="批量移除所有标签失败",
        context={"route": "tags_bulk.remove_all"},
        expected_exceptions=(ValidationError, NotFoundError),
    )


@tags_bulk_bp.route("/api/instances")
@login_required
@view_required
def list_taggable_instances() -> tuple[Response, int]:
    """获取所有实例列表 API.

    Returns:
        tuple[Response, int]: 实例列表 JSON 与状态码.

    """
    def _execute() -> tuple[Response, int]:
        result = TagOptionsService().list_taggable_instances()
        instances_data = marshal(result.instances, TAGGABLE_INSTANCE_FIELDS)
        return jsonify_unified_success(data={"instances": instances_data})

    return safe_route_call(
        _execute,
        module="tags_bulk",
        action="list_taggable_instances",
        public_error="获取实例列表失败",
        context={"endpoint": "tags_bulk.instances"},
    )


@tags_bulk_bp.route("/api/tags")
@login_required
@view_required
def list_all_tags() -> tuple[Response, int]:
    """获取所有标签列表 API(包括非活跃标签).

    Returns:
        tuple[Response, int]: 标签与分类信息的 JSON.

    """
    def _execute() -> tuple[Response, int]:
        result = TagOptionsService().list_all_tags()
        tags_data = marshal(result.tags, TAG_OPTION_FIELDS)
        return jsonify_unified_success(
            data={
                "tags": tags_data,
                "category_names": result.category_names,
            },
        )

    return safe_route_call(
        _execute,
        module="tags_bulk",
        action="list_all_tags",
        public_error="获取标签列表失败",
        context={"endpoint": "tags_bulk.tags"},
    )


@tags_bulk_bp.route("/assign")
@login_required
@view_required
def batch_assign() -> RouteReturn:
    """批量分配标签页面.

    仅管理员可访问.

    Returns:
        渲染的批量分配页面或重定向到标签列表.

    """
    if current_user.role != UserRole.ADMIN:
        flash("您没有权限访问此页面", FlashCategory.ERROR)
        return redirect(url_for("tags.index"))

    return render_template("tags/bulk/assign.html")
