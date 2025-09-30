"""
聚合统计路由
专注于核心聚合功能：聚合计算、状态管理、汇总统计
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from app.utils.time_utils import time_utils
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_, or_
from app.models.instance import Instance
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.services.database_size_aggregation_service import DatabaseSizeAggregationService
from app.tasks.database_size_aggregation_tasks import (
    calculate_database_size_aggregations,
    calculate_instance_aggregations,
    calculate_period_aggregations,
    get_aggregation_status
)
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
aggregations_bp = Blueprint('aggregations', __name__)

# 页面路由
@aggregations_bp.route('/instance', methods=['GET'])
@login_required
@view_required
def instance_aggregations():
    """
    实例统计聚合页面
    返回HTML页面
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
    
    return render_template('database_sizes/instance_aggregations.html', 
                         instances_list=instances_list)

@aggregations_bp.route('/database', methods=['GET'])
@login_required
@view_required
def database_aggregations():
    """
    数据库统计聚合页面
    返回HTML页面
    """
    # 获取数据库类型列表
    db_types = db.session.query(Instance.db_type).distinct().all()
    db_types_list = [db_type[0] for db_type in db_types]
    
    return render_template('database_sizes/database_aggregations.html', 
                         db_types_list=db_types_list)

# 核心聚合功能API
@aggregations_bp.route('/api/summary', methods=['GET'])
@login_required
@view_required
def get_aggregations_summary():
    """
    获取统计聚合数据汇总统计
    
    Returns:
        JSON: 汇总统计信息
    """
    try:
        # 获取基本统计
        total_aggregations = DatabaseSizeAggregation.query.count()
        total_instances = Instance.query.filter_by(is_active=True).count()
        
        # 获取数据库数量统计
        total_databases = db.session.query(
            func.count(func.distinct(DatabaseSizeAggregation.database_name))
        ).scalar() or 0
        
        # 获取大小统计
        size_stats = db.session.query(
            func.sum(DatabaseSizeAggregation.avg_size_mb).label('total_size_mb'),
            func.avg(DatabaseSizeAggregation.avg_size_mb).label('avg_size_mb'),
            func.max(DatabaseSizeAggregation.avg_size_mb).label('max_size_mb')
        ).first()
        
        # 获取最近更新时间
        latest_aggregation = DatabaseSizeAggregation.query.order_by(
            desc(DatabaseSizeAggregation.calculated_at)
        ).first()
        
        return jsonify({
            'success': True,
            'data': {
                'total_aggregations': total_aggregations,
                'total_instances': total_instances,
                'total_databases': total_databases,
                'total_size_mb': float(size_stats.total_size_mb) if size_stats.total_size_mb else 0,
                'avg_size_mb': float(size_stats.avg_size_mb) if size_stats.avg_size_mb else 0,
                'max_size_mb': float(size_stats.max_size_mb) if size_stats.max_size_mb else 0,
                'last_updated': latest_aggregation.calculated_at.isoformat() if latest_aggregation else None
            }
        })
        
    except Exception as e:
        logger.error(f"获取聚合汇总统计时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@aggregations_bp.route('/api/manual_aggregate', methods=['POST'])
@login_required
@view_required
def manual_aggregate():
    """
    手动触发聚合计算
    
    Returns:
        JSON: 聚合结果
    """
    try:
        data = request.get_json() or {}
        instance_id = data.get('instance_id')
        period_type = data.get('period_type', 'daily')
        
        if instance_id:
            # 计算指定实例的聚合
            result = calculate_instance_aggregations(instance_id, period_type)
        else:
            # 计算所有实例的聚合
            result = calculate_database_size_aggregations(period_type)
        
        return jsonify({
            'success': True,
            'message': '聚合计算任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"手动触发聚合计算失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@aggregations_bp.route('/api/aggregate', methods=['POST'])
@login_required
@view_required
def aggregate():
    """
    手动触发统计聚合计算
    
    Returns:
        JSON: 聚合结果
    """
    try:
        data = request.get_json() or {}
        period_type = data.get('period_type', 'daily')
        
        # 触发聚合计算
        result = calculate_database_size_aggregations(period_type)
        
        return jsonify({
            'success': True,
            'message': '统计聚合计算任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"触发统计聚合计算失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@aggregations_bp.route('/api/aggregate-today', methods=['POST'])
@login_required
@view_required
def aggregate_today():
    """
    手动触发今日数据聚合
    
    Returns:
        JSON: 聚合结果
    """
    try:
        # 触发今日数据聚合
        result = calculate_period_aggregations('daily')
        
        return jsonify({
            'success': True,
            'message': '今日数据聚合任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"触发今日数据聚合失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@aggregations_bp.route('/api/aggregate/status', methods=['GET'])
@login_required
@view_required
def get_aggregation_status():
    """
    获取聚合状态信息
    
    Returns:
        JSON: 聚合状态
    """
    try:
        # 获取聚合状态
        status = get_aggregation_status()
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': time_utils.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取聚合状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
