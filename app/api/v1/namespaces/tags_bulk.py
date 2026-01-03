"""Tags bulk namespace (Phase 4C 标签批量操作)."""

from __future__ import annotations

from typing import ClassVar

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.constants.system_constants import ErrorMessages
from app.errors import NotFoundError, ValidationError
from app.models.instance import Instance
from app.models.tag import Tag
from app.routes.tags.restx_models import TAG_OPTION_FIELDS, TAGGABLE_INSTANCE_FIELDS
from app.services.tags.tag_options_service import TagOptionsService
from app.utils.decorators import require_csrf
from app.utils.structlog_config import log_info

ns = Namespace("tags_bulk", description="标签批量操作")

ErrorEnvelope = get_error_envelope_model(ns)

TaggableInstanceModel = ns.model("TaggableInstance", TAGGABLE_INSTANCE_FIELDS)
TagOptionModel = ns.model("TagOption", TAG_OPTION_FIELDS)

TagsBulkInstancesData = ns.model(
    "TagsBulkInstancesData",
    {
        "instances": fields.List(fields.Nested(TaggableInstanceModel)),
    },
)
TagsBulkInstancesSuccessEnvelope = make_success_envelope_model(
    ns, "TagsBulkInstancesSuccessEnvelope", TagsBulkInstancesData
)

TagsBulkTagsData = ns.model(
    "TagsBulkTagsData",
    {
        "tags": fields.List(fields.Nested(TagOptionModel)),
        "category_names": fields.Raw(),
    },
)
TagsBulkTagsSuccessEnvelope = make_success_envelope_model(ns, "TagsBulkTagsSuccessEnvelope", TagsBulkTagsData)

TagBulkAssignPayload = ns.model(
    "TagBulkAssignPayload",
    {
        "instance_ids": fields.List(fields.Integer, required=True),
        "tag_ids": fields.List(fields.Integer, required=True),
    },
)

TagBulkAssignData = ns.model(
    "TagBulkAssignData",
    {
        "assigned_count": fields.Integer(),
        "instance_ids": fields.List(fields.Integer),
        "tag_ids": fields.List(fields.Integer),
    },
)
TagBulkAssignSuccessEnvelope = make_success_envelope_model(ns, "TagBulkAssignSuccessEnvelope", TagBulkAssignData)

TagBulkRemoveData = ns.model(
    "TagBulkRemoveData",
    {
        "removed_count": fields.Integer(),
        "instance_ids": fields.List(fields.Integer),
        "tag_ids": fields.List(fields.Integer),
    },
)
TagBulkRemoveSuccessEnvelope = make_success_envelope_model(ns, "TagBulkRemoveSuccessEnvelope", TagBulkRemoveData)

TagBulkRemoveAllPayload = ns.model(
    "TagBulkRemoveAllPayload",
    {
        "instance_ids": fields.List(fields.Integer, required=True),
    },
)

TagBulkRemoveAllData = ns.model(
    "TagBulkRemoveAllData",
    {
        "removed_count": fields.Integer(),
        "instance_ids": fields.List(fields.Integer),
    },
)
TagBulkRemoveAllSuccessEnvelope = make_success_envelope_model(
    ns, "TagBulkRemoveAllSuccessEnvelope", TagBulkRemoveAllData
)

TagBulkInstanceTagsPayload = ns.model(
    "TagBulkInstanceTagsPayload",
    {
        "instance_ids": fields.List(fields.Integer, required=True),
    },
)

TagBulkInstanceTagsData = ns.model(
    "TagBulkInstanceTagsData",
    {
        "tags": fields.Raw(),
        "category_names": fields.Raw(),
        "instance_ids": fields.List(fields.Integer),
    },
)
TagBulkInstanceTagsSuccessEnvelope = make_success_envelope_model(
    ns,
    "TagBulkInstanceTagsSuccessEnvelope",
    TagBulkInstanceTagsData,
)


@ns.route("/instances")
class TagsBulkInstancesResource(BaseResource):
    """批量标签-实例选项资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", TagsBulkInstancesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取可分配标签的实例列表."""

        def _execute():
            result = TagOptionsService().list_taggable_instances()
            instances_data = marshal(result.instances, TAGGABLE_INSTANCE_FIELDS)
            return self.success(data={"instances": instances_data}, message="操作成功")

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="list_taggable_instances",
            public_error="获取实例列表失败",
            context={"endpoint": "tags_bulk.instances"},
        )


@ns.route("/tags")
class TagsBulkTagsResource(BaseResource):
    """批量标签-标签选项资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", TagsBulkTagsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取标签选项."""

        def _execute():
            result = TagOptionsService().list_all_tags()
            tags_data = marshal(result.tags, TAG_OPTION_FIELDS)
            return self.success(
                data={
                    "tags": tags_data,
                    "category_names": result.category_names,
                },
                message="操作成功",
            )

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="list_all_tags",
            public_error="获取标签列表失败",
            context={"endpoint": "tags_bulk.tags"},
        )


@ns.route("/assign")
class TagsBulkAssignResource(BaseResource):
    """批量分配标签资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("create")]

    @ns.expect(TagBulkAssignPayload, validate=False)
    @ns.response(200, "OK", TagBulkAssignSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """批量分配标签."""
        payload = request.get_json(silent=True) or {}

        def _execute():
            if not payload:
                raise ValidationError(ErrorMessages.REQUEST_DATA_EMPTY, message_key="REQUEST_DATA_EMPTY")

            instance_ids_raw = payload.get("instance_ids", [])
            tag_ids_raw = payload.get("tag_ids", [])

            try:
                instance_ids = [int(item) for item in instance_ids_raw]
                tag_ids = [int(item) for item in tag_ids_raw]
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"ID格式错误: {exc}") from exc

            if not instance_ids or not tag_ids:
                raise ValidationError(ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids, tag_ids"))

            instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()

            if not instances:
                raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})
            if not tags:
                raise NotFoundError("未找到任何标签", extra={"tag_ids": tag_ids})

            log_info(
                "开始批量分配标签",
                module="tags_bulk",
                instance_ids=instance_ids,
                tag_ids=tag_ids,
                found_instances=len(instances),
                found_tags=len(tags),
                user_id=getattr(current_user, "id", None),
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
                user_id=getattr(current_user, "id", None),
            )

            return self.success(
                data={"assigned_count": assigned_count, "instance_ids": instance_ids, "tag_ids": tag_ids},
                message=f"标签批量分配成功,共分配 {assigned_count} 个标签关系",
            )

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="batch_assign_tags",
            public_error="批量分配标签失败",
            expected_exceptions=(ValidationError, NotFoundError),
            context={"route": "tags_bulk.assign"},
        )


@ns.route("/remove")
class TagsBulkRemoveResource(BaseResource):
    """批量移除标签资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("create")]

    @ns.expect(TagBulkAssignPayload, validate=False)
    @ns.response(200, "OK", TagBulkRemoveSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """批量移除标签."""
        payload = request.get_json(silent=True) or {}

        def _execute():
            if not payload:
                raise ValidationError(ErrorMessages.REQUEST_DATA_EMPTY, message_key="REQUEST_DATA_EMPTY")

            instance_ids_raw = payload.get("instance_ids", [])
            tag_ids_raw = payload.get("tag_ids", [])

            try:
                instance_ids = [int(item) for item in instance_ids_raw]
                tag_ids = [int(item) for item in tag_ids_raw]
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"ID格式错误: {exc}") from exc

            if not instance_ids or not tag_ids:
                raise ValidationError(ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids, tag_ids"))

            instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()

            if not instances:
                raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})
            if not tags:
                raise NotFoundError("未找到任何标签", extra={"tag_ids": tag_ids})

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
                user_id=getattr(current_user, "id", None),
            )

            return self.success(
                data={"removed_count": removed_count, "instance_ids": instance_ids, "tag_ids": tag_ids},
                message=f"标签批量移除成功,共移除 {removed_count} 个标签关系",
            )

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="batch_remove_tags",
            public_error="批量移除标签失败",
            expected_exceptions=(ValidationError, NotFoundError),
            context={"route": "tags_bulk.remove"},
        )


@ns.route("/instance-tags")
class TagsBulkInstanceTagsResource(BaseResource):
    """批量标签-实例标签资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.expect(TagBulkInstanceTagsPayload, validate=False)
    @ns.response(200, "OK", TagBulkInstanceTagsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """获取实例标签列表."""
        data = request.get_json(silent=True) or {}

        def _execute():
            if not data:
                raise ValidationError(ErrorMessages.REQUEST_DATA_EMPTY, message_key="REQUEST_DATA_EMPTY")

            instance_ids_raw = data.get("instance_ids", [])
            try:
                instance_ids = [int(item) for item in instance_ids_raw]
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"ID格式错误: {exc}") from exc

            if not instance_ids:
                raise ValidationError(ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids"))

            instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
            if not instances:
                raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})

            all_tags: set[Tag] = set()
            for instance in instances:
                all_tags.update(instance.tags)

            tags_data = [tag.to_dict() for tag in all_tags]
            category_names = dict(Tag.get_category_choices())
            return self.success(
                data={"tags": tags_data, "category_names": category_names, "instance_ids": instance_ids},
                message="操作成功",
            )

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="list_instance_tags",
            public_error="获取实例标签失败",
            expected_exceptions=(ValidationError, NotFoundError),
            context={"route": "tags_bulk.list_instance_tags"},
        )


@ns.route("/remove-all")
class TagsBulkRemoveAllResource(BaseResource):
    """批量移除所有标签资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("create")]

    @ns.expect(TagBulkRemoveAllPayload, validate=False)
    @ns.response(200, "OK", TagBulkRemoveAllSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """批量移除所有标签."""
        payload = request.get_json(silent=True) or {}

        def _execute():
            if not payload:
                raise ValidationError(ErrorMessages.REQUEST_DATA_EMPTY, message_key="REQUEST_DATA_EMPTY")

            instance_ids_raw = payload.get("instance_ids", [])
            try:
                instance_ids = [int(item) for item in instance_ids_raw]
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"ID格式错误: {exc}") from exc

            if not instance_ids:
                raise ValidationError(ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids"))

            instances = Instance.query.filter(Instance.id.in_(instance_ids)).all()
            if not instances:
                raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})

            total_removed = 0
            for instance in instances:
                current_tags = list(instance.tags.all())
                for tag in current_tags:
                    instance.tags.remove(tag)
                total_removed += len(current_tags)

            log_info(
                "批量移除所有标签成功",
                module="tags_bulk",
                instance_ids=instance_ids,
                removed_count=total_removed,
                user_id=getattr(current_user, "id", None),
            )

            return self.success(
                data={"removed_count": total_removed, "instance_ids": instance_ids},
                message=f"批量移除成功,共移除 {total_removed} 个标签关系",
            )

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="batch_remove_all_tags",
            public_error="批量移除所有标签失败",
            expected_exceptions=(ValidationError, NotFoundError),
            context={"route": "tags_bulk.remove_all"},
        )
