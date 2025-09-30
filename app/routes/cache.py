
"""
鲸落 - 缓存管理路由
提供缓存管理相关的API接口
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.utils.decorators import admin_required, update_required, view_required

from app.models import Instance
from app.services.cache_manager import cache_manager
from app.services.sync_adapters.sqlserver_sync_adapter import SQLServerSyncAdapter
from app.services.account_classification_service import AccountClassificationService
from app.utils.structlog_config import get_system_logger, log_error, log_info

logger = get_system_logger()

# 创建蓝图
cache_bp = Blueprint("cache", __name__)


@cache_bp.route("/api/stats", methods=["GET"])
@login_required
def get_cache_stats() -> tuple[dict, int]:
    """获取缓存统计信息"""
    try:
        stats = cache_manager.get_cache_stats()
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        return jsonify({"success": False, "message": f"获取缓存统计失败: {str(e)}"}), 500


@cache_bp.route("/api/health", methods=["GET"])
@login_required
def check_cache_health() -> tuple[dict, int]:
    """检查缓存健康状态"""
    try:
        is_healthy = cache_manager.health_check()
        return jsonify({"success": True, "data": {"healthy": is_healthy, "status": "正常" if is_healthy else "异常"}})
    except Exception as e:
        return jsonify({"success": False, "message": f"缓存健康检查失败: {str(e)}"}), 500


@cache_bp.route("/api/clear/user", methods=["POST"])
@login_required
@admin_required
def clear_user_cache() -> tuple[dict, int]:
    """清除用户缓存"""
    try:
        data = request.get_json()
        instance_id = data.get("instance_id")
        username = data.get("username")

        if not instance_id or not username:
            return jsonify({"success": False, "message": "缺少必要参数: instance_id 和 username"}), 400

        instance = Instance.query.get(instance_id)
        if not instance:
            return jsonify({"success": False, "message": "实例不存在"}), 404

        # 根据数据库类型选择适配器
        if instance.db_type == "sqlserver":
            adapter = SQLServerSyncAdapter()
            success = adapter.clear_user_cache(instance, username)
        else:
            # 其他数据库类型暂时不支持缓存清理
            success = cache_manager.invalidate_user_cache(instance_id, username)

        return jsonify({"success": success, "message": "用户缓存清除成功" if success else "用户缓存清除失败"})

    except Exception as e:
        return jsonify({"success": False, "message": f"清除用户缓存失败: {str(e)}"}), 500


@cache_bp.route("/api/clear/instance", methods=["POST"])
@login_required
@admin_required
def clear_instance_cache() -> tuple[dict, int]:
    """清除实例缓存"""
    try:
        data = request.get_json()
        instance_id = data.get("instance_id")

        if not instance_id:
            return jsonify({"success": False, "message": "缺少必要参数: instance_id"}), 400

        instance = Instance.query.get(instance_id)
        if not instance:
            return jsonify({"success": False, "message": "实例不存在"}), 404

        # 根据数据库类型选择适配器
        if instance.db_type == "sqlserver":
            adapter = SQLServerSyncAdapter()
            success = adapter.clear_instance_cache(instance)
        else:
            # 其他数据库类型暂时不支持缓存清理
            success = cache_manager.invalidate_instance_cache(instance_id)

        return jsonify({"success": success, "message": "实例缓存清除成功" if success else "实例缓存清除失败"})

    except Exception as e:
        return jsonify({"success": False, "message": f"清除实例缓存失败: {str(e)}"}), 500


@cache_bp.route("/api/clear/all", methods=["POST"])
@login_required
@admin_required
def clear_all_cache() -> tuple[dict, int]:
    """清除所有缓存"""
    try:
        # 获取所有实例
        instances = Instance.query.filter_by(is_active=True).all()
        cleared_count = 0

        for instance in instances:
            if instance.db_type == "sqlserver":
                adapter = SQLServerSyncAdapter()
                if adapter.clear_instance_cache(instance):
                    cleared_count += 1

        return jsonify({"success": True, "message": f"已清除 {cleared_count} 个实例的缓存"})

    except Exception as e:
        return jsonify({"success": False, "message": f"清除所有缓存失败: {str(e)}"}), 500


# 分类缓存相关路由

@cache_bp.route("/api/classification/clear", methods=["POST"])
@login_required
@update_required
def clear_classification_cache() -> tuple[dict, int]:
    """清除分类相关缓存"""
    try:
        service = AccountClassificationService()
        result = service.invalidate_cache()
        
        if result:
            log_info("分类缓存清除成功", module="cache", user_id=request.user.id if hasattr(request, 'user') else None)
            return jsonify({"success": True, "message": "分类缓存已清除"})
        else:
            return jsonify({"success": False, "error": "缓存清除失败"})
            
    except Exception as e:
        log_error(f"清除分类缓存失败: {e}", module="cache")
        return jsonify({"success": False, "error": str(e)}), 500


@cache_bp.route("/api/classification/clear/<db_type>", methods=["POST"])
@login_required
@update_required
def clear_db_type_cache(db_type: str) -> tuple[dict, int]:
    """清除特定数据库类型的缓存"""
    try:
        # 验证数据库类型
        valid_db_types = ["mysql", "postgresql", "sqlserver", "oracle"]
        if db_type.lower() not in valid_db_types:
            return jsonify({"success": False, "error": f"不支持的数据库类型: {db_type}"}), 400
        
        service = AccountClassificationService()
        result = service.invalidate_db_type_cache(db_type.lower())
        
        if result:
            log_info(f"数据库类型 {db_type} 缓存清除成功", module="cache", user_id=request.user.id if hasattr(request, 'user') else None)
            return jsonify({"success": True, "message": f"数据库类型 {db_type} 缓存已清除"})
        else:
            return jsonify({"success": False, "error": f"数据库类型 {db_type} 缓存清除失败"})
            
    except Exception as e:
        log_error(f"清除数据库类型 {db_type} 缓存失败: {e}", module="cache")
        return jsonify({"success": False, "error": str(e)}), 500


@cache_bp.route("/api/classification/stats", methods=["GET"])
@login_required
@view_required
def get_classification_cache_stats() -> tuple[dict, int]:
    """获取分类缓存统计信息"""
    try:
        if not cache_manager:
            return jsonify({"success": False, "error": "缓存管理器未初始化"}), 500
            
        stats = cache_manager.get_cache_stats()
        
        # 获取按数据库类型的缓存统计
        db_type_stats = {}
        db_types = ["mysql", "postgresql", "sqlserver", "oracle"]
        
        for db_type in db_types:
            try:
                # 检查规则缓存
                rules_cache = cache_manager.get_classification_rules_by_db_type_cache(db_type)
                # 检查账户缓存
                accounts_cache = cache_manager.get_accounts_by_db_type_cache(db_type)
                
                db_type_stats[db_type] = {
                    "rules_cached": rules_cache is not None,
                    "rules_count": len(rules_cache) if rules_cache else 0,
                    "accounts_cached": accounts_cache is not None,
                    "accounts_count": len(accounts_cache) if accounts_cache else 0
                }
            except Exception as e:
                log_error(f"获取数据库类型 {db_type} 缓存统计失败: {e}", module="cache")
                db_type_stats[db_type] = {
                    "rules_cached": False,
                    "rules_count": 0,
                    "accounts_cached": False,
                    "accounts_count": 0,
                    "error": str(e)
                }
        
        return jsonify({
            "success": True, 
            "cache_stats": stats,
            "db_type_stats": db_type_stats,
            "cache_enabled": cache_manager is not None
        })
        
    except Exception as e:
        log_error(f"获取分类缓存统计失败: {e}", module="cache")
        return jsonify({"success": False, "error": str(e)}), 500
