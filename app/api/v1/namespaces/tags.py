"""Tags namespace (Phase 2 核心域迁移)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, ClassVar, cast

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.api.v1.restx_models.tags import TAG_LIST_ITEM_FIELDS, TAG_OPTION_FIELDS, TAGGABLE_INSTANCE_FIELDS
from app.core.constants import HttpStatus
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.types.tags import TagListFilters
from app.schemas.tags_query import TagOptionsQuery, TagsListQuery
from app.schemas.validation import validate_or_raise
from app.services.tags.tag_detail_read_service import TagDetailReadService
from app.services.tags.tag_list_service import TagListService
from app.services.tags.tag_options_service import TagOptionsService
from app.services.tags.tag_write_service import TagWriteService
from app.services.tags.tags_bulk_actions_service import TagsBulkActionsService
from app.utils.decorators import require_csrf

ns = Namespace("tags", description="标签管理")

ErrorEnvelope = get_error_envelope_model(ns)

TagWritePayload = ns.model(
    "TagWritePayload",
    {
        "name": fields.String(required=True, description="标签代码", example="prod"),
        "display_name": fields.String(required=True, description="标签展示名", example="生产"),
        "category": fields.String(required=True, description="分类", example="env"),
        "color": fields.String(required=False, description="颜色 key(可选)", example="red"),
        "is_active": fields.Boolean(required=False, description="是否启用(可选)", example=True),
    },
)

TagListItemModel = ns.model("TagListItem", TAG_LIST_ITEM_FIELDS)
TagOptionModel = ns.model("TagOptionItem", TAG_OPTION_FIELDS)
TaggableInstanceModel = ns.model("TaggableInstance", TAGGABLE_INSTANCE_FIELDS)

TagStatsModel = ns.model(
    "TagStats",
    {
        "total": fields.Integer(description="标签总数", example=10),
        "active": fields.Integer(description="启用标签数", example=9),
        "inactive": fields.Integer(description="停用标签数", example=1),
        "category_count": fields.Integer(description="分类数", example=3),
    },
)

TagsListData = ns.model(
    "TagsListData",
    {
        "items": fields.List(fields.Nested(TagListItemModel), description="标签列表"),
        "total": fields.Integer(description="总数", example=10),
        "page": fields.Integer(description="页码", example=1),
        "pages": fields.Integer(description="总页数", example=1),
        "limit": fields.Integer(description="分页大小", example=20),
        "stats": fields.Nested(TagStatsModel, description="统计信息"),
    },
)

TagsListSuccessEnvelope = make_success_envelope_model(ns, "TagsListSuccessEnvelope", TagsListData)

TagOptionsData = ns.model(
    "TagOptionsData",
    {
        "tags": fields.List(fields.Nested(TagOptionModel), description="标签选项列表"),
        "category": fields.String(required=False, description="筛选分类(可选)", example="env"),
    },
)

TagOptionsSuccessEnvelope = make_success_envelope_model(ns, "TagOptionsSuccessEnvelope", TagOptionsData)

TagCategoriesData = ns.model(
    "TagCategoriesData",
    {
        "categories": fields.List(fields.Raw, description="分类列表", example=["env", "app"]),
    },
)

TagCategoriesSuccessEnvelope = make_success_envelope_model(ns, "TagCategoriesSuccessEnvelope", TagCategoriesData)

TagDetailData = ns.model(
    "TagDetailData",
    {
        "tag": fields.Raw(description="标签详情"),
    },
)

TagDetailSuccessEnvelope = make_success_envelope_model(ns, "TagDetailSuccessEnvelope", TagDetailData)

TagDeleteData = ns.model(
    "TagDeleteData",
    {
        "tag_id": fields.Integer(description="标签 ID", example=1),
    },
)

TagDeleteSuccessEnvelope = make_success_envelope_model(ns, "TagDeleteSuccessEnvelope", TagDeleteData)

TagBatchDeletePayload = ns.model(
    "TagBatchDeletePayload",
    {
        "tag_ids": fields.List(fields.Integer(), required=True, description="标签 ID 列表", example=[1, 2]),
    },
)

TagBatchDeleteResultItem = ns.model(
    "TagBatchDeleteResultItem",
    {
        "tag_id": fields.Raw(description="标签 ID", example=1),
        "status": fields.String(description="状态(success/failed/skipped)", example="success"),
        "instance_count": fields.Integer(required=False, description="关联实例数(可选)", example=0),
        "message": fields.String(required=False, description="提示信息(可选)", example="deleted"),
    },
)

TagBatchDeleteData = ns.model(
    "TagBatchDeleteData",
    {
        "results": fields.List(fields.Nested(TagBatchDeleteResultItem), description="批量删除结果列表"),
    },
)

TagBatchDeleteSuccessEnvelope = make_success_envelope_model(ns, "TagBatchDeleteSuccessEnvelope", TagBatchDeleteData)

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

_tags_list_query_parser = new_parser()
_tags_list_query_parser.add_argument("page", type=int, default=1, location="args")
_tags_list_query_parser.add_argument("limit", type=int, default=20, location="args")
_tags_list_query_parser.add_argument("search", type=str, default="", location="args")
_tags_list_query_parser.add_argument("category", type=str, default="", location="args")
_tags_list_query_parser.add_argument("status", type=str, default="all", location="args")

_tag_options_query_parser = new_parser()
_tag_options_query_parser.add_argument("category", type=str, default="", location="args")


def _build_tag_list_filters(parsed: dict[str, object]) -> TagListFilters:
    query = validate_or_raise(TagsListQuery, parsed)
    return query.to_filters()


def _get_raw_payload() -> object:
    if request.is_json:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}
    return request.form


def _build_tag_write_service() -> TagWriteService:
    return TagWriteService()


@ns.route("")
class TagsResource(BaseResource):
    """标签列表资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", TagsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_tags_list_query_parser)
    @api_permission_required("view")
    def get(self):
        """获取标签列表."""

        def _execute():
            parsed = cast("dict[str, object]", _tags_list_query_parser.parse_args())
            filters = _build_tag_list_filters(parsed)
            page_result, stats = TagListService().list_tags(filters)
            items = marshal(page_result.items, TAG_LIST_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": page_result.total,
                    "page": page_result.page,
                    "pages": page_result.pages,
                    "limit": page_result.limit,
                    "stats": asdict(stats),
                },
            )

        return self.safe_call(
            _execute,
            module="tags",
            action="list_tags",
            public_error="获取标签列表失败",
            context={"query_params": request.args.to_dict(flat=False)},
        )

    @ns.expect(TagWritePayload, validate=False)
    @ns.response(201, "Created", TagDetailSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("create")
    @require_csrf
    def post(self):
        """创建标签."""
        payload = cast(Any, _get_raw_payload())
        operator_id = getattr(current_user, "id", None)

        def _execute():
            tag = _build_tag_write_service().create(payload, operator_id=operator_id)
            return self.success(
                data={"tag": tag.to_dict()},
                message="标签创建成功",
                status=HttpStatus.CREATED,
            )

        return self.safe_call(
            _execute,
            module="tags",
            action="create_tag",
            public_error="标签创建失败",
            context={"tag_name": payload.get("name")},
        )


@ns.route("/options")
class TagOptionsResource(BaseResource):
    """标签选项资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", TagOptionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_tag_options_query_parser)
    def get(self):
        """获取标签选项."""

        def _execute():
            parsed = _tag_options_query_parser.parse_args()
            query = validate_or_raise(TagOptionsQuery, dict(parsed))
            result = TagOptionsService().list_tag_options(query.category)
            tags_data = marshal(result.tags, TAG_OPTION_FIELDS)
            return self.success(
                data={
                    "tags": tags_data,
                    "category": result.category,
                },
            )

        return self.safe_call(
            _execute,
            module="tags",
            action="list_tag_options",
            public_error="获取标签列表失败",
        )


@ns.route("/categories")
class TagCategoriesResource(BaseResource):
    """标签分类资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", TagCategoriesSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取标签分类列表."""

        def _execute():
            categories = TagOptionsService().list_categories()
            return self.success(data={"categories": categories})

        return self.safe_call(
            _execute,
            module="tags",
            action="list_tag_categories",
            public_error="获取标签分类失败",
            context={"endpoint": "tags.categories"},
        )


@ns.route("/<int:tag_id>")
class TagDetailResource(BaseResource):
    """标签详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", TagDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, tag_id: int):
        """获取标签详情."""

        def _execute():
            tag = TagDetailReadService().get_tag_or_error(tag_id)
            return self.success(
                data={"tag": tag.to_dict()},
                message="获取标签详情成功",
            )

        return self.safe_call(
            _execute,
            module="tags",
            action="get_tag_by_id",
            public_error="获取标签详情失败",
            context={"tag_id": tag_id},
        )

    @ns.expect(TagWritePayload, validate=False)
    @ns.response(200, "OK", TagDetailSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("update")
    @require_csrf
    def put(self, tag_id: int):
        """更新标签."""
        payload = cast(Any, _get_raw_payload())
        operator_id = getattr(current_user, "id", None)

        def _execute():
            tag = _build_tag_write_service().update(tag_id, payload, operator_id=operator_id)
            return self.success(
                data={"tag": tag.to_dict()},
                message="标签更新成功",
            )

        return self.safe_call(
            _execute,
            module="tags",
            action="update_tag",
            public_error="标签更新失败",
            context={"tag_id": tag_id, "tag_name": payload.get("name")},
        )

    @ns.response(200, "OK", TagDeleteSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def delete(self, tag_id: int):
        """删除标签."""
        operator_id = getattr(current_user, "id", None)

        def _execute():
            outcome = _build_tag_write_service().delete(tag_id, operator_id=operator_id)
            if outcome.status == "in_use":
                raise ConflictError(
                    f"标签 '{outcome.display_name}' 仍被 {outcome.instance_count} 个实例使用,无法删除",
                    message_key="TAG_IN_USE",
                    extra={"tag_id": tag_id, "instance_count": outcome.instance_count},
                )
            return self.success(
                data={"tag_id": tag_id},
                message="标签删除成功",
            )

        return self.safe_call(
            _execute,
            module="tags",
            action="delete_tag",
            public_error="删除标签失败",
            context={"tag_id": tag_id},
            expected_exceptions=(ConflictError,),
        )


@ns.route("/batch-delete")
class TagBatchDeleteResource(BaseResource):
    """标签批量删除资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.expect(TagBatchDeletePayload, validate=False)
    @ns.response(200, "OK", TagBatchDeleteSuccessEnvelope)
    @ns.response(207, "Multi-Status", TagBatchDeleteSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("delete")
    @require_csrf
    def post(self):
        """批量删除标签."""
        raw_json = request.get_json(silent=True)
        raw: object = raw_json if isinstance(raw_json, dict) else {}
        operator_id = getattr(current_user, "id", None)
        raw_tag_ids = raw.get("tag_ids") if isinstance(raw, dict) else None
        count = len(raw_tag_ids) if isinstance(raw_tag_ids, list) else 0

        def _execute():
            outcome = _build_tag_write_service().batch_delete_from_payload(raw, operator_id=operator_id)
            status = HttpStatus.MULTI_STATUS if outcome.has_failure else HttpStatus.OK
            message = "部分标签未能删除" if outcome.has_failure else "标签批量删除成功"
            return self.success(data={"results": outcome.results}, message=message, status=status)

        return self.safe_call(
            _execute,
            module="tags",
            action="batch_delete_tags",
            public_error="批量删除标签失败",
            context={"count": count},
            expected_exceptions=(ValidationError,),
        )


@ns.route("/bulk/instances")
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


@ns.route("/bulk/tags")
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


@ns.route("/bulk/actions/assign")
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
        raw_json = request.get_json(silent=True)
        raw: object = raw_json if isinstance(raw_json, dict) else {}
        actor_id = getattr(current_user, "id", None)

        def _execute():
            outcome = TagsBulkActionsService().assign_from_payload(raw, actor_id=actor_id)

            return self.success(
                data={
                    "assigned_count": outcome.assigned_count,
                    "instance_ids": outcome.instance_ids,
                    "tag_ids": outcome.tag_ids,
                },
                message=f"标签批量分配成功,共分配 {outcome.assigned_count} 个标签关系",
            )

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="batch_assign_tags",
            public_error="批量分配标签失败",
            expected_exceptions=(ValidationError, NotFoundError),
            context={"route": "tags_bulk.assign"},
        )


@ns.route("/bulk/actions/remove")
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
        raw_json = request.get_json(silent=True)
        raw: object = raw_json if isinstance(raw_json, dict) else {}
        actor_id = getattr(current_user, "id", None)

        def _execute():
            outcome = TagsBulkActionsService().remove_from_payload(raw, actor_id=actor_id)

            return self.success(
                data={
                    "removed_count": outcome.removed_count,
                    "instance_ids": outcome.instance_ids,
                    "tag_ids": outcome.tag_ids,
                },
                message=f"标签批量移除成功,共移除 {outcome.removed_count} 个标签关系",
            )

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="batch_remove_tags",
            public_error="批量移除标签失败",
            expected_exceptions=(ValidationError, NotFoundError),
            context={"route": "tags_bulk.remove"},
        )


@ns.route("/bulk/instance-tags")
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
        raw_json = request.get_json(silent=True)
        raw: object = raw_json if isinstance(raw_json, dict) else {}

        def _execute():
            outcome = TagsBulkActionsService().list_instance_tags_from_payload(raw)
            return self.success(
                data={
                    "tags": outcome.tags,
                    "category_names": outcome.category_names,
                    "instance_ids": outcome.instance_ids,
                },
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


@ns.route("/bulk/actions/remove-all")
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
        raw_json = request.get_json(silent=True)
        raw: object = raw_json if isinstance(raw_json, dict) else {}
        actor_id = getattr(current_user, "id", None)

        def _execute():
            outcome = TagsBulkActionsService().remove_all_from_payload(raw, actor_id=actor_id)

            return self.success(
                data={"removed_count": outcome.removed_count, "instance_ids": outcome.instance_ids},
                message=f"批量移除成功,共移除 {outcome.removed_count} 个标签关系",
            )

        return self.safe_call(
            _execute,
            module="tags_bulk",
            action="batch_remove_all_tags",
            public_error="批量移除所有标签失败",
            expected_exceptions=(ValidationError, NotFoundError),
            context={"route": "tags_bulk.remove_all"},
        )
