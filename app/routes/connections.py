"""鲸落 - 数据库连接管理API."""
from typing import Any

from flask import Blueprint, Response, request
from flask_login import login_required

from app.errors import NotFoundError, SystemError, ValidationError
from app.models import Instance
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.services.connection_adapters.connection_test_service import ConnectionTestService
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils

connections_bp = Blueprint("connections", __name__)
connection_test_service = ConnectionTestService()

@connections_bp.route("/api/test", methods=["POST"])
@login_required
@view_required
@require_csrf
def test_connection() -> Response:
    """测试数据库连接 API。.

    支持两种模式：
    1. 测试现有实例：传入 instance_id
    2. 测试新连接：传入连接参数（db_type、host、port、credential_id）

    Returns:
        JSON 响应，包含连接测试结果和数据库版本信息。

    Raises:
        ValidationError: 当请求数据为空或参数无效时抛出。
        NotFoundError: 当实例或凭据不存在时抛出。
        SystemError: 当连接测试失败时抛出。

    """
    data = request.get_json()
    if not data:
        msg = "请求数据不能为空"
        raise ValidationError(msg)
    try:
        if "instance_id" in data:
            return _test_existing_instance(int(data["instance_id"]))
        return _test_new_connection(data)
    except Exception as exc:
        log_error("连接测试失败", module="connections", error=str(exc))
        msg = "连接测试失败"
        raise SystemError(msg) from exc

def _test_existing_instance(instance_id: int) -> Response:
    """测试现有实例连接。.

    Args:
        instance_id: 实例 ID。

    Returns:
        JSON 响应，包含测试结果。

    Raises:
        NotFoundError: 当实例不存在时抛出。
        SystemError: 当连接测试失败时抛出。

    """
    instance = Instance.query.get(instance_id)
    if not instance:
        msg = "实例不存在"
        raise NotFoundError(msg)
    result = connection_test_service.test_connection(instance)
    if result.get("success"):
        log_info("实例连接测试成功", module="connections", instance_id=instance_id, instance_name=instance.name, database_version=result.get("database_version"), main_version=result.get("main_version"), detailed_version=result.get("detailed_version"))
        return jsonify_unified_success(data={"result": result}, message="实例连接测试成功")
    error_message = result.get("error") or result.get("message") or "实例连接测试失败"
    raise SystemError(error_message)

def _test_new_connection(connection_params: dict[str, Any]) -> Response:
    """测试新连接参数。.

    创建临时实例对象进行连接测试。

    Args:
        connection_params: 连接参数字典，必须包含 db_type、host、port、credential_id。

    Returns:
        JSON 响应，包含测试结果。

    Raises:
        ValidationError: 当参数缺失或无效时抛出。
        NotFoundError: 当凭据不存在时抛出。
        SystemError: 当连接测试失败时抛出。

    """
    required_fields = ["db_type", "host", "port", "credential_id"]
    missing_fields = [field for field in required_fields if not connection_params.get(field)]
    if missing_fields:
        msg = f"缺少必需参数: {', '.join(missing_fields)}"
        raise ValidationError(msg)
    db_type = str(connection_params.get("db_type", "")).lower()
    if not ConnectionFactory.is_type_supported(db_type):
        msg = f"不支持的数据库类型: {db_type}"
        raise ValidationError(msg)
    try:
        port = int(connection_params.get("port", 0))
    except (ValueError, TypeError) as exc:
        msg = "端口号必须是有效的数字"
        raise ValidationError(msg) from exc
    if port <= 0 or port > 65535:
        msg = "端口号必须在1-65535之间"
        raise ValidationError(msg)
    from app.models import Credential
    credential = Credential.query.get(connection_params.get("credential_id"))
    if not credential:
        msg = "凭据不存在"
        raise NotFoundError(msg)
    temp_instance = Instance(name=connection_params.get("name", "temp_test"), db_type=db_type, host=connection_params.get("host"), port=port, credential_id=connection_params.get("credential_id"), description="临时测试连接")
    temp_instance.credential = credential
    result = connection_test_service.test_connection(temp_instance)
    if result.get("success"):
        log_info("新连接参数测试成功", module="connections", db_type=db_type, host=temp_instance.host, port=port)
        return jsonify_unified_success(data={"result": result}, message="连接测试成功")
    error_message = result.get("error") or result.get("message") or "连接测试失败"
    raise SystemError(error_message)

@connections_bp.route("/api/validate-params", methods=["POST"])
@login_required
@view_required
@require_csrf
def validate_connection_params() -> Response:
    """验证连接参数。.

    验证数据库类型、端口号和凭据 ID 的有效性。

    Returns:
        JSON 响应。

    Raises:
        ValidationError: 当参数无效时抛出。
        NotFoundError: 当凭据不存在时抛出。

    """
    data = request.get_json()
    if not data:
        msg = "请求数据不能为空"
        raise ValidationError(msg)
    try:
        db_type = str(data.get("db_type", "")).lower()
        if not ConnectionFactory.is_type_supported(db_type):
            msg = f"不支持的数据库类型: {db_type}"
            raise ValidationError(msg)
        try:
            port = int(data.get("port", 0))
        except (ValueError, TypeError) as exc:
            msg = "端口号必须是有效的数字"
            raise ValidationError(msg) from exc
        if port <= 0 or port > 65535:
            msg = "端口号必须在1-65535之间"
            raise ValidationError(msg)
        if data.get("credential_id"):
            from app.models import Credential
            credential = Credential.query.get(data.get("credential_id"))
            if not credential:
                msg = "凭据不存在"
                raise NotFoundError(msg)
        log_info("连接参数验证通过", module="connections", db_type=db_type)
        return jsonify_unified_success(message="连接参数验证通过")
    except Exception as exc:
        log_error("验证连接参数失败", module="connections", error=str(exc))
        raise

@connections_bp.route("/api/batch-test", methods=["POST"])
@login_required
@view_required
@require_csrf
def batch_test_connections() -> Response:
    """批量测试连接。.

    最多支持 50 个实例的批量测试。

    Returns:
        JSON 响应，包含每个实例的测试结果和汇总统计。

    Raises:
        ValidationError: 当参数无效或数量超限时抛出。
        SystemError: 当批量测试失败时抛出。

    """
    data = request.get_json() or {}
    if "instance_ids" not in data:
        msg = "缺少实例ID列表"
        raise ValidationError(msg)
    instance_ids = data["instance_ids"]
    if not isinstance(instance_ids, list) or not instance_ids:
        msg = "实例ID列表不能为空"
        raise ValidationError(msg)
    if len(instance_ids) > 50:
        msg = "批量测试数量不能超过50个"
        raise ValidationError(msg)
    try:
        results = []
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
                result = connection_test_service.test_connection(instance)
                result["instance_id"] = instance_id
                result["instance_name"] = instance.name
                if result.get("success"):
                    success_count += 1
                else:
                    fail_count += 1
                results.append(result)
            except Exception as e:
                results.append({"instance_id": instance_id, "success": False, "error": f"测试失败: {e!s}"})
                fail_count += 1
                log_error("批量连接测试单实例失败", module="connections", instance_id=instance_id, error=str(e))
        log_info("批量连接测试完成", module="connections", total=len(instance_ids), success=success_count, failed=fail_count)
        return jsonify_unified_success(data={"results": results, "summary": {"total": len(instance_ids), "success": success_count, "failed": fail_count}}, message="批量连接测试完成")
    except Exception as exc:
        log_error("批量测试连接失败", module="connections", error=str(exc))
        msg = "批量测试连接失败"
        raise SystemError(msg) from exc

@connections_bp.route("/api/status/<int:instance_id>", methods=["GET"])
@login_required
@view_required
def get_connection_status(instance_id: int) -> Response:
    """获取实例连接状态。.

    根据最后连接时间判断状态：1小时内为 good，1天内为 warning，超过1天为 poor。

    Args:
        instance_id: 实例 ID。

    Returns:
        JSON 响应，包含实例信息和连接状态。

    Raises:
        NotFoundError: 当实例不存在时抛出。
        SystemError: 当获取状态失败时抛出。

    """
    instance = Instance.query.get(instance_id)
    if not instance:
        msg = "实例不存在"
        raise NotFoundError(msg)
    try:
        last_connected = instance.last_connected.isoformat() if instance.last_connected else None
        status = "unknown"
        if instance.last_connected:
            from datetime import datetime, timedelta
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
        return jsonify_unified_success(data={"instance_id": instance_id, "instance_name": instance.name, "db_type": instance.db_type, "host": instance.host, "port": instance.port, "last_connected": last_connected, "status": status, "is_active": instance.is_active}, message="获取连接状态成功")
    except Exception as exc:
        log_error("获取连接状态失败", module="connections", instance_id=instance_id, error=str(exc))
        msg = "获取连接状态失败"
        raise SystemError(msg) from exc
