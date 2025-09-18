"""
泰摸鱼吧 - 缓存管理路由
提供缓存管理相关的API接口
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.models import Instance
from app.services.cache_manager import cache_manager
from app.services.sync_adapters.sqlserver_sync_adapter import SQLServerSyncAdapter
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()

cache_bp = Blueprint("cache", __name__)


@cache_bp.route("/cache/stats", methods=["GET"])
@login_required
def get_cache_stats() -> tuple[dict, int]:
    """获取缓存统计信息"""
    try:
        stats = cache_manager.get_cache_stats()
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        return jsonify({"success": False, "message": f"获取缓存统计失败: {str(e)}"}), 500


@cache_bp.route("/cache/health", methods=["GET"])
@login_required
def check_cache_health() -> tuple[dict, int]:
    """检查缓存健康状态"""
    try:
        is_healthy = cache_manager.health_check()
        return jsonify({"success": True, "data": {"healthy": is_healthy, "status": "正常" if is_healthy else "异常"}})
    except Exception as e:
        return jsonify({"success": False, "message": f"缓存健康检查失败: {str(e)}"}), 500


@cache_bp.route("/cache/clear/user", methods=["POST"])
@login_required
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


@cache_bp.route("/cache/clear/instance", methods=["POST"])
@login_required
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


@cache_bp.route("/cache/clear/all", methods=["POST"])
@login_required
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
