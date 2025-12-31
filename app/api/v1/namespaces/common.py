"""Common/options namespace (Phase 3 全量覆盖 - 通用数据模块)."""

from __future__ import annotations

from flask import request
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.errors import NotFoundError, ValidationError
from app.models.instance import Instance
from app.routes.common_restx_models import (
    COMMON_DATABASE_OPTION_ITEM_FIELDS,
    COMMON_DATABASES_OPTIONS_RESPONSE_FIELDS,
    COMMON_DBTYPE_OPTION_ITEM_FIELDS,
    COMMON_DBTYPES_OPTIONS_RESPONSE_FIELDS,
    COMMON_INSTANCE_OPTION_ITEM_FIELDS,
    COMMON_INSTANCES_OPTIONS_RESPONSE_FIELDS,
)
from app.services.common.filter_options_service import FilterOptionsService
from app.types.common_filter_options import CommonDatabasesOptionsFilters

ns = Namespace("common", description="通用数据")

ErrorEnvelope = get_error_envelope_model(ns)

CommonInstanceOptionItemModel = ns.model("CommonInstanceOptionItem", COMMON_INSTANCE_OPTION_ITEM_FIELDS)
CommonInstancesOptionsData = ns.model(
    "CommonInstancesOptionsData",
    {
        "instances": fields.List(fields.Nested(CommonInstanceOptionItemModel)),
    },
)
CommonInstancesOptionsSuccessEnvelope = make_success_envelope_model(
    ns,
    "CommonInstancesOptionsSuccessEnvelope",
    CommonInstancesOptionsData,
)

CommonDatabaseOptionItemModel = ns.model("CommonDatabaseOptionItem", COMMON_DATABASE_OPTION_ITEM_FIELDS)
CommonDatabasesOptionsData = ns.model(
    "CommonDatabasesOptionsData",
    {
        "databases": fields.List(fields.Nested(CommonDatabaseOptionItemModel)),
        "total_count": fields.Integer(),
        "limit": fields.Integer(),
        "offset": fields.Integer(),
    },
)
CommonDatabasesOptionsSuccessEnvelope = make_success_envelope_model(
    ns,
    "CommonDatabasesOptionsSuccessEnvelope",
    CommonDatabasesOptionsData,
)

CommonDatabaseTypeOptionItemModel = ns.model("CommonDatabaseTypeOptionItem", COMMON_DBTYPE_OPTION_ITEM_FIELDS)
CommonDatabaseTypesOptionsData = ns.model(
    "CommonDatabaseTypesOptionsData",
    {
        "options": fields.List(fields.Nested(CommonDatabaseTypeOptionItemModel)),
    },
)
CommonDatabaseTypesOptionsSuccessEnvelope = make_success_envelope_model(
    ns,
    "CommonDatabaseTypesOptionsSuccessEnvelope",
    CommonDatabaseTypesOptionsData,
)


@ns.route("/instances/options")
class CommonInstancesOptionsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", CommonInstancesOptionsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        db_type = (request.args.get("db_type") or "").strip() or None

        def _execute():
            result = FilterOptionsService().get_common_instances_options(db_type=db_type)
            payload = marshal(result, COMMON_INSTANCES_OPTIONS_RESPONSE_FIELDS)
            return self.success(data=payload, message="实例选项获取成功")

        return self.safe_call(
            _execute,
            module="common",
            action="get_instance_options",
            public_error="加载实例选项失败",
            context={"db_type": db_type},
        )


@ns.route("/databases/options")
class CommonDatabasesOptionsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", CommonDatabasesOptionsSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            instance_id = request.args.get("instance_id", type=int)
            if not instance_id:
                raise ValidationError("instance_id 为必填参数")

            instance = Instance.query.get(instance_id)
            if not instance:
                raise NotFoundError("实例不存在")

            try:
                limit = int(request.args.get("limit", 100))
                offset = int(request.args.get("offset", 0))
            except ValueError as exc:
                raise ValidationError("limit/offset 必须为整数") from exc

            result = FilterOptionsService().get_common_databases_options(
                CommonDatabasesOptionsFilters(
                    instance_id=int(instance.id),
                    limit=limit,
                    offset=offset,
                ),
            )
            payload = marshal(result, COMMON_DATABASES_OPTIONS_RESPONSE_FIELDS)
            return self.success(data=payload, message="数据库选项获取成功")

        return self.safe_call(
            _execute,
            module="common",
            action="get_database_options",
            public_error="获取实例数据库列表失败",
            expected_exceptions=(ValidationError, NotFoundError),
        )


@ns.route("/database-types/options")
class CommonDatabaseTypesOptionsResource(BaseResource):
    method_decorators = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", CommonDatabaseTypesOptionsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        def _execute():
            result = FilterOptionsService().get_common_database_types_options()
            payload = marshal(result, COMMON_DBTYPES_OPTIONS_RESPONSE_FIELDS)
            return self.success(data=payload, message="数据库类型选项获取成功")

        return self.safe_call(
            _execute,
            module="common",
            action="get_database_type_options",
            public_error="加载数据库类型选项失败",
        )
