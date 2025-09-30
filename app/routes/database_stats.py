"""
数据库统计 API 路由
提供数据库大小监控、历史数据、统计聚合等接口
专注于数据库层面的统计功能
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from app.utils.time_utils import time_utils
from flask_login import login_required, current_user
from sqlalchemy import and_, desc, func
from app.models.instance import Instance
from app.models.database_size_stat import DatabaseSizeStat
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
database_stats_bp = Blueprint('database_stats', __name__)

@database_stats_bp.route('/api/instances/<int:instance_id>/database-sizes/total', methods=['GET'])
@login_required
@view_required
def get_instance_total_size(instance_id: int):
    """
    获取指定实例的数据库总大小（从InstanceSizeStat表获取）
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 实例总大小信息
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 从InstanceSizeStat表获取最新的实例大小统计数据
        from app.models.instance_size_stat import InstanceSizeStat
        
        latest_stat = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.is_deleted == False
        ).order_by(InstanceSizeStat.collected_date.desc()).first()
        
        if not latest_stat:
            return jsonify({
                'success': True,
                'total_size_mb': 0,
                'database_count': 0,
                'last_collected': None
            })
        
        # 直接使用实例大小统计数据
        total_size_mb = latest_stat.total_size_mb
        database_count = latest_stat.database_count
        last_collected = latest_stat.collected_date
        
        return jsonify({
            'success': True,
            'total_size_mb': total_size_mb,
            'database_count': database_count,
            'last_collected': last_collected.isoformat() if last_collected else None
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 总大小失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_stats_bp.route('/api/instances/<int:instance_id>/database-sizes', methods=['GET'])
@login_required
@view_required
def get_instance_database_sizes(instance_id: int):
    """
    获取指定实例的数据库大小历史数据
    先从instance_databases获取所有数据库（包括软删除的），再从database_size_stats获取最新容量
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 数据库大小历史数据
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取查询参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        database_name = request.args.get('database_name')
        latest_only = request.args.get('latest_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # 直接从 database_size_stats 表查询数据库大小数据
        from sqlalchemy import func
        
        if latest_only:
            # 使用窗口函数获取每个数据库的最新记录
            from sqlalchemy import text
            
            # 使用原生SQL查询，避免SQLAlchemy窗口函数语法问题
            sql_query = text("""
                SELECT * FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (
                               PARTITION BY database_name 
                               ORDER BY collected_date DESC
                           ) as rn
                    FROM database_size_stats 
                    WHERE instance_id = :instance_id
                ) ranked
                WHERE rn = 1
            """)
            
            # 执行原生SQL查询
            result = db.session.execute(sql_query, {'instance_id': instance_id})
            stats = []
            for row in result:
                # 手动构建DatabaseSizeStat对象
                stat = DatabaseSizeStat()
                stat.id = row.id
                stat.instance_id = row.instance_id
                stat.database_name = row.database_name
                stat.size_mb = row.size_mb
                stat.data_size_mb = row.data_size_mb
                stat.log_size_mb = row.log_size_mb
                stat.collected_date = row.collected_date
                stat.collected_at = row.collected_at
                stats.append(stat)
            
            # 应用数据库名称筛选
            if database_name:
                stats = [stat for stat in stats if database_name.lower() in stat.database_name.lower()]
            
            # 应用日期筛选条件
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    stats = [stat for stat in stats if stat.collected_date >= start_date_obj]
                except ValueError:
                    return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
            
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    stats = [stat for stat in stats if stat.collected_date <= end_date_obj]
                except ValueError:
                    return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
            
            # 排序
            stats.sort(key=lambda x: x.collected_date, reverse=True)
            
            # 分页
            total_count = len(stats)
            stats = stats[offset:offset + limit]
            
            # 构建返回数据
            data = []
            for stat in stats:
                data.append({
                    'database_name': stat.database_name,
                    'is_active': True,
                    'first_seen_date': stat.collected_date.isoformat(),
                    'last_seen_date': stat.collected_date.isoformat(),
                    'deleted_at': None,
                    'id': stat.id,
                    'size_mb': stat.size_mb,
                    'data_size_mb': stat.data_size_mb,
                    'log_size_mb': stat.log_size_mb,
                    'collected_date': stat.collected_date.isoformat(),
                    'collected_at': stat.collected_at.isoformat() if stat.collected_at else None
                })
            
            return jsonify({
                'success': True,
                'data': data,
                'total_count': total_count,
                'limit': limit,
                'offset': offset
            })
        
        else:
            # 查询历史数据
            query = DatabaseSizeStat.query.filter(
                DatabaseSizeStat.instance_id == instance_id
            )
            
            # 应用筛选条件
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    query = query.filter(DatabaseSizeStat.collected_date >= start_date_obj)
                except ValueError:
                    return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
            
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    query = query.filter(DatabaseSizeStat.collected_date <= end_date_obj)
                except ValueError:
                    return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
            
            if database_name:
                query = query.filter(DatabaseSizeStat.database_name.ilike(f'%{database_name}%'))
            
            # 排序和分页
            query = query.order_by(desc(DatabaseSizeStat.collected_date))
            total_count = query.count()
            stats = query.offset(offset).limit(limit).all()
            
            # 构建返回数据
            data = []
            for stat in stats:
                data.append({
                    'database_name': stat.database_name,
                    'is_active': True,
                    'first_seen_date': stat.collected_date.isoformat(),
                    'last_seen_date': stat.collected_date.isoformat(),
                    'deleted_at': None,
                    'id': stat.id,
                    'size_mb': stat.size_mb,
                    'data_size_mb': stat.data_size_mb,
                    'log_size_mb': stat.log_size_mb,
                    'collected_date': stat.collected_date.isoformat(),
                    'collected_at': stat.collected_at.isoformat() if stat.collected_at else None
                })
            
            return jsonify({
                'success': True,
                'data': data,
                'total_count': total_count,
                'limit': limit,
                'offset': offset
            })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 数据库大小历史数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_stats_bp.route('/api/instances/<int:instance_id>/database-sizes/summary', methods=['GET'])
@login_required
@view_required
def get_instance_database_summary(instance_id: int):
    """
    获取指定实例的数据库大小汇总信息
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 汇总信息
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取最近30天的数据
        thirty_days_ago = time_utils.now_china().date() - timedelta(days=30)
        
        # 查询最近30天的数据
        recent_stats = DatabaseSizeStat.query.filter(
            DatabaseSizeStat.instance_id == instance_id,
            DatabaseSizeStat.collected_date >= thirty_days_ago
        ).all()
        
        if not recent_stats:
            return jsonify({
                'data': {
                    'total_databases': 0,
                    'total_size_mb': 0,
                    'average_size_mb': 0,
                    'largest_database': None,
                    'growth_rate': 0,
                    'last_collected': None
                },
                'instance': {
                    'id': instance.id,
                    'name': instance.name,
                    'db_type': instance.db_type
                }
            })
        
        # 按数据库分组计算统计
        db_stats = {}
        for stat in recent_stats:
            db_name = stat.database_name
            if db_name not in db_stats:
                db_stats[db_name] = []
            db_stats[db_name].append(stat)
        
        # 计算每个数据库的最新大小
        latest_db_sizes = {}
        for db_name, stats in db_stats.items():
            # 按日期排序，取最新的
            latest_stat = max(stats, key=lambda x: x.collected_date)
            latest_db_sizes[db_name] = latest_stat.size_mb
        
        # 计算汇总统计
        total_databases = len(latest_db_sizes)
        total_size_mb = sum(latest_db_sizes.values())
        average_size_mb = total_size_mb / total_databases if total_databases > 0 else 0
        
        # 找出最大的数据库
        largest_database = None
        if latest_db_sizes:
            largest_db_name = max(latest_db_sizes, key=latest_db_sizes.get)
            largest_database = {
                'name': largest_db_name,
                'size_mb': latest_db_sizes[largest_db_name]
            }
        
        # 计算增长率（比较30天前和现在）
        growth_rate = 0
        if len(recent_stats) >= 2:
            # 按日期排序
            sorted_stats = sorted(recent_stats, key=lambda x: x.collected_date)
            oldest_date = sorted_stats[0].collected_date
            newest_date = sorted_stats[-1].collected_date
            
            # 计算30天前的总大小
            thirty_days_ago_stats = [s for s in recent_stats if s.collected_date <= oldest_date + timedelta(days=1)]
            if thirty_days_ago_stats:
                old_total = sum(s.size_mb for s in thirty_days_ago_stats)
                new_total = sum(s.size_mb for s in recent_stats)
                if old_total > 0:
                    growth_rate = ((new_total - old_total) / old_total) * 100
        
        # 获取最后采集时间
        last_collected = max(recent_stats, key=lambda x: x.collected_date).collected_date
        
        return jsonify({
            'data': {
                'total_databases': total_databases,
                'total_size_mb': total_size_mb,
                'average_size_mb': average_size_mb,
                'largest_database': largest_database,
                'growth_rate': growth_rate,
                'last_collected': last_collected.isoformat() if last_collected else None
            },
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type
            }
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 数据库汇总信息失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_stats_bp.route('/api/instances/<int:instance_id>/databases', methods=['GET'])
@login_required
@view_required
def get_instance_databases(instance_id: int):
    """
    获取指定实例的数据库列表
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 数据库列表
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取查询参数
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # 查询数据库列表
        from app.models.instance_database import InstanceDatabase
        
        query = InstanceDatabase.query.filter(
            InstanceDatabase.instance_id == instance_id
        ).order_by(InstanceDatabase.database_name)
        
        total_count = query.count()
        databases = query.offset(offset).limit(limit).all()
        
        # 构建返回数据
        data = []
        for db in databases:
            data.append({
                'id': db.id,
                'database_name': db.database_name,
                'is_active': not db.is_deleted,
                'first_seen_date': db.first_seen_date.isoformat() if db.first_seen_date else None,
                'last_seen_date': db.last_seen_date.isoformat() if db.last_seen_date else None,
                'deleted_at': db.deleted_at.isoformat() if db.deleted_at else None
            })
        
        return jsonify({
            'success': True,
            'data': data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 数据库列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
