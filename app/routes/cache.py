"""鲸落 - 缓存管理路由
提供缓存管理相关的API接口.
"""

from flask import Blueprint, Response, request
from flask_login import current_user, login_required

from app.errors import ConflictError, NotFoundError, ValidationError
from app.models import Instance
from app.services.account_classification.orchestrator import AccountClassificationService
from app.services.cache_service import CACHE_EXCEPTIONS, cache_manager
from app.utils.decorators import admin_required, require_csrf, update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import log_with_context, safe_route_call
from app.utils.structlog_config import log_info

# 创建蓝图
cache_bp = Blueprint("cache", __name__)


@cache_bp.route("/api/stats", methods=["GET"])
@login_required
def get_cache_stats() -> Response:
    """获取缓存统计信息.

    Returns:
        包含缓存统计数据的 JSON 响应.

    Raises:
        SystemError: 当获取统计失败时抛出.

    """

    def _load_stats() -> Response:
        stats = cache_manager.get_cache_stats()
        return jsonify_unified_success(data={"stats": stats}, message="缓存统计获取成功")

    return safe_route_call(
        _load_stats,
        module="cache",
        action="get_cache_stats",
        public_error="获取缓存统计失败",
        context={"endpoint": "stats"},
    )


@cache_bp.route("/api/clear/user", methods=["POST"])
@login_required
@admin_required
@require_csrf
def clear_user_cache() -> Response:
    """清除用户缓存.

    清除指定实例和用户名的缓存数据.

    Request Body:
        instance_id: 实例 ID.
        username: 用户名.

    Returns:
        操作结果的 JSON 响应.

    Raises:
        ValidationError: 当缺少必要参数时抛出.
        NotFoundError: 当实例不存在时抛出.
        ConflictError: 当缓存状态导致清理失败时抛出.

    """
    log_context: dict[str, object] = {}

    def _execute() -> Response:
        data = request.get_json() or {}
        instance_id = data.get("instance_id")
        username = data.get("username")
        log_context.update({"instance_id": instance_id, "username": username})

        if not instance_id or not username:
            msg = "缺少必要参数: instance_id 和 username"
            raise ValidationError(msg)

        instance = Instance.query.get(instance_id)
        if not instance:
            msg = "实例不存在"
            raise NotFoundError(msg)

        success = cache_manager.invalidate_user_cache(instance_id, username)
        if not success:
            msg = "用户缓存清除失败"
            raise ConflictError(msg)

        log_info(
            "用户缓存清除成功",
            module="cache",
            instance_id=instance_id,
            username=username,
            operator_id=getattr(current_user, "id", None),
        )
        return jsonify_unified_success(message="用户缓存清除成功")

    return safe_route_call(
        _execute,
        module="cache",
        action="clear_user_cache",
        public_error="清除用户缓存失败",
        context=log_context,
        expected_exceptions=(ValidationError, NotFoundError, ConflictError),
    )


@cache_bp.route("/api/clear/instance", methods=["POST"])
@login_required
@admin_required
@require_csrf
def clear_instance_cache() -> Response:
    """清除实例缓存.

    Returns:
        成功时返回统一成功响应,失败抛出业务异常.

    """
    log_context: dict[str, object] = {}

    def _execute() -> Response:
        data = request.get_json() or {}
        instance_id = data.get("instance_id")
        log_context.update({"instance_id": instance_id})

        if not instance_id:
            msg = "缺少必要参数: instance_id"
            raise ValidationError(msg)

        instance = Instance.query.get(instance_id)
        if not instance:
            msg = "实例不存在"
            raise NotFoundError(msg)

        success = cache_manager.invalidate_instance_cache(instance_id)
        if not success:
            msg = "实例缓存清除失败"
            raise ConflictError(msg)

        log_info(
            "实例缓存清除成功",
            module="cache",
            instance_id=instance_id,
            operator_id=getattr(current_user, "id", None),
        )
        return jsonify_unified_success(message="实例缓存清除成功")

    return safe_route_call(
        _execute,
        module="cache",
        action="clear_instance_cache",
        public_error="清除实例缓存失败",
        context=log_context,
        expected_exceptions=(ValidationError, NotFoundError, ConflictError),
    )


@cache_bp.route("/api/clear/all", methods=["POST"])
@login_required
@admin_required
@require_csrf
def clear_all_cache() -> Response:
    """清除所有缓存.

    Returns:
        统一成功响应,data 中包含已清理实例数量.

    """

    def _execute() -> Response:
        instances = Instance.query.filter_by(is_active=True).all()

        cleared_count = 0
        for instance in instances:
            try:
                if cache_manager.invalidate_instance_cache(instance.id):
                    cleared_count += 1
            except CACHE_EXCEPTIONS as exc:
                log_with_context(
                    "error",
                    "清除实例缓存失败",
                    module="cache",
                    action="clear_all_cache",
                    context={"instance_id": instance.id},
                    extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
                )

        log_info(
            "批量清除缓存完成",
            module="cache",
            cleared_count=cleared_count,
            operator_id=getattr(current_user, "id", None),
        )
        return jsonify_unified_success(
            message=f"已清除 {cleared_count} 个实例的缓存",
            data={"cleared_count": cleared_count},
        )

    return safe_route_call(
        _execute,
        module="cache",
        action="clear_all_cache",
        public_error="清除所有缓存失败",
        context={"scope": "all_instances"},
    )


# 分类缓存相关路由


@cache_bp.route("/api/classification/clear", methods=["POST"])
@login_required
@update_required
@require_csrf
def clear_classification_cache() -> Response:
    """清除分类相关缓存.

    Returns:
        成功响应,失败时抛出异常交由统一处理.

    """

    def _execute() -> Response:
        service = AccountClassificationService()
        result = service.invalidate_cache()
        if not result:
            msg = "分类缓存清除失败"
            raise ConflictError(msg)

        log_info(
            "分类缓存清除成功",
            module="cache",
            operator_id=getattr(current_user, "id", None),
        )
        return jsonify_unified_success(message="分类缓存已清除")

    return safe_route_call(
        _execute,
        module="cache",
        action="clear_classification_cache",
        public_error="清除分类缓存失败",
        context={"target": "classification"},
        expected_exceptions=(ConflictError,),
    )


@cache_bp.route("/api/classification/clear/<db_type>", methods=["POST"])
@login_required
@update_required
@require_csrf
def clear_db_type_cache(db_type: str) -> Response:
    """清除特定数据库类型的缓存.

    Args:
        db_type: 数据库类型字符串,例如 mysql.

    Returns:
        成功响应,其中 message 描述已清理的类型.

    """
    log_context: dict[str, object] = {"db_type": db_type}

    def _execute() -> Response:
        valid_db_types = {"mysql", "postgresql", "sqlserver", "oracle"}
        normalized_type = db_type.lower()
        log_context["db_type"] = normalized_type
        if normalized_type not in valid_db_types:
            msg = f"不支持的数据库类型: {db_type}"
            raise ValidationError(msg)

        service = AccountClassificationService()
        result = service.invalidate_db_type_cache(normalized_type)
        if not result:
            msg = f"数据库类型 {db_type} 缓存清除失败"
            raise ConflictError(msg)

        log_info(
            f"数据库类型 {db_type} 缓存清除成功",
            module="cache",
            operator_id=getattr(current_user, "id", None),
        )
        return jsonify_unified_success(message=f"数据库类型 {db_type} 缓存已清除")

    return safe_route_call(
        _execute,
        module="cache",
        action="clear_db_type_cache",
        public_error=f"清除数据库类型 {db_type} 缓存失败",
        context=log_context,
        expected_exceptions=(ValidationError, ConflictError),
    )


@cache_bp.route("/api/classification/stats", methods=["GET"])
@login_required
@view_required
def get_classification_cache_stats() -> Response:
    """获取分类缓存统计信息.

    Returns:
        包含缓存状态和按 db_type 划分统计的 JSON 响应.

    """

    def _execute() -> Response:
        if cache_manager is None:
            msg = "缓存管理器未初始化"
            raise ConflictError(msg)

        stats = cache_manager.get_cache_stats()
        db_type_stats: dict[str, dict[str, object]] = {}
        db_types = ["mysql", "postgresql", "sqlserver", "oracle"]

        for db_type in db_types:
            try:
                rules_cache = cache_manager.get_classification_rules_by_db_type_cache(db_type)
                db_type_stats[db_type] = {
                    "rules_cached": rules_cache is not None,
                    "rules_count": len(rules_cache) if rules_cache else 0,
                }
            except CACHE_EXCEPTIONS as exc:
                log_with_context(
                    "error",
                    "获取数据库类型缓存统计失败",
                    module="cache",
                    action="get_classification_cache_stats",
                    context={"db_type": db_type},
                    extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
                )
                db_type_stats[db_type] = {
                    "rules_cached": False,
                    "rules_count": 0,
                    "error": str(exc),
                }

        return jsonify_unified_success(
            data={
                "cache_stats": stats,
                "db_type_stats": db_type_stats,
                "cache_enabled": cache_manager is not None,
            },
            message="分类缓存统计获取成功",
        )

    return safe_route_call(
        _execute,
        module="cache",
        action="get_classification_cache_stats",
        public_error="获取分类缓存统计失败",
        context={"endpoint": "classification_stats"},
        expected_exceptions=(ConflictError,),
    )
