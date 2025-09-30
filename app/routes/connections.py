"""
鲸落 - 数据库连接管理API
"""

import logging
from typing import Any, Dict

from flask import Blueprint, Response, jsonify, request
from flask_login import login_required

from app import db
from app.models import Instance
from app.services.connection_factory import ConnectionFactory
from app.services.connection_test_service import ConnectionTestService
from app.utils.decorators import view_required
from app.utils.structlog_config import get_sync_logger

# 创建蓝图
connections_bp = Blueprint("connections", __name__)

# 日志记录器
logger = logging.getLogger(__name__)
sync_logger = get_sync_logger()

# 服务实例
connection_test_service = ConnectionTestService()


@connections_bp.route("/api/test", methods=["POST"])
@login_required
@view_required
def test_connection() -> Response:
    """
    测试数据库连接API
    
    支持两种模式：
    1. 测试现有实例：传入 instance_id
    2. 测试新连接：传入连接参数
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据不能为空"
            }), 400

        # 检查是测试现有实例还是新连接
        if "instance_id" in data:
            return _test_existing_instance(data["instance_id"])
        else:
            return _test_new_connection(data)

    except Exception as e:
        logger.error(f"连接测试失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"连接测试失败: {str(e)}"
        }), 500


def _test_existing_instance(instance_id: int) -> Response:
    """测试现有实例连接"""
    try:
        instance = Instance.query.get(instance_id)
        if not instance:
            return jsonify({
                "success": False,
                "error": "实例不存在"
            }), 404

        # 使用连接测试服务
        result = connection_test_service.test_connection(instance)
        
        # 更新最后连接时间
        if result.get("success"):
            from app.utils.time_utils import now
            instance.last_connected = now()
            db.session.commit()

        return jsonify(result)

    except Exception as e:
        logger.error(f"测试实例连接失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"测试实例连接失败: {str(e)}"
        }), 500


def _test_new_connection(connection_params: Dict[str, Any]) -> Response:
    """测试新连接参数"""
    try:
        # 验证必需参数
        required_fields = ["db_type", "host", "port", "credential_id"]
        missing_fields = [field for field in required_fields if not connection_params.get(field)]
        
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"缺少必需参数: {', '.join(missing_fields)}"
            }), 400

        # 验证端口号
        try:
            port = int(connection_params.get("port", 0))
            if port <= 0 or port > 65535:
                return jsonify({
                    "success": False,
                    "error": "端口号必须在1-65535之间"
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "端口号必须是有效的数字"
            }), 400

        # 验证凭据
        from app.models import Credential
        credential = Credential.query.get(connection_params.get("credential_id"))
        if not credential:
            return jsonify({
                "success": False,
                "error": "凭据不存在"
            }), 404

        # 创建临时实例对象
        temp_instance = Instance(
            name=connection_params.get("name", "temp_test"),
            db_type=connection_params.get("db_type"),
            host=connection_params.get("host"),
            port=port,
            credential_id=connection_params.get("credential_id"),
            description="临时测试连接"
        )
        temp_instance.credential = credential

        # 测试连接
        result = connection_test_service.test_connection(temp_instance)
        
        return jsonify(result)

    except Exception as e:
        logger.error(f"测试新连接失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"测试新连接失败: {str(e)}"
        }), 500


@connections_bp.route("/api/supported-types", methods=["GET"])
@login_required
@view_required
def get_supported_types() -> Response:
    """获取支持的数据库类型列表"""
    try:
        supported_types = ConnectionFactory.get_supported_types()
        
        return jsonify({
            "success": True,
            "data": supported_types,
            "count": len(supported_types)
        })

    except Exception as e:
        logger.error(f"获取支持的数据库类型失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取支持的数据库类型失败: {str(e)}"
        }), 500


@connections_bp.route("/api/validate-params", methods=["POST"])
@login_required
@view_required
def validate_connection_params() -> Response:
    """验证连接参数"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "请求数据不能为空"
            }), 400

        # 验证数据库类型
        db_type = data.get("db_type", "").lower()
        if not ConnectionFactory.is_type_supported(db_type):
            return jsonify({
                "success": False,
                "error": f"不支持的数据库类型: {db_type}",
                "supported_types": ConnectionFactory.get_supported_types()
            }), 400

        # 验证端口号
        try:
            port = int(data.get("port", 0))
            if port <= 0 or port > 65535:
                return jsonify({
                    "success": False,
                    "error": "端口号必须在1-65535之间"
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "error": "端口号必须是有效的数字"
            }), 400

        # 验证凭据
        if data.get("credential_id"):
            from app.models import Credential
            credential = Credential.query.get(data.get("credential_id"))
            if not credential:
                return jsonify({
                    "success": False,
                    "error": "凭据不存在"
                }), 404

        return jsonify({
            "success": True,
            "message": "连接参数验证通过"
        })

    except Exception as e:
        logger.error(f"验证连接参数失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"验证连接参数失败: {str(e)}"
        }), 500


@connections_bp.route("/api/batch-test", methods=["POST"])
@login_required
@view_required
def batch_test_connections() -> Response:
    """批量测试连接"""
    try:
        data = request.get_json()
        if not data or "instance_ids" not in data:
            return jsonify({
                "success": False,
                "error": "缺少实例ID列表"
            }), 400

        instance_ids = data["instance_ids"]
        if not isinstance(instance_ids, list) or len(instance_ids) == 0:
            return jsonify({
                "success": False,
                "error": "实例ID列表不能为空"
            }), 400

        # 限制批量测试数量
        if len(instance_ids) > 50:
            return jsonify({
                "success": False,
                "error": "批量测试数量不能超过50个"
            }), 400

        results = []
        success_count = 0
        fail_count = 0

        for instance_id in instance_ids:
            try:
                instance = Instance.query.get(instance_id)
                if not instance:
                    results.append({
                        "instance_id": instance_id,
                        "success": False,
                        "error": "实例不存在"
                    })
                    fail_count += 1
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
                results.append({
                    "instance_id": instance_id,
                    "success": False,
                    "error": f"测试失败: {str(e)}"
                })
                fail_count += 1

        return jsonify({
            "success": True,
            "data": results,
            "summary": {
                "total": len(instance_ids),
                "success": success_count,
                "failed": fail_count
            }
        })

    except Exception as e:
        logger.error(f"批量测试连接失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"批量测试连接失败: {str(e)}"
        }), 500


@connections_bp.route("/api/status/<int:instance_id>", methods=["GET"])
@login_required
@view_required
def get_connection_status(instance_id: int) -> Response:
    """获取实例连接状态"""
    try:
        instance = Instance.query.get(instance_id)
        if not instance:
            return jsonify({
                "success": False,
                "error": "实例不存在"
            }), 404

        # 检查最后连接时间
        last_connected = instance.last_connected.isoformat() if instance.last_connected else None
        
        # 简单的连接状态检查（不实际连接）
        status = "unknown"
        if last_connected:
            from datetime import datetime, timedelta
            from app.utils.time_utils import now
            
            last_connected_time = instance.last_connected
            if isinstance(last_connected_time, str):
                last_connected_time = datetime.fromisoformat(last_connected_time.replace('Z', '+00:00'))
            
            # 如果最后连接时间在1小时内，认为状态良好
            if now() - last_connected_time < timedelta(hours=1):
                status = "good"
            elif now() - last_connected_time < timedelta(days=1):
                status = "warning"
            else:
                status = "poor"

        return jsonify({
            "success": True,
            "data": {
                "instance_id": instance_id,
                "instance_name": instance.name,
                "db_type": instance.db_type,
                "host": instance.host,
                "port": instance.port,
                "last_connected": last_connected,
                "status": status,
                "is_active": instance.is_active
            }
        })

    except Exception as e:
        logger.error(f"获取连接状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"获取连接状态失败: {str(e)}"
        }), 500
