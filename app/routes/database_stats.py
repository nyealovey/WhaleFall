"""
数据库统计 API 路由
提供数据库大小监控、历史数据、统计聚合等接口
专注于数据库层面的统计功能
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app, render_template
from app.utils.time_utils import time_utils
from flask_login import login_required, current_user
from sqlalchemy import and_, desc, func
from app.models.instance import Instance
from app.models.database_size_stat import DatabaseSizeStat
from app.utils.decorators import view_required
from app.services.database_type_service import DatabaseTypeService
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
database_stats_bp = Blueprint('database_stats', __name__)

# 页面路由
# 实例统计页面已移动到 instance_stats 模块中

@database_stats_bp.route('/database', methods=['GET'])
@login_required
@view_required
def database_aggregations():
    """
    数据库统计聚合页面（数据库统计层面）
    返回HTML页面
    """
    # 获取数据库类型列表
    database_types = [
        {
            'name': db_type.name,
            'display_name': db_type.display_name
        }
        for db_type in DatabaseTypeService.get_active_types()
    ]
    instances = Instance.query.filter_by(is_active=True).order_by(Instance.name.asc()).all()
    instances_list = [{
        'id': instance.id,
        'name': instance.name,
        'db_type': instance.db_type
    } for instance in instances]
    
    selected_db_type = request.args.get('db_type', '')
    selected_instance = request.args.get('instance', '')
    selected_database_id = request.args.get('database_id', '')
    selected_database = request.args.get('database', '')
    if not selected_database_id and selected_database:
        from app.models.instance_database import InstanceDatabase
        instance_filter = InstanceDatabase.query.filter(InstanceDatabase.database_name == selected_database)
        if selected_instance := request.args.get('instance'):
            try:
                instance_filter = instance_filter.filter(InstanceDatabase.instance_id == int(selected_instance))
            except ValueError:
                pass
        db_record = instance_filter.first()
        if db_record:
            selected_database_id = str(db_record.id)
    if selected_database_id:
        selected_database = ''
    selected_period_type = request.args.get('period_type', 'daily')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    return render_template(
        'database_sizes/database_aggregations.html',
        database_types=database_types,
        instances_list=instances_list,
        databases_list=[],
        db_type=selected_db_type,
        instance=selected_instance,
        database_id=selected_database_id,
        database=selected_database,
        period_type=selected_period_type,
        start_date=start_date,
        end_date=end_date
    )

# 实例总大小API已移动到 instance_stats 模块中


# 实例选项API已移动到 instance_stats 模块中


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
            
            total_size_mb = sum(stat.size_mb or 0 for stat in stats)
            database_count = len(stats)

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
                'database_count': database_count,
                'limit': limit,
                'offset': offset,
                'total_size_mb': total_size_mb
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


# 实例聚合API已移动到 instance_stats 模块中


# 实例聚合汇总API已移动到 instance_stats 模块中

@database_stats_bp.route('/api/databases/aggregations', methods=['GET'])
@login_required
@view_required
def get_databases_aggregations():
    """
    获取数据库统计聚合数据（数据库统计层面）
    原 /api/database 功能
    
    Returns:
        JSON: 数据库聚合数据
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        database_name = request.args.get('database_name')
        database_id = request.args.get('database_id', type=int)
        period_type = request.args.get('period_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        # 是否返回所有数据（用于图表显示）
        get_all = request.args.get('get_all', 'false').lower() == 'true'
        
        # 计算offset
        offset = (page - 1) * per_page
        limit = per_page
        
        # 构建查询 - 直接查询聚合统计表
        from app.models.database_size_aggregation import DatabaseSizeAggregation
        query = DatabaseSizeAggregation.query.join(Instance)
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(DatabaseSizeAggregation.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)
        elif database_id:
            from app.models.instance_database import InstanceDatabase
            db_record = InstanceDatabase.query.filter_by(id=database_id).first()
            if db_record:
                query = query.filter(DatabaseSizeAggregation.database_name == db_record.database_name)
        if period_type:
            query = query.filter(DatabaseSizeAggregation.period_type == period_type)
        if start_date:
            query = query.filter(DatabaseSizeAggregation.period_start >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(DatabaseSizeAggregation.period_end <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # 排序和分页
        if get_all:
            base_query = query.with_entities(
                DatabaseSizeAggregation.instance_id,
                DatabaseSizeAggregation.database_name,
                func.max(DatabaseSizeAggregation.avg_size_mb).label('max_avg_size_mb')
            ).group_by(DatabaseSizeAggregation.instance_id, DatabaseSizeAggregation.database_name).subquery()

            top_pairs = db.session.query(
                base_query.c.instance_id,
                base_query.c.database_name
            ).order_by(desc(base_query.c.max_avg_size_mb)).limit(100).all()

            if top_pairs:
                from sqlalchemy import tuple_
                pair_values = [(row.instance_id, row.database_name) for row in top_pairs]
                aggregations = query.filter(
                    tuple_(DatabaseSizeAggregation.instance_id, DatabaseSizeAggregation.database_name).in_(pair_values)
                ).order_by(DatabaseSizeAggregation.period_start.asc()).all()
                total = len(aggregations)
            else:
                aggregations = []
                total = 0
        else:
            # 用于表格显示：按时间排序分页
            query = query.order_by(desc(DatabaseSizeAggregation.period_start))
            total = query.count()
            aggregations = query.offset(offset).limit(limit).all()
        
        # 转换为字典格式，包含实例信息
        data = []
        for agg in aggregations:
            agg_dict = agg.to_dict()
            # 添加实例信息
            agg_dict['instance'] = {
                'id': agg.instance.id,
                'name': agg.instance.name,
                'db_type': agg.instance.db_type
            }
            data.append(agg_dict)

        
        return jsonify({
            'success': True,
            'data': data,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'has_prev': page > 1,
            'has_next': page < (total + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"获取数据库统计聚合数据时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@database_stats_bp.route('/api/databases/aggregations/summary', methods=['GET'])
@login_required
@view_required
def get_databases_aggregations_summary():
    """
    获取数据库统计聚合汇总信息（数据库统计层面）
    原 /api/database/summary 功能
    
    Returns:
        JSON: 数据库聚合汇总信息
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        database_name = request.args.get('database_name')
        database_id = request.args.get('database_id', type=int)
        period_type = request.args.get('period_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 构建查询
        from app.models.database_size_aggregation import DatabaseSizeAggregation
        query = DatabaseSizeAggregation.query.join(Instance)
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(DatabaseSizeAggregation.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)
        elif database_id:
            from app.models.instance_database import InstanceDatabase
            db_record = InstanceDatabase.query.filter_by(id=database_id).first()
            if db_record:
                query = query.filter(DatabaseSizeAggregation.database_name == db_record.database_name)
        if period_type:
            query = query.filter(DatabaseSizeAggregation.period_type == period_type)
        if start_date:
            query = query.filter(DatabaseSizeAggregation.period_start >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(DatabaseSizeAggregation.period_end <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # 获取聚合数据
        aggregations = query.all()
        
        if not aggregations:
            return jsonify({
                'success': True,
                'data': {
                    'total_databases': 0,
                    'total_instances': 0,
                    'total_size_mb': 0,
                    'avg_size_mb': 0,
                    'max_size_mb': 0,
                    'period_type': period_type or 'all'
                }
            })
        
        # 计算汇总统计
        total_databases = len(set(agg.database_name for agg in aggregations))
        total_instances = len(set(agg.instance_id for agg in aggregations))
        total_size_mb = sum(agg.avg_size_mb for agg in aggregations)
        avg_size_mb = total_size_mb / len(aggregations) if aggregations else 0
        max_size_mb = max(agg.avg_size_mb for agg in aggregations) if aggregations else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_databases': total_databases,
                'total_instances': total_instances,
                'total_size_mb': total_size_mb,
                'avg_size_mb': avg_size_mb,
                'max_size_mb': max_size_mb,
                'period_type': period_type or 'all'
            }
        })
        
    except Exception as e:
        logger.error(f"获取数据库统计聚合汇总时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500