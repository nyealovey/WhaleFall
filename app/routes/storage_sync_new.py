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
from app.tasks.database_size_collection_tasks import (
    collect_database_sizes,
    collect_specific_instance_database_sizes,
    collect_database_sizes_by_type,
    get_collection_status
)
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

@storage_sync_bp.route('/api/status', methods=['GET'])
@login_required
@view_required
def get_sync_status():
    """
    获取数据库大小监控状态
    
    Returns:
        JSON: 监控状态信息
    """
    try:
        # 获取采集状态
        status = get_collection_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': time_utils.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取监控状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@storage_sync_bp.route('/api/stats', methods=['GET'])
@login_required
@view_required
def get_sync_stats():
    """
    获取数据库大小监控统计信息
    
    Returns:
        JSON: 统计信息
    """
    try:
        from app.models.database_size_stat import DatabaseSizeStat
        from app.models.instance_size_stat import InstanceSizeStat
        
        # 获取基本统计信息
        total_records = DatabaseSizeStat.query.count()
        total_instances = InstanceSizeStat.query.filter_by(is_deleted=False).count()
        
        # 获取最近24小时的数据
        yesterday = time_utils.now_china().date() - timedelta(days=1)
        recent_records = DatabaseSizeStat.query.filter(
            DatabaseSizeStat.collected_date >= yesterday
        ).count()
        
        return jsonify({
            'success': True,
            'data': {
                'total_records': total_records,
                'total_instances': total_instances,
                'recent_records_24h': recent_records,
                'last_updated': time_utils.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

@storage_sync_bp.route('/api/manual_collect', methods=['POST'])
@login_required
@view_required
def manual_collect():
    """
    手动触发数据采集
    
    Returns:
        JSON: 采集结果
    """
    try:
        data = request.get_json() or {}
        instance_id = data.get('instance_id')
        db_type = data.get('db_type')
        
        if instance_id:
            # 采集指定实例
            result = collect_specific_instance_database_sizes(instance_id)
        elif db_type:
            # 按数据库类型采集
            result = collect_database_sizes_by_type(db_type)
        else:
            # 采集所有实例
            result = collect_database_sizes()
        
        return jsonify({
            'success': True,
            'message': '数据采集任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"手动采集数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

@storage_sync_bp.route('/api/collect', methods=['POST'])
@login_required
@view_required
def collect_data():
    """
    手动触发数据库大小采集
    
    Returns:
        JSON: 采集结果
    """
    try:
        # 触发采集任务
        result = collect_database_sizes()
        
        return jsonify({
            'success': True,
            'message': '数据库大小采集任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"触发采集任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@storage_sync_bp.route("/api/instances/<int:instance_id>/sync-capacity", methods=['POST'])
@login_required
@view_required
def sync_instance_capacity(instance_id: int):
    """
    同步指定实例的数据库容量信息
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 同步结果
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 触发指定实例的容量同步
        result = collect_specific_instance_database_sizes(instance_id)
        
        return jsonify({
            'success': True,
            'message': f'实例 {instance.name} 的容量同步任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"同步实例 {instance_id} 容量失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
