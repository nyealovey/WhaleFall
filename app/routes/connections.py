"""鲸落 - 数据库连接管理API."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast

from flask import Blueprint, Response, request
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError

from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import Credential, Instance
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.services.connection_adapters.connection_test_service import ConnectionTestService
from app.types import JsonDict, JsonValue
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.structlog_config import log_info, log_warning
from app.utils.time_utils import time_utils

connections_bp = Blueprint("connections", __name__)
connection_test_service = ConnectionTestService()

MIN_ALLOWED_PORT = 1
MAX_ALLOWED_PORT = 65535
MAX_BATCH_TEST_SIZE = 50
BatchTestResult = JsonDict

BATCH_TEST_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    ConnectionError,
    RuntimeError,
)


def _normalize_db_type(raw_db_type: JsonValue | None) -> str:
    """规范化数据库类型字符串并校验是否受支持."""
    db_type = str(raw_db_type or "").lower()
    if not ConnectionFactory.is_type_supported(db_type):
        msg = f"不支持的数据库类型: {db_type}"
        raise ValidationError(msg)
    return db_type


def _normalize_port(raw_port: JsonValue | None) -> int:
    """将端口转换为整数并验证范围."""
    try:
        port = int(raw_port)
    except (ValueError, TypeError) as exc:
        msg = "端口号必须是有效的数字"
        raise ValidationError(msg) from exc
    if port < MIN_ALLOWED_PORT or port > MAX_ALLOWED_PORT:
        msg = f"端口号必须在{MIN_ALLOWED_PORT}-{MAX_ALLOWED_PORT}之间"
        raise ValidationError(msg)
    return port


def _normalize_credential_id(raw_id: JsonValue | None) -> int:
    """将凭据 ID 归一化为整数.

    Args:
        raw_id: 原始凭据 ID,可能是字符串或数字.

    Returns:
        归一化后的凭据 ID.

    Raises:
        ValidationError: 当 ID 缺失或无法转换为整数时抛出.

    """
    if raw_id is None:
        msg = "credential_id 不能为空"
        raise ValidationError(msg)
    try:
        return int(raw_id)
    except (ValueError, TypeError) as exc:
        msg = "credential_id 必须是整数"
        raise ValidationError(msg) from exc


def _require_credential(credential_id: int) -> Credential:
    """根据 ID 获取凭据,不存在时抛出 NotFoundError."""
    credential = Credential.query.get(credential_id)
    if not credential:
        msg = "凭据不存在"
        raise NotFoundError(msg)
    return credential


def _validate_connection_payload(data: JsonDict) -> tuple[str, int]:
    """验证连接参数并返回规范化后的 db_type 与端口."""
    db_type = _normalize_db_type(data.get("db_type"))
    port = _normalize_port(data.get("port", 0))
    credential_id = data.get("credential_id")
    if credential_id is not None:
        _require_credential(_normalize_credential_id(credential_id))
    return db_type, port


@connections_bp.route("/api/test", methods=["POST"])
@login_required
@view_required
@require_csrf
def test_connection() -> Response:
    """测试数据库连接 API.

    支持两种模式:
    1. 测试现有实例:传入 instance_id
    2. 测试新连接:传入连接参数(db_type、host、port、credential_id)

    Returns:
        JSON 响应,包含连接测试结果和数据库版本信息.

    Raises:
        ValidationError: 当请求数据为空或参数无效时抛出.
        NotFoundError: 当实例或凭据不存在时抛出.
        ConflictError: 当连接测试失败时抛出.

    """
    data = cast("JsonDict | None", request.get_json(silent=True))
    if not data:
        msg = "请求数据不能为空"
        raise ValidationError(msg)

    def _execute() -> Response:
        if "instance_id" in data:
            return _test_existing_instance(int(data["instance_id"]))
        return _test_new_connection(data)

    return safe_route_call(
        _execute,
        module="connections",
        action="test_connection",
        public_error="连接测试失败",
        expected_exceptions=(ValidationError, NotFoundError),
        context={"has_instance_id": "instance_id" in data},
    )


def _test_existing_instance(instance_id: int) -> Response:
    """测试现有实例连接.

    Args:
        instance_id: 实例 ID.

    Returns:
        JSON 响应,包含测试结果.

    Raises:
        NotFoundError: 当实例不存在时抛出.
        SystemError: 当连接测试失败时抛出.

    """
    instance = Instance.query.get(instance_id)
    if not instance:
        msg = "实例不存在"
        raise NotFoundError(msg)
    result = connection_test_service.test_connection(instance)
    if result.get("success"):
        log_info(
            "实例连接测试成功",
            module="connections",
            instance_id=instance_id,
            instance_name=instance.name,
            database_version=result.get("database_version"),
            main_version=result.get("main_version"),
            detailed_version=result.get("detailed_version"),
        )
        return jsonify_unified_success(data={"result": result}, message="实例连接测试成功")
    error_message = result.get("error") or result.get("message") or "实例连接测试失败"
    raise ConflictError(error_message)


def _test_new_connection(connection_params: JsonDict) -> Response:
    """测试新连接参数.

    创建临时实例对象进行连接测试.

    Args:
        connection_params: 连接参数字典,必须包含 db_type、host、port、credential_id.

    Returns:
        JSON 响应,包含测试结果.

    Raises:
        ValidationError: 当参数缺失或无效时抛出.
        NotFoundError: 当凭据不存在时抛出.
        ConflictError: 当连接测试失败时抛出.

    """
    required_fields = ["db_type", "host", "port", "credential_id"]
    missing_fields = [field for field in required_fields if not connection_params.get(field)]
    if missing_fields:
        msg = f"缺少必需参数: {', '.join(missing_fields)}"
        raise ValidationError(msg)
    db_type = _normalize_db_type(connection_params.get("db_type"))
    port = _normalize_port(connection_params.get("port", 0))
    credential = _require_credential(_normalize_credential_id(connection_params.get("credential_id")))
    temp_instance = Instance(
        name=connection_params.get("name", "temp_test"),
        db_type=db_type,
        host=connection_params.get("host"),
        port=port,
        credential_id=credential.id,
        description="临时测试连接",
    )
    temp_instance.credential = credential
    result = connection_test_service.test_connection(temp_instance)
    if result.get("success"):
        log_info(
            "新连接参数测试成功",
            module="connections",
            db_type=db_type,
            host=temp_instance.host,
            port=port,
        )
        return jsonify_unified_success(data={"result": result}, message="连接测试成功")
    error_message = result.get("error") or result.get("message") or "连接测试失败"
    raise ConflictError(error_message)


@connections_bp.route("/api/validate-params", methods=["POST"])
@login_required
@view_required
@require_csrf
def validate_connection_params() -> Response:
    """验证连接参数.

    验证数据库类型、端口号和凭据 ID 的有效性.

    Returns:
        JSON 响应.

    Raises:
        ValidationError: 当参数无效时抛出.
        NotFoundError: 当凭据不存在时抛出.

    """
    data = cast("JsonDict | None", request.get_json(silent=True))
    if not data:
        msg = "请求数据不能为空"
        raise ValidationError(msg)

    def _execute() -> Response:
        db_type, _ = _validate_connection_payload(data)
        log_info("连接参数验证通过", module="connections", db_type=db_type)
        return jsonify_unified_success(message="连接参数验证通过")

    return safe_route_call(
        _execute,
        module="connections",
        action="validate_connection_params",
        public_error="验证连接参数失败",
        expected_exceptions=(ValidationError, NotFoundError),
    )


def _execute_batch_tests(instance_ids: list[int]) -> tuple[list[BatchTestResult], int, int]:
    """执行批量连接测试并返回结果与统计."""
    results: list[BatchTestResult] = []
    success_count = 0
    fail_count = 0
    for instance_id in instance_ids:
        try:
            instance = Instance.query.get(instance_id)
            if not instance:
                results.append({"instance_id": instance_id, "success": False, "error": "实例不存在"})
                fail_count += 1
                log_warning("批量连接测试遇到不存在的实例", module="connections", instance_id=instance_id)
                continue
            result = cast("BatchTestResult", connection_test_service.test_connection(instance))
            result["instance_id"] = instance_id
            result["instance_name"] = instance.name
            if result.get("success"):
                success_count += 1
            else:
                fail_count += 1
            results.append(result)
        except BATCH_TEST_EXCEPTIONS as exc:  # pragma: no cover - 单个实例失败记录
            results.append({"instance_id": instance_id, "success": False, "error": f"测试失败: {exc!s}"})
            fail_count += 1
            log_with_context(
                "warning",
                "批量连接测试单实例失败",
                module="connections",
                action="batch_test_single",
                context={"instance_id": instance_id},
                extra={"error_message": str(exc)},
            )
    return results, success_count, fail_count


@connections_bp.route("/api/batch-test", methods=["POST"])
@login_required
@view_required
@require_csrf
def batch_test_connections() -> Response:
    """批量测试连接.

    最多支持 50 个实例的批量测试.

    Returns:
        JSON 响应,包含每个实例的测试结果和汇总统计.

    Raises:
        ValidationError: 当参数无效或数量超限时抛出.
        SystemError: 当批量测试失败时抛出.

    """
    raw_data = request.get_json(silent=True)
    if raw_data is None:
        raw_data = {}
    if not isinstance(raw_data, dict):
        msg = "请求数据格式必须是 JSON 对象"
        raise ValidationError(msg)
    data = cast("JsonDict", raw_data)

    def _execute() -> Response:
        if "instance_ids" not in data:
            msg = "缺少实例ID列表"
            raise ValidationError(msg)
        instance_ids_raw = data["instance_ids"]
        if not isinstance(instance_ids_raw, list) or not instance_ids_raw:
            msg = "实例ID列表不能为空"
            raise ValidationError(msg)
        try:
            instance_ids = [int(item) for item in instance_ids_raw]
        except (TypeError, ValueError) as exc:
            msg = "实例ID列表必须为整数"
            raise ValidationError(msg) from exc
        if len(instance_ids) > MAX_BATCH_TEST_SIZE:
            msg = f"批量测试数量不能超过{MAX_BATCH_TEST_SIZE}个"
            raise ValidationError(msg)

        results, success_count, fail_count = _execute_batch_tests(instance_ids)
        summary = {"total": len(instance_ids), "success": success_count, "failed": fail_count}
        log_info(
            "批量连接测试完成",
            module="connections",
            total=summary["total"],
            success=summary["success"],
            failed=summary["failed"],
        )
        return jsonify_unified_success(
            data={"results": results, "summary": summary},
            message="批量连接测试完成",
        )

    return safe_route_call(
        _execute,
        module="connections",
        action="batch_test_connections",
        public_error="批量测试连接失败",
        expected_exceptions=(ValidationError,),
        context={"payload_keys": list(cast("dict", data).keys())},
    )


@connections_bp.route("/api/status/<int:instance_id>", methods=["GET"])
@login_required
@view_required
def get_connection_status(instance_id: int) -> Response:
    """获取实例连接状态.

    根据最后连接时间判断状态:1小时内为 good,1天内为 warning,超过1天为 poor.

    Args:
        instance_id: 实例 ID.

    Returns:
        JSON 响应,包含实例信息和连接状态.

    Raises:
        NotFoundError: 当实例不存在时抛出.
        SystemError: 当获取状态失败时抛出.

    """
    instance = Instance.query.get(instance_id)
    if not instance:
        msg = "实例不存在"
        raise NotFoundError(msg)
    payload = _build_connection_status_payload(instance)
    return jsonify_unified_success(data=payload, message="获取连接状态成功")


def _build_connection_status_payload(instance: Instance) -> JsonDict:
    """构建连接状态响应负载."""
    last_connected = instance.last_connected.isoformat() if instance.last_connected else None
    status = "unknown"
    if instance.last_connected:
        last_connected_time = instance.last_connected
        if isinstance(last_connected_time, str):
            last_connected_time = datetime.fromisoformat(last_connected_time)
        delta = time_utils.now() - last_connected_time
        if delta < timedelta(hours=1):
            status = "good"
        elif delta < timedelta(days=1):
            status = "warning"
        else:
            status = "poor"
    return {
        "instance_id": instance.id,
        "instance_name": instance.name,
        "db_type": instance.db_type,
        "host": instance.host,
        "port": instance.port,
        "last_connected": last_connected,
        "status": status,
        "is_active": instance.is_active,
    }
