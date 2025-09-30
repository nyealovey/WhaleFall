"""
存储同步 API 路由
专注于数据同步功能，不包含统计功能
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app, render_template
from app.utils.time_utils import time_utils
from flask_login import login_required, current_user
from sqlalchemy import and_, desc, func
from app.models.instance import Instance
from app.services.database_size_collector_service import collect_all_instances_database_sizes
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
storage_sync_bp = Blueprint('storage_sync', __name__)

# 页面路由 - 存储同步主页面
@storage_sync_bp.route('/', methods=['GET'])
@login_required
@view_required
def storage_sync():
    """
    存储同步主页面
    """
    # 获取实例列表用于筛选
    instances = Instance.query.filter_by(is_active=True).order_by(Instance.id).all()
    instances_list = []
    for instance in instances:
        instances_list.append({
            'id': instance.id,
            'name': instance.name,
            'db_type': instance.db_type
        })
    
    return render_template('database_sizes/storage_sync.html', 
                         instances_list=instances_list)


@storage_sync_bp.route('/api/test_connection', methods=['POST'])
@login_required
@view_required
def test_connection():
    """
    测试数据库连接（已弃用，请使用 /connections/api/test）
    """
    return jsonify({
        'success': False,
        'error': '此API已弃用，请使用 /connections/api/test'
    }), 410


@storage_sync_bp.route('/api/instances', methods=['GET'])
@login_required
@view_required
def get_instances():
    """
    获取实例列表
    
    Returns:
        JSON: 实例列表
    """
    try:
        instances = Instance.query.filter_by(is_active=True).order_by(Instance.id).all()
        
        data = []
        for instance in instances:
            data.append({
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port,
                'is_active': instance.is_active
            })
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.error(f"获取实例列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@storage_sync_bp.route("/api/instances/<int:instance_id>/sync-capacity", methods=["POST"])
@view_required("instance_management.instance_list.sync_capacity")
def sync_instance_capacity(instance_id: int):
    """
    同步指定实例的容量信息

    Args:
        instance_id (int): 实例ID

    Returns:
        json: 同步结果
    """
    try:
        instance = Instance.query.get_or_404(instance_id)
        logger.info(
            "用户操作: 开始同步容量",
            extra={
                "operation": "sync_capacity",
                "instance_id": instance.id,
                "instance_name": instance.name,
                "action": "开始同步容量",
                "user_action": True,
            },
        )

        # 触发指定实例的容量同步
        # 运行时导入以避免潜在的加载顺序问题
        from app.tasks.database_size_collection_tasks import collect_specific_instance_database_sizes
        result = collect_specific_instance_database_sizes(instance_id)

        if result and result.get("success"):
            logger.info(
                "同步实例容量成功",
                extra={
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "action": "同步容量成功",
                    "user_action": True,
                },
            )
            return jsonify({
                'success': True,
                'message': f'实例 {instance.name} 的容量同步任务已成功完成',
                'data': result
            })
        else:
            logger.warning(
                "同步实例容量失败",
                extra={
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "action": "同步容量失败",
                    "user_action": True,
                    "result": result,
                },
            )
            return jsonify({
                'success': False,
                'message': f'实例 {instance.name} 的容量同步失败: {result.get("message", "未知错误")}',
                'error': result.get('error', '任务返回失败状态但没有提供错误信息。')
            }), 400
        
    except Exception as e:
        logger.error(f"同步实例 {instance_id} 容量失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
