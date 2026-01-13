"""Instances namespace: connections actions/status.

将原 `connections` namespace 下的连接测试/参数校验/状态查询 API 下沉到 `instances` namespace。
"""

from __future__ import annotations

from typing import ClassVar, cast
from uuid import uuid4

from flask import Response, request
from flask_restx import fields
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.namespaces.instances import ns
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.core.constants.system_constants import ErrorMessages
from app.core.exceptions import NotFoundError, ValidationError
from app.services.connection_adapters.connection_test_service import ConnectionTestService
from app.services.connections.instance_connections_write_service import InstanceConnectionsWriteService
from app.services.connections.instance_connection_status_service import InstanceConnectionStatusService
from app.services.credentials import CredentialDetailReadService
from app.services.instances.instance_detail_read_service import InstanceDetailReadService
from app.core.types import JsonDict, JsonValue
from app.utils.decorators import require_csrf
from app.utils.response_utils import jsonify_unified_error_message
from app.infra.route_safety import log_with_context

ErrorEnvelope = get_error_envelope_model(ns)

EmptySuccessEnvelope = make_success_envelope_model(ns, "InstancesConnectionsEmptySuccessEnvelope")

ConnectionTestPayload = ns.model(
    "InstancesConnectionsConnectionTestPayload",
    {
        "instance_id": fields.Integer(required=False, description="测试既有实例(可选)", example=1),
        "db_type": fields.String(
            required=False,
            description="数据库类型(mysql/postgresql/sqlserver/oracle)",
            example="mysql",
        ),
        "host": fields.String(required=False, description="主机地址", example="127.0.0.1"),
        "port": fields.Integer(required=False, description="端口号", example=3306),
        "credential_id": fields.Integer(required=False, description="凭据 ID(可选)", example=1),
        "name": fields.String(required=False, description="实例名称(可选)", example="prod-mysql-1"),
    },
)

ConnectionTestData = ns.model(
    "InstancesConnectionsConnectionTestData",
    {
        "success": fields.Boolean(description="连接是否成功", example=True),
        "message": fields.String(description="连接测试消息", example="OK"),
        "details": fields.Raw(description="连接测试详情(可选)", example={}),
    },
)

ConnectionTestSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstancesConnectionsConnectionTestSuccessEnvelope",
    ConnectionTestData,
)

ValidateParamsPayload = ns.model(
    "InstancesConnectionsValidateConnectionParamsPayload",
    {
        "db_type": fields.String(required=True, description="数据库类型", example="mysql"),
        "port": fields.Integer(required=True, description="端口", example=3306),
        "credential_id": fields.Integer(required=False, description="凭据 ID(可选)", example=1),
    },
)

BatchTestPayload = ns.model(
    "InstancesConnectionsBatchTestPayload",
    {
        "instance_ids": fields.List(fields.Integer(), required=True, description="实例 ID 列表", example=[1, 2]),
    },
)

BatchTestSummary = ns.model(
    "InstancesConnectionsBatchTestSummary",
    {
        "total": fields.Integer(description="总数", example=2),
        "success": fields.Integer(description="成功数", example=1),
        "failed": fields.Integer(description="失败数", example=1),
    },
)

BatchTestData = ns.model(
    "InstancesConnectionsBatchTestData",
    {
        "results": fields.List(fields.Raw, description="结果列表"),
        "summary": fields.Nested(BatchTestSummary, description="汇总信息"),
    },
)

BatchTestSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstancesConnectionsBatchTestSuccessEnvelope",
    BatchTestData,
)

ConnectionStatusData = ns.model(
    "InstancesConnectionsConnectionStatusData",
    {
        "instance_id": fields.Integer(description="实例 ID", example=1),
        "instance_name": fields.String(description="实例名称", example="prod-mysql-1"),
        "db_type": fields.String(description="数据库类型", example="mysql"),
        "host": fields.String(description="主机", example="127.0.0.1"),
        "port": fields.Integer(description="端口", example=3306),
        "last_connected": fields.String(required=False, description="最后连接时间(ISO8601, 可选)", example=None),
        "status": fields.String(description="状态", example="ok"),
        "is_active": fields.Boolean(description="是否启用", example=True),
    },
)

ConnectionStatusSuccessEnvelope = make_success_envelope_model(
    ns,
    "InstancesConnectionsConnectionStatusSuccessEnvelope",
    ConnectionStatusData,
)

BATCH_TEST_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    ConnectionError,
    RuntimeError,
)


def _parse_json_payload() -> JsonDict:
    raw = request.get_json(silent=True)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValidationError("请求数据格式必须是 JSON 对象")
    return cast("JsonDict", raw)


def _require_credential(credential_id: int) -> object:
    return CredentialDetailReadService().get_credential_or_error(credential_id)


def _test_existing_instance(connection_test_service: ConnectionTestService, instance_id: int):
    instance = InstanceDetailReadService().get_instance_by_id(instance_id)
    if instance is None:
        raise NotFoundError("实例不存在", extra={"instance_id": instance_id})
    result = connection_test_service.test_connection(instance)
    if result.get("success"):
        return result, 200, "实例连接测试成功"

    extra: JsonDict = {}
    if result.get("error_id"):
        extra["connection_error_id"] = str(result["error_id"])
    if result.get("error_code"):
        extra["error_code"] = str(result["error_code"])
    if result.get("details"):
        extra["details"] = cast("JsonValue", result["details"])

    response, status = jsonify_unified_error_message(
        ErrorMessages.DATABASE_CONNECTION_ERROR,
        status_code=409,
        message_key="DATABASE_CONNECTION_ERROR",
        extra=extra,
    )
    response.status_code = status
    return response


def _test_new_connection(connection_test_service: ConnectionTestService, connection_params: object):
    parsed = cast(object, connection_params)
    name = cast("str | None", getattr(parsed, "name"))
    db_type = cast("str", getattr(parsed, "db_type"))
    host = cast("str", getattr(parsed, "host"))
    port = cast("int", getattr(parsed, "port"))
    credential_id = cast("int", getattr(parsed, "credential_id"))

    resolved_name = "temp_test"
    if isinstance(name, str) and name.strip():
        resolved_name = name

    credential = _require_credential(credential_id)
    result = connection_test_service.test_connection_with_params(
        name=resolved_name,
        db_type=db_type,
        host=host,
        port=port,
        credential=credential,
    )
    if result.get("success"):
        return result, 200, "连接测试成功"

    extra: JsonDict = {}
    if result.get("error_id"):
        extra["connection_error_id"] = str(result["error_id"])
    if result.get("error_code"):
        extra["error_code"] = str(result["error_code"])
    if result.get("details"):
        extra["details"] = cast("JsonValue", result["details"])

    response, status = jsonify_unified_error_message(
        ErrorMessages.DATABASE_CONNECTION_ERROR,
        status_code=409,
        message_key="DATABASE_CONNECTION_ERROR",
        extra=extra,
    )
    response.status_code = status
    return response


def _execute_batch_tests(
    connection_test_service: ConnectionTestService, instance_ids: list[int]
) -> tuple[list[JsonDict], int, int]:
    results: list[JsonDict] = []
    success_count = 0
    fail_count = 0
    instance_detail_service = InstanceDetailReadService()

    for instance_id in instance_ids:
        try:
            instance = instance_detail_service.get_instance_by_id(instance_id)
            if instance is None:
                results.append({"instance_id": instance_id, "success": False, "error": "实例不存在"})
                fail_count += 1
                continue

            result = cast("JsonDict", connection_test_service.test_connection(instance))
            result["instance_id"] = instance_id
            result["instance_name"] = instance.name
            if result.get("success"):
                success_count += 1
            else:
                fail_count += 1
            results.append(result)
        except BATCH_TEST_EXCEPTIONS as exc:  # pragma: no cover
            error_id = uuid4().hex
            results.append(
                {
                    "instance_id": instance_id,
                    "success": False,
                    "message": ErrorMessages.DATABASE_CONNECTION_ERROR,
                    "error_code": "BATCH_TEST_FAILED",
                    "error_id": error_id,
                },
            )
            fail_count += 1
            log_with_context(
                "warning",
                "批量连接测试单实例失败",
                module="connections",
                action="batch_test_single",
                context={"instance_id": instance_id},
                extra={"error_id": error_id, "error_type": exc.__class__.__name__, "error_message": str(exc)},
            )

    return results, success_count, fail_count


@ns.route("/actions/test-connection")
class InstancesConnectionsTestResource(BaseResource):
    """连接测试资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.expect(ConnectionTestPayload, validate=False)
    @ns.response(200, "OK", ConnectionTestSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """执行连接测试."""
        raw = _parse_json_payload()
        write_service = InstanceConnectionsWriteService()
        connection_test_service = ConnectionTestService()

        def _execute():
            parsed = write_service.parse_connection_test_payload(raw)
            if parsed.instance_id is not None:
                maybe_error = _test_existing_instance(connection_test_service, parsed.instance_id)
                if isinstance(maybe_error, Response):
                    return maybe_error
                success_payload, status_code, message = cast("tuple[JsonDict, int, str]", maybe_error)
                return self.success(data=success_payload, message=message, status=status_code)

            maybe_error = _test_new_connection(connection_test_service, parsed)
            if isinstance(maybe_error, Response):
                return maybe_error
            success_payload, status_code, message = cast("tuple[JsonDict, int, str]", maybe_error)
            return self.success(data=success_payload, message=message, status=status_code)

        return self.safe_call(
            _execute,
            module="connections",
            action="test_connection",
            public_error="连接测试失败",
            expected_exceptions=(ValidationError, NotFoundError),
            context={"has_instance_id": "instance_id" in raw},
        )


@ns.route("/actions/validate-connection-params")
class InstancesConnectionsValidateParamsResource(BaseResource):
    """连接参数验证资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.expect(ValidateParamsPayload, validate=False)
    @ns.response(200, "OK", EmptySuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """验证连接参数."""
        raw = _parse_json_payload()
        write_service = InstanceConnectionsWriteService()

        def _execute():
            write_service.validate_connection_params_from_payload(raw)
            return self.success(message="连接参数验证通过")

        return self.safe_call(
            _execute,
            module="connections",
            action="validate_connection_params",
            public_error="验证连接参数失败",
            expected_exceptions=(ValidationError, NotFoundError),
        )


@ns.route("/actions/batch-test-connections")
class InstancesConnectionsBatchTestResource(BaseResource):
    """批量连接测试资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.expect(BatchTestPayload, validate=False)
    @ns.response(200, "OK", BatchTestSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """执行批量连接测试."""
        raw = _parse_json_payload()
        write_service = InstanceConnectionsWriteService()

        def _execute():
            parsed = write_service.parse_batch_test_payload(raw)
            instance_ids = parsed.instance_ids
            results, success_count, fail_count = _execute_batch_tests(ConnectionTestService(), instance_ids)
            summary = {"total": len(instance_ids), "success": success_count, "failed": fail_count}
            return self.success(
                data={"results": results, "summary": summary},
                message="批量连接测试完成",
            )

        return self.safe_call(
            _execute,
            module="connections",
            action="batch_test_connections",
            public_error="批量测试连接失败",
            expected_exceptions=(ValidationError,),
            context={"payload_keys": list(raw.keys())},
        )


@ns.route("/<int:instance_id>/connection-status")
class InstancesConnectionsStatusResource(BaseResource):
    """连接状态查询资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", ConnectionStatusSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, instance_id: int):
        """获取连接状态."""

        def _execute():
            payload = InstanceConnectionStatusService().get_status(instance_id)
            return self.success(data=payload, message="获取连接状态成功")

        return self.safe_call(
            _execute,
            module="connections",
            action="get_connection_status",
            public_error="获取连接状态失败",
            expected_exceptions=(NotFoundError,),
            context={"instance_id": instance_id},
        )
