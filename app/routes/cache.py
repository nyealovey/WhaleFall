
"""鲸落 - 缓存管理路由
提供缓存管理相关的API接口.
"""

from flask import Blueprint, Response, request
from flask_login import current_user, login_required

from app.errors import NotFoundError, SystemError, ValidationError
from app.models import Instance
from app.services.account_classification.orchestrator import AccountClassificationService
from app.services.cache_service import cache_manager
from app.utils.decorators import admin_required, require_csrf, update_required, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
cache_bp = Blueprint("cache", __name__)


@cache_bp.route("/api/stats", methods=["GET"])
@login_required
def get_cache_stats() -> Response:
    """获取缓存统计信息..

    Returns:
        包含缓存统计数据的 JSON 响应.

    Raises:
        SystemError: 当获取统计失败时抛出.

    """
    try:
        stats = cache_manager.get_cache_stats()
    except Exception as exc:
        log_error(f"获取缓存统计失败: {exc}", module="cache")
        msg = "获取缓存统计失败"
        raise SystemError(msg) from exc

    return jsonify_unified_success(data={"stats": stats}, message="缓存统计获取成功")


@cache_bp.route("/api/clear/user", methods=["POST"])
@login_required
@admin_required
@require_csrf
def clear_user_cache() -> Response:
    """清除用户缓存..

    清除指定实例和用户名的缓存数据.

    Request Body:
        instance_id: 实例 ID.
        username: 用户名.

    Returns:
        操作结果的 JSON 响应.

    Raises:
        ValidationError: 当缺少必要参数时抛出.
        NotFoundError: 当实例不存在时抛出.
        SystemError: 当清除失败时抛出.

    """
    data = request.get_json() or {}
    instance_id = data.get("instance_id")
    username = data.get("username")

    if not instance_id or not username:
        msg = "缺少必要参数: instance_id 和 username"
        raise ValidationError(msg)

    instance = Instance.query.get(instance_id)
    if not instance:
        msg = "实例不存在"
        raise NotFoundError(msg)

    try:
        success = cache_manager.invalidate_user_cache(instance_id, username)
    except Exception as exc:
        log_error(f"清除用户缓存失败: {exc}", module="cache", instance_id=instance_id, username=username)
        msg = "清除用户缓存失败"
        raise SystemError(msg) from exc

    if not success:
        msg = "用户缓存清除失败"
        raise SystemError(msg)

    log_info(
        "用户缓存清除成功",
        module="cache",
        instance_id=instance_id,
        username=username,
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(message="用户缓存清除成功")


@cache_bp.route("/api/clear/instance", methods=["POST"])
@login_required
@admin_required
@require_csrf
def clear_instance_cache() -> Response:
    """清除实例缓存..

    Returns:
        成功时返回统一成功响应,失败抛出业务异常.

    """
    data = request.get_json() or {}
    instance_id = data.get("instance_id")

    if not instance_id:
        msg = "缺少必要参数: instance_id"
        raise ValidationError(msg)

    instance = Instance.query.get(instance_id)
    if not instance:
        msg = "实例不存在"
        raise NotFoundError(msg)

    try:
        success = cache_manager.invalidate_instance_cache(instance_id)
    except Exception as exc:
        log_error(f"清除实例缓存失败: {exc}", module="cache", instance_id=instance_id)
        msg = "清除实例缓存失败"
        raise SystemError(msg) from exc

    if not success:
        msg = "实例缓存清除失败"
        raise SystemError(msg)

    log_info(
        "实例缓存清除成功",
        module="cache",
        instance_id=instance_id,
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(message="实例缓存清除成功")


@cache_bp.route("/api/clear/all", methods=["POST"])
@login_required
@admin_required
@require_csrf
def clear_all_cache() -> Response:
    """清除所有缓存..

    Returns:
        统一成功响应,data 中包含已清理实例数量.

    """
    try:
        instances = Instance.query.filter_by(is_active=True).all()
    except Exception as exc:
        log_error(f"查询实例列表失败: {exc}", module="cache")
        msg = "清除所有缓存失败"
        raise SystemError(msg) from exc

    cleared_count = 0
    for instance in instances:
        try:
            if cache_manager.invalidate_instance_cache(instance.id):
                cleared_count += 1
        except Exception as exc:
            log_error(f"清除实例 {instance.id} 缓存失败: {exc}", module="cache")

    log_info(
        "批量清除缓存完成",
        module="cache",
        cleared_count=cleared_count,
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(message=f"已清除 {cleared_count} 个实例的缓存", data={"cleared_count": cleared_count})


# 分类缓存相关路由

@cache_bp.route("/api/classification/clear", methods=["POST"])
@login_required
@update_required
@require_csrf
def clear_classification_cache() -> Response:
    """清除分类相关缓存..

    Returns:
        成功响应,失败时抛出异常交由统一处理.

    """
    service = AccountClassificationService()
    try:
        result = service.invalidate_cache()
    except Exception as exc:
        log_error(f"清除分类缓存失败: {exc}", module="cache")
        msg = "清除分类缓存失败"
        raise SystemError(msg) from exc

    if not result:
        msg = "分类缓存清除失败"
        raise SystemError(msg)

    log_info(
        "分类缓存清除成功",
        module="cache",
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(message="分类缓存已清除")


@cache_bp.route("/api/classification/clear/<db_type>", methods=["POST"])
@login_required
@update_required
@require_csrf
def clear_db_type_cache(db_type: str) -> Response:
    """清除特定数据库类型的缓存..

    Args:
        db_type: 数据库类型字符串,例如 mysql.

    Returns:
        成功响应,其中 message 描述已清理的类型.

    """
    valid_db_types = {"mysql", "postgresql", "sqlserver", "oracle"}
    normalized_type = db_type.lower()
    if normalized_type not in valid_db_types:
        msg = f"不支持的数据库类型: {db_type}"
        raise ValidationError(msg)

    service = AccountClassificationService()
    try:
        result = service.invalidate_db_type_cache(normalized_type)
    except Exception as exc:
        log_error(f"清除数据库类型 {db_type} 缓存失败: {exc}", module="cache")
        msg = f"清除数据库类型 {db_type} 缓存失败"
        raise SystemError(msg) from exc

    if not result:
        msg = f"数据库类型 {db_type} 缓存清除失败"
        raise SystemError(msg)

    log_info(
        f"数据库类型 {db_type} 缓存清除成功",
        module="cache",
        operator_id=getattr(current_user, "id", None),
    )
    return jsonify_unified_success(message=f"数据库类型 {db_type} 缓存已清除")


@cache_bp.route("/api/classification/stats", methods=["GET"])
@login_required
@view_required
def get_classification_cache_stats() -> Response:
    """获取分类缓存统计信息..

    Returns:
        包含缓存状态和按 db_type 划分统计的 JSON 响应.

    """
    if cache_manager is None:
        msg = "缓存管理器未初始化"
        raise SystemError(msg)

    try:
        stats = cache_manager.get_cache_stats()
    except Exception as exc:
        log_error(f"获取缓存统计失败: {exc}", module="cache")
        msg = "获取分类缓存统计失败"
        raise SystemError(msg) from exc

    db_type_stats: dict[str, dict[str, object]] = {}
    db_types = ["mysql", "postgresql", "sqlserver", "oracle"]

    for db_type in db_types:
        try:
            rules_cache = cache_manager.get_classification_rules_by_db_type_cache(db_type)
            db_type_stats[db_type] = {
                "rules_cached": rules_cache is not None,
                "rules_count": len(rules_cache) if rules_cache else 0,
            }
        except Exception as exc:
            log_error(f"获取数据库类型 {db_type} 缓存统计失败: {exc}", module="cache")
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
