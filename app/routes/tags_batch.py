"""
鲸落 - 标签批量操作路由
"""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.constants.system_constants import ErrorMessages
from app.errors import NotFoundError, ValidationError
from app.models.instance import Instance
from app.models.tag import Tag
from app.utils.decorators import create_required, require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
tags_batch_bp = Blueprint("tags_batch", __name__)


@tags_batch_bp.route("/api/batch_assign_tags", methods=["POST"])
@login_required
@create_required
@require_csrf
def batch_assign_tags() -> tuple[Response, int]:
    """批量分配标签给实例"""
    data = request.get_json(silent=True) or {}
    if not data:
        raise ValidationError(
            ErrorMessages.REQUEST_DATA_EMPTY,
            message_key="REQUEST_DATA_EMPTY",
            extra={"permission_type": "create", "route": "tags_batch.batch_assign_tags"},
        )

    instance_ids_raw = data.get("instance_ids", [])
    tag_ids_raw = data.get("tag_ids", [])

    try:
        instance_ids = [int(item) for item in instance_ids_raw]
        tag_ids = [int(item) for item in tag_ids_raw]
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"ID格式错误: {exc}",
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
        raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})
    if not tags:
        raise NotFoundError("未找到任何标签", extra={"tag_ids": tag_ids})

    log_info(
        "开始批量分配标签",
        module="tags_batch",
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

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "批量分配标签失败",
            module="tags_batch",
            user_id=current_user.id,
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            exception=exc,
        )
        raise

    log_info(
        "批量分配标签成功",
        module="tags_batch",
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
        message=f"标签批量分配成功，共分配 {assigned_count} 个标签关系",
    )


@tags_batch_bp.route("/api/batch_remove_tags", methods=["POST"])
@login_required
@create_required
@require_csrf
def batch_remove_tags() -> tuple[Response, int]:
    """批量移除实例的标签"""
    data = request.get_json(silent=True) or {}
    if not data:
        raise ValidationError(
            ErrorMessages.REQUEST_DATA_EMPTY,
            message_key="REQUEST_DATA_EMPTY",
            extra={"permission_type": "create", "route": "tags_batch.batch_remove_tags"},
        )

    instance_ids_raw = data.get("instance_ids", [])
    tag_ids_raw = data.get("tag_ids", [])

    try:
        instance_ids = [int(item) for item in instance_ids_raw]
        tag_ids = [int(item) for item in tag_ids_raw]
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"ID格式错误: {exc}",
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
        raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})
    if not tags:
        raise NotFoundError("未找到任何标签", extra={"tag_ids": tag_ids})

    log_info(
        "开始批量移除标签",
        module="tags_batch",
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

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "批量移除标签失败",
            module="tags_batch",
            user_id=current_user.id,
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            exception=exc,
        )
        raise

    log_info(
        "批量移除标签成功",
        module="tags_batch",
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
        message=f"标签批量移除成功，共移除 {removed_count} 个标签关系",
    )


@tags_batch_bp.route("/api/instance_tags", methods=["POST"])
@login_required
@view_required
@require_csrf
def api_instance_tags() -> tuple[Response, int]:
    """获取实例的已关联标签API"""
    data = request.get_json(silent=True) or {}
    if not data:
        raise ValidationError(
            ErrorMessages.REQUEST_DATA_EMPTY,
            message_key="REQUEST_DATA_EMPTY",
            extra={"route": "tags_batch.api_instance_tags"},
        )

    instance_ids_raw = data.get("instance_ids", [])

    try:
        instance_ids = [int(item) for item in instance_ids_raw]
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"ID格式错误: {exc}",
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
        raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})

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
        }
    )


@tags_batch_bp.route("/api/batch_remove_all_tags", methods=["POST"])
@login_required
@create_required
@require_csrf
def batch_remove_all_tags() -> tuple[Response, int]:
    """批量移除实例的所有标签"""
    data = request.get_json(silent=True) or {}
    if not data:
        raise ValidationError(
            ErrorMessages.REQUEST_DATA_EMPTY,
            message_key="REQUEST_DATA_EMPTY",
            extra={"permission_type": "create", "route": "tags_batch.batch_remove_all_tags"},
        )

    instance_ids_raw = data.get("instance_ids", [])

    try:
        instance_ids = [int(item) for item in instance_ids_raw]
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"ID格式错误: {exc}",
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
        raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})

    total_removed = 0
    for instance in instances:
        current_tags = list(instance.tags.all())
        tag_count = len(current_tags)
        log_info(
            "实例标签统计",
            module="tags_batch",
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
            module="tags_batch",
            instance_id=instance.id,
            instance_name=instance.name,
            user_id=current_user.id,
        )

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "批量移除所有标签失败",
            module="tags_batch",
            user_id=current_user.id,
            instance_ids=instance_ids,
            exception=exc,
        )
        raise

    log_info(
        "批量移除所有标签成功",
        module="tags_batch",
        instance_ids=instance_ids,
        removed_count=total_removed,
        user_id=current_user.id,
    )

    return jsonify_unified_success(
        data={
            "removed_count": total_removed,
            "instance_ids": instance_ids,
        },
        message=f"批量移除成功，共移除 {total_removed} 个标签关系",
    )


@tags_batch_bp.route("/api/instances")
@login_required
@view_required
def api_instances() -> tuple[Response, int]:
    """获取所有实例列表API"""
    instances = Instance.query.all()
    instances_data = [
        {
            "id": instance.id,
            "name": instance.name,
            "host": instance.host,
            "port": instance.port,
            "db_type": instance.db_type,
        }
        for instance in instances
    ]
    return jsonify_unified_success(data={"instances": instances_data})


@tags_batch_bp.route("/api/all_tags")
@login_required
@view_required
def api_all_tags() -> tuple[Response, int]:
    """获取所有标签列表API (包括非活跃标签)"""
    tags = Tag.query.all()
    tags_data = [tag.to_dict() for tag in tags]

    category_choices = Tag.get_category_choices()
    category_names = dict(category_choices)

    return jsonify_unified_success(
        data={
            "tags": tags_data,
            "category_names": category_names,
        }
    )


@tags_batch_bp.route("/batch_assign")
@login_required
@view_required
def batch_assign() -> str:
    """批量分配标签页面"""
    if current_user.role != "admin":
        flash("您没有权限访问此页面", "error")
        return redirect(url_for("tags.index"))

    return render_template("tags/batch_assign.html")

