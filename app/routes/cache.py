
"""
鲸落 - 缓存管理路由
提供缓存管理相关的API接口
"""

from flask import Blueprint, Response, request
from flask_login import current_user, login_required

from app.utils.decorators import admin_required, require_csrf, update_required, view_required
from app.constants import DatabaseType, TaskStatus

from app.models import Instance
from app.services.cache_service import cache_manager
from app.services.account_sync.adapters.sqlserver_adapter import SQLServerAccountAdapter
from app.services.account_classification_service import AccountClassificationService
from app.errors import NotFoundError, SystemError, ValidationError
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
cache_bp = Blueprint("cache", __name__)


@cache_bp.route("/api/stats", methods=["GET"])
@login_required
def get_cache_stats() -> Response:
    """获取缓存统计信息"""
    try:
        stats = cache_manager.get_cache_stats()
    except Exception as exc:
        log_error(f"获取缓存统计失败: {exc}", module="cache")
        raise SystemError("获取缓存统计失败") from exc

    return jsonify_unified_success(data={"stats": stats}, message="缓存统计获取成功")


@cache_bp.route("/api/clear/user", methods=["POST"])
@login_required
@admin_required
@require_csrf
def clear_user_cache() -> Response:
    """清除用户缓存"""
    data = request.get_json() or {}
    instance_id = data.get("instance_id")
    username = data.get("username")

    if not instance_id or not username:
        raise ValidationError("缺少必要参数: instance_id 和 username")

    instance = Instance.query.get(instance_id)
    if not instance:
        raise NotFoundError("实例不存在")

    try:
        if instance.db_type == DatabaseType.SQLSERVER:
            adapter = SQLServerAccountAdapter()
            success = adapter.clear_user_cache(instance, username)
        else:
            success = cache_manager.invalidate_user_cache(instance_id, username)
    except Exception as exc:
        log_error(f"清除用户缓存失败: {exc}", module="cache", instance_id=instance_id, username=username)
        raise SystemError("清除用户缓存失败") from exc

    if not success:
        raise SystemError("用户缓存清除失败")

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
    """清除实例缓存"""
    data = request.get_json() or {}
    instance_id = data.get("instance_id")

    if not instance_id:
        raise ValidationError("缺少必要参数: instance_id")

    instance = Instance.query.get(instance_id)
    if not instance:
        raise NotFoundError("实例不存在")

    try:
        if instance.db_type == DatabaseType.SQLSERVER:
            adapter = SQLServerSyncAdapter()
            success = adapter.clear_instance_cache(instance)
        else:
            success = cache_manager.invalidate_instance_cache(instance_id)
    except Exception as exc:
        log_error(f"清除实例缓存失败: {exc}", module="cache", instance_id=instance_id)
        raise SystemError("清除实例缓存失败") from exc

    if not success:
        raise SystemError("实例缓存清除失败")

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
    """清除所有缓存"""
    try:
        instances = Instance.query.filter_by(is_active=True).all()
    except Exception as exc:
        log_error(f"查询实例列表失败: {exc}", module="cache")
        raise SystemError("清除所有缓存失败") from exc

    cleared_count = 0
    for instance in instances:
        try:
            if instance.db_type == DatabaseType.SQLSERVER:
                adapter = SQLServerSyncAdapter()
                if adapter.clear_instance_cache(instance):
                    cleared_count += 1
            else:
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
    """清除分类相关缓存"""
    service = AccountClassificationService()
    try:
        result = service.invalidate_cache()
    except Exception as exc:
        log_error(f"清除分类缓存失败: {exc}", module="cache")
        raise SystemError("清除分类缓存失败") from exc

    if not result:
        raise SystemError("分类缓存清除失败")

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
    """清除特定数据库类型的缓存"""
    valid_db_types = {"mysql", "postgresql", "sqlserver", "oracle"}
    normalized_type = db_type.lower()
    if normalized_type not in valid_db_types:
        raise ValidationError(f"不支持的数据库类型: {db_type}")

    service = AccountClassificationService()
    try:
        result = service.invalidate_db_type_cache(normalized_type)
    except Exception as exc:
        log_error(f"清除数据库类型 {db_type} 缓存失败: {exc}", module="cache")
        raise SystemError(f"清除数据库类型 {db_type} 缓存失败") from exc

    if not result:
        raise SystemError(f"数据库类型 {db_type} 缓存清除失败")

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
    """获取分类缓存统计信息"""
    if cache_manager is None:
        raise SystemError("缓存管理器未初始化")

    try:
        stats = cache_manager.get_cache_stats()
    except Exception as exc:
        log_error(f"获取缓存统计失败: {exc}", module="cache")
        raise SystemError("获取分类缓存统计失败") from exc

    db_type_stats = {}
    db_types = ["mysql", "postgresql", "sqlserver", "oracle"]

    for db_type in db_types:
        try:
            rules_cache = cache_manager.get_classification_rules_by_db_type_cache(db_type)
            accounts_cache = cache_manager.get_accounts_by_db_type_cache(db_type)
            db_type_stats[db_type] = {
                "rules_cached": rules_cache is not None,
                "rules_count": len(rules_cache) if rules_cache else 0,
                "accounts_cached": accounts_cache is not None,
                "accounts_count": len(accounts_cache) if accounts_cache else 0,
            }
        except Exception as exc:
            log_error(f"获取数据库类型 {db_type} 缓存统计失败: {exc}", module="cache")
            db_type_stats[db_type] = {
                "rules_cached": False,
                "rules_count": 0,
                "accounts_cached": False,
                "accounts_count": 0,
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
