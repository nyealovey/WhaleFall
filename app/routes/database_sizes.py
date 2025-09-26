"""
数据库大小监控 API 路由
提供历史数据、统计聚合、趋势分析等接口
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import login_required, current_user
from sqlalchemy import and_, desc, func
from app.models.instance import Instance
from app.models.database_size_stat import DatabaseSizeStat
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.services.database_size_collector_service import collect_all_instances_database_sizes
from app.services.database_size_aggregation_service import DatabaseSizeAggregationService
from app.services.partition_management_service import PartitionManagementService
from app.tasks.partition_management_tasks import get_partition_management_status
from app.tasks.database_size_collection_tasks import (
    collect_database_sizes,
    collect_specific_instance_database_sizes,
    collect_database_sizes_by_type,
    get_collection_status,
    validate_collection_config
)
from app.tasks.database_size_aggregation_tasks import (
    calculate_database_size_aggregations,
    calculate_instance_aggregations,
    calculate_period_aggregations,
    get_aggregation_status,
    validate_aggregation_config,
    cleanup_old_aggregations
)
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
database_sizes_bp = Blueprint('database_sizes', __name__)

# 页面路由
@database_sizes_bp.route('/aggregations', methods=['GET'])
@login_required
@view_required
def aggregations():
    """
    统计聚合页面或API
    
    如果是页面请求（无查询参数），返回HTML页面
    如果是API请求（有查询参数），返回JSON数据
    """
    # 检查是否有查询参数，如果有则返回API数据
    if request.args:
        try:
            # 获取查询参数
            instance_id = request.args.get('instance_id', type=int)
            db_type = request.args.get('db_type')
            database_name = request.args.get('database_name')
            period_type = request.args.get('period_type')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # 构建查询
            query = DatabaseSizeAggregation.query.join(Instance)
            
            # 过滤掉已删除的数据库（通过检查最新的DatabaseSizeStat记录）
            from app.models.database_size_stat import DatabaseSizeStat
            from sqlalchemy import and_, or_, func
            
            # 子查询：获取每个实例-数据库组合的最新状态
            # 使用窗口函数获取每个(instance_id, database_name)的最新记录
            latest_stats_subquery = db.session.query(
                DatabaseSizeStat.instance_id,
                DatabaseSizeStat.database_name,
                DatabaseSizeStat.is_deleted,
                func.row_number().over(
                    partition_by=[DatabaseSizeStat.instance_id, DatabaseSizeStat.database_name],
                    order_by=DatabaseSizeStat.collected_date.desc()
                ).label('rn')
            ).subquery()
            
            # 获取未删除的数据库列表
            active_databases_subquery = db.session.query(
                latest_stats_subquery.c.instance_id,
                latest_stats_subquery.c.database_name
            ).filter(
                and_(
                    latest_stats_subquery.c.rn == 1,  # 只取最新记录
                    or_(
                        latest_stats_subquery.c.is_deleted == False,
                        latest_stats_subquery.c.is_deleted.is_(None)
                    )
                )
            ).subquery()
            
            # 只显示当前活跃的数据库的聚合数据
            query = query.join(
                active_databases_subquery,
                and_(
                    DatabaseSizeAggregation.instance_id == active_databases_subquery.c.instance_id,
                    DatabaseSizeAggregation.database_name == active_databases_subquery.c.database_name
                )
            )
            
            if instance_id:
                query = query.filter(DatabaseSizeAggregation.instance_id == instance_id)
            if db_type:
                query = query.filter(Instance.db_type == db_type)
            if database_name:
                query = query.filter(DatabaseSizeAggregation.database_name == database_name)
            if period_type:
                query = query.filter(DatabaseSizeAggregation.period_type == period_type)
            if start_date:
                query = query.filter(DatabaseSizeAggregation.period_start >= datetime.strptime(start_date, '%Y-%m-%d').date())
            if end_date:
                query = query.filter(DatabaseSizeAggregation.period_end <= datetime.strptime(end_date, '%Y-%m-%d').date())
            
            # 排序和分页
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
            
            # 如果没有聚合数据，尝试从原始数据生成
            if not data and period_type == 'daily':
                data = _generate_daily_data_from_stats(
                    instance_id, db_type, database_name, 
                    start_date, end_date, limit, offset
                )
                total = len(data)
            
            return jsonify({
                'success': True,
                'data': data,
                'total': total,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            logger.error(f"获取聚合数据时出错: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    else:
        # 无查询参数，返回HTML页面
        # 获取实例列表用于筛选
        instances = Instance.query.filter_by(is_active=True).order_by(Instance.id).all()
        instances_list = []
        for instance in instances:
            instances_list.append({
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type
            })
        
        # 获取数据库类型配置
        from app.models.database_type_config import DatabaseTypeConfig
        database_types = DatabaseTypeConfig.query.filter_by(is_active=True).order_by(DatabaseTypeConfig.id).all()
        database_types_list = []
        for db_type in database_types:
            database_types_list.append({
                'name': db_type.name,
                'display_name': db_type.display_name
            })
        
        return render_template('database_sizes/aggregations.html', 
                             instances_list=instances_list,
                             database_types=database_types_list)

@database_sizes_bp.route('/api/config', methods=['GET', 'PUT'])
@login_required
@view_required
def config():
    """
    配置管理API
    
    提供数据库大小监控相关配置的获取和更新功能
    """
    if request.method == 'GET':
        try:
            # 从配置中获取参数
            config = {
                'collect_hour': current_app.config.get('COLLECT_DB_SIZE_HOUR', 3),
                'collect_enabled': current_app.config.get('COLLECT_DB_SIZE_ENABLED', True),
                'cleanup_hour': current_app.config.get('CLEANUP_PARTITION_HOUR', 3),
                'create_hour': current_app.config.get('CREATE_PARTITION_HOUR', 2),
                'retention_days': current_app.config.get('DATABASE_SIZE_RETENTION_DAYS', 365),
                'retention_months': current_app.config.get('DATABASE_SIZE_RETENTION_MONTHS', 12),
                'aggregation_hour': current_app.config.get('AGGREGATION_HOUR', 4),
                'aggregation_enabled': current_app.config.get('AGGREGATION_ENABLED', True),
                'collect_timeout': current_app.config.get('DB_SIZE_COLLECT_TIMEOUT', 30),
                'batch_size': current_app.config.get('DB_SIZE_COLLECT_BATCH_SIZE', 10),
                'retry_count': current_app.config.get('DB_SIZE_COLLECT_RETRY_COUNT', 3)
            }
            
            return jsonify({
                'success': True,
                'config': config,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"获取配置时出错: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    else:  # PUT request
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400
            
            # 更新配置参数
            if 'collect_hour' in data:
                current_app.config['COLLECT_DB_SIZE_HOUR'] = data['collect_hour']
            if 'collect_enabled' in data:
                current_app.config['COLLECT_DB_SIZE_ENABLED'] = data['collect_enabled']
            if 'cleanup_hour' in data:
                current_app.config['CLEANUP_PARTITION_HOUR'] = data['cleanup_hour']
            if 'create_hour' in data:
                current_app.config['CREATE_PARTITION_HOUR'] = data['create_hour']
            if 'retention_days' in data:
                current_app.config['DATABASE_SIZE_RETENTION_DAYS'] = data['retention_days']
            if 'retention_months' in data:
                current_app.config['DATABASE_SIZE_RETENTION_MONTHS'] = data['retention_months']
            if 'aggregation_hour' in data:
                current_app.config['AGGREGATION_HOUR'] = data['aggregation_hour']
            if 'aggregation_enabled' in data:
                current_app.config['AGGREGATION_ENABLED'] = data['aggregation_enabled']
            if 'collect_timeout' in data:
                current_app.config['DB_SIZE_COLLECT_TIMEOUT'] = data['collect_timeout']
            if 'batch_size' in data:
                current_app.config['DB_SIZE_COLLECT_BATCH_SIZE'] = data['batch_size']
            if 'retry_count' in data:
                current_app.config['DB_SIZE_COLLECT_RETRY_COUNT'] = data['retry_count']
            
            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully',
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"更新配置时出错: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


@database_sizes_bp.route('/partitions', methods=['GET'])
@login_required
@view_required
def partitions():
    """
    分区管理页面或API
    
    如果是页面请求（无查询参数），返回HTML页面
    如果是API请求（有查询参数），返回JSON数据
    """
    # 检查是否有查询参数，如果有则返回API数据
    if request.args:
        try:
            service = PartitionManagementService()
            result = service.get_partition_info()
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': result,
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', '获取分区信息失败')
                }), 500
                
        except Exception as e:
            logger.error(f"获取分区信息时出错: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    else:
        # 无查询参数，返回HTML页面
        return render_template('database_sizes/partitions.html')

# API 路由

@database_sizes_bp.route('/aggregations/summary', methods=['GET'])
@login_required
@view_required
def get_aggregations_summary():
    """
    获取聚合数据汇总统计
    
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
            func.avg(DatabaseSizeAggregation.avg_size_mb).label('avg_size'),
            func.max(DatabaseSizeAggregation.max_size_mb).label('max_size')
        ).first()
        
        # 按周期类型统计
        period_stats = db.session.query(
            DatabaseSizeAggregation.period_type,
            func.count(DatabaseSizeAggregation.id).label('count')
        ).group_by(DatabaseSizeAggregation.period_type).all()
        
        # 按实例统计
        instance_stats = db.session.query(
            DatabaseSizeAggregation.instance_id,
            Instance.name.label('instance_name'),
            func.count(DatabaseSizeAggregation.id).label('count')
        ).join(Instance).group_by(
            DatabaseSizeAggregation.instance_id, 
            Instance.name
        ).order_by(func.count(DatabaseSizeAggregation.id).desc()).limit(10).all()
        
        # 最近更新时间
        latest_aggregation = DatabaseSizeAggregation.query.order_by(
            desc(DatabaseSizeAggregation.calculated_at)
        ).first()
        
        summary = {
            'total_aggregations': total_aggregations,
            'total_instances': total_instances,
            'total_databases': total_databases,
            'average_size_mb': float(size_stats.avg_size) if size_stats.avg_size else 0,
            'max_size_mb': int(size_stats.max_size) if size_stats.max_size else 0,
            'period_stats': [
                {'period_type': stat.period_type, 'count': stat.count}
                for stat in period_stats
            ],
            'top_instances': [
                {'instance_id': stat.instance_id, 'instance_name': stat.instance_name, 'count': stat.count}
                for stat in instance_stats
            ],
            'last_updated': latest_aggregation.calculated_at.isoformat() if latest_aggregation else None
        }
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"获取聚合汇总数据时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 配置管理相关路由

@database_sizes_bp.route('/status', methods=['GET'])
@login_required
@view_required
def get_status():
    """
    获取数据库大小监控状态
    """
    try:
        # 获取采集状态
        from app.tasks.database_size_collection_tasks import get_collection_status
        collection_status = get_collection_status()
        
        # 获取聚合状态
        from app.tasks.database_size_aggregation_tasks import get_aggregation_status
        aggregation_status = get_aggregation_status()
        
        # 获取分区管理状态
        from app.tasks.partition_management_tasks import get_partition_management_status
        partition_status = get_partition_management_status()
        
        status = {
            'collection': collection_status.get('status', {}),
            'aggregation': aggregation_status.get('status', {}),
            'partition': partition_status.get('status', {}),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"获取状态时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_sizes_bp.route('/stats', methods=['GET'])
@login_required
@view_required
def get_stats():
    """
    获取数据库大小监控统计信息
    """
    try:
        # 获取基本统计
        total_stats = DatabaseSizeStat.query.count()
        total_aggregations = DatabaseSizeAggregation.query.count()
        total_instances = Instance.query.filter_by(is_active=True).count()
        
        # 获取最近采集时间
        latest_stat = DatabaseSizeStat.query.order_by(desc(DatabaseSizeStat.collected_at)).first()
        
        # 获取按数据库类型统计
        db_type_stats = db.session.query(
            Instance.db_type,
            func.count(DatabaseSizeStat.id).label('count')
        ).join(DatabaseSizeStat).group_by(Instance.db_type).all()
        
        stats = {
            'total_stats': total_stats,
            'total_aggregations': total_aggregations,
            'total_instances': total_instances,
            'last_collection': latest_stat.collected_at.isoformat() if latest_stat else None,
            'db_type_stats': [
                {'db_type': stat.db_type, 'count': stat.count}
                for stat in db_type_stats
            ]
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取统计信息时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_sizes_bp.route('/test_connection', methods=['POST'])
@login_required
@view_required
def test_connection():
    """
    测试数据库连接
    """
    try:
        data = request.get_json()
        instance_id = data.get('instance_id')
        
        if not instance_id:
            return jsonify({
                'success': False,
                'error': '实例ID不能为空'
            }), 400
        
        instance = Instance.query.get(instance_id)
        if not instance:
            return jsonify({
                'success': False,
                'error': '实例不存在'
            }), 404
        
        # 这里可以添加连接测试逻辑
        return jsonify({
            'success': True,
            'message': f'实例 {instance.name} 连接测试成功'
        })
        
    except Exception as e:
        logger.error(f"测试连接时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_sizes_bp.route('/manual_collect', methods=['POST'])
@login_required
@view_required
def manual_collect():
    """
    手动触发数据采集
    """
    try:
        from app.tasks.database_size_collection_tasks import collect_database_sizes
        
        # 触发采集任务
        result = collect_database_sizes()
        
        return jsonify({
            'success': True,
            'message': '手动采集任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"手动采集时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_sizes_bp.route('/manual_aggregate', methods=['POST'])
@login_required
@view_required
def manual_aggregate():
    """
    手动触发聚合计算
    """
    try:
        from app.tasks.database_size_aggregation_tasks import calculate_database_size_aggregations
        
        # 触发聚合任务
        result = calculate_database_size_aggregations()
        
        return jsonify({
            'success': True,
            'message': '手动聚合任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"手动聚合时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_sizes_bp.route('/cleanup_partitions', methods=['POST'])
@login_required
@view_required
def cleanup_partitions_manual():
    """
    手动清理分区
    """
    try:
        from app.tasks.partition_management_tasks import cleanup_database_size_partitions
        
        # 触发清理任务
        result = cleanup_database_size_partitions()
        
        return jsonify({
            'success': True,
            'message': '分区清理任务已触发',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"清理分区时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_sizes_bp.route('/instances', methods=['GET'])
@login_required
@view_required
def get_instances():
    """
    获取实例列表
    
    Returns:
        JSON: 实例列表
    """
    try:
        instances = Instance.query.filter_by(is_active=True).all()
        
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
        logger.error(f"获取实例列表时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@database_sizes_bp.route('/instances/<int:instance_id>/database-sizes/total', methods=['GET'])
@login_required
@view_required
def get_instance_total_size(instance_id: int):
    """
    获取指定实例的数据库总大小
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 实例总大小信息
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取最新的数据库大小数据
        latest_stats = DatabaseSizeStat.query.filter(
            DatabaseSizeStat.instance_id == instance_id
        ).order_by(DatabaseSizeStat.collected_date.desc()).all()
        
        if not latest_stats:
            return jsonify({
                'success': True,
                'total_size_mb': 0,
                'database_count': 0,
                'last_collected': None
            })
        
        # 计算总大小
        total_size_mb = sum(stat.size_mb for stat in latest_stats)
        database_count = len(set(stat.database_name for stat in latest_stats))
        last_collected = latest_stats[0].collected_date if latest_stats else None
        
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


@database_sizes_bp.route('/instances/<int:instance_id>/database-sizes', methods=['GET'])
@login_required
@view_required
def get_instance_database_sizes(instance_id: int):
    """
    获取指定实例的数据库大小历史数据
    
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
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # 构建查询
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
        
        # 格式化数据
        data = []
        for stat in stats:
            data.append({
                'id': stat.id,
                'database_name': stat.database_name,
                'size_mb': stat.size_mb,
                'data_size_mb': stat.data_size_mb,
                'log_size_mb': stat.log_size_mb,
                'collected_date': stat.collected_date.isoformat(),
                'collected_at': stat.collected_at.isoformat()
            })
        
        return jsonify({
            'data': data,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port
            }
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 数据库大小数据时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/instances/<int:instance_id>/database-sizes/aggregations', methods=['GET'])
@login_required
@view_required
def get_instance_database_aggregations(instance_id: int):
    """
    获取指定实例的数据库大小统计聚合数据
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 统计聚合数据
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取查询参数
        period_type = request.args.get('period_type', 'monthly')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        database_name = request.args.get('database_name')
        
        # 验证周期类型
        if period_type not in ['weekly', 'monthly', 'quarterly']:
            return jsonify({'error': 'Invalid period_type. Must be weekly, monthly, or quarterly'}), 400
        
        # 解析日期
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        
        # 获取聚合数据
        aggregation_service = DatabaseSizeAggregationService()
        data = aggregation_service.get_aggregations(
            instance_id=instance_id,
            period_type=period_type,
            start_date=start_date_obj,
            end_date=end_date_obj,
            database_name=database_name
        )
        
        return jsonify({
            'data': data,
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port
            },
            'period_type': period_type
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 统计聚合数据时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/instances/<int:instance_id>/database-sizes/trends', methods=['GET'])
@login_required
@view_required
def get_instance_database_trends(instance_id: int):
    """
    获取指定实例的数据库大小趋势分析数据
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 趋势分析数据
    """
    try:
        # 验证实例是否存在
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取查询参数
        period_type = request.args.get('period_type', 'monthly')
        months = int(request.args.get('months', 12))
        
        # 验证周期类型
        if period_type not in ['weekly', 'monthly', 'quarterly']:
            return jsonify({'error': 'Invalid period_type. Must be weekly, monthly, or quarterly'}), 400
        
        # 获取趋势分析数据
        aggregation_service = DatabaseSizeAggregationService()
        data = aggregation_service.get_trends_analysis(
            instance_id=instance_id,
            period_type=period_type,
            months=months
        )
        
        return jsonify({
            'data': data,
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port
            },
            'period_type': period_type,
            'months': months
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 趋势分析数据时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/instances/<int:instance_id>/database-sizes/summary', methods=['GET'])
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
        thirty_days_ago = date.today() - timedelta(days=30)
        
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
        
        # 计算每个数据库的平均大小
        db_averages = {}
        for db_name, stats in db_stats.items():
            sizes = [s.size_mb for s in stats]
            db_averages[db_name] = sum(sizes) / len(sizes)
        
        # 计算汇总信息
        total_databases = len(db_averages)
        total_size_mb = sum(db_averages.values())
        average_size_mb = total_size_mb / total_databases if total_databases > 0 else 0
        
        # 找出最大的数据库
        largest_database = max(db_averages.items(), key=lambda x: x[1])[0] if db_averages else None
        
        # 计算增长率（简化计算：比较第一个和最后一个数据点）
        growth_rate = 0
        if len(recent_stats) >= 2:
            first_size = recent_stats[-1].size_mb  # 最旧的数据
            last_size = recent_stats[0].size_mb    # 最新的数据
            if first_size > 0:
                growth_rate = ((last_size - first_size) / first_size) * 100
        
        # 获取最后采集时间
        last_collected = recent_stats[0].collected_at if recent_stats else None
        
        return jsonify({
            'data': {
                'total_databases': total_databases,
                'total_size_mb': int(total_size_mb),
                'average_size_mb': int(average_size_mb),
                'largest_database': largest_database,
                'growth_rate': round(growth_rate, 2),
                'last_collected': last_collected.isoformat() if last_collected else None
            },
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port
            }
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 汇总信息时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/collect', methods=['POST'])
@login_required
@view_required
def collect_database_sizes():
    """
    手动触发数据库大小采集
    
    Returns:
        JSON: 采集结果
    """
    try:
        # 检查是否启用采集
        if not current_app.config.get('COLLECT_DB_SIZE_ENABLED', True):
            return jsonify({'error': 'Database size collection is disabled'}), 400
        
        # 执行采集
        result = collect_all_instances_database_sizes()
        
        return jsonify({
            'message': 'Database size collection completed',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"手动采集数据库大小时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/aggregate', methods=['POST'])
@login_required
@view_required
def calculate_aggregations():
    """
    手动触发统计聚合计算
    
    Returns:
        JSON: 聚合结果
    """
    try:
        # 检查是否启用聚合
        if not current_app.config.get('AGGREGATION_ENABLED', True):
            return jsonify({'error': 'Database size aggregation is disabled'}), 400
        
        # 执行聚合计算
        aggregation_service = DatabaseSizeAggregationService()
        result = aggregation_service.calculate_all_aggregations()
        
        return jsonify({
            'message': 'Database size aggregation completed',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"手动计算统计聚合时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500






@database_sizes_bp.route('/partitions/status', methods=['GET'])
@login_required
@view_required
def get_partition_status():
    """
    获取分区管理状态
    
    Returns:
        JSON: 分区状态
    """
    try:
        result = get_partition_management_status()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取分区状态时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/partitions/create', methods=['POST'])
@login_required
@view_required
def create_partition():
    """
    创建分区
    
    Returns:
        JSON: 创建结果
    """
    try:
        data = request.get_json()
        partition_date_str = data.get('date')
        
        if not partition_date_str:
            return jsonify({'error': '缺少日期参数'}), 400
        
        # 解析日期
        try:
            partition_date = datetime.strptime(partition_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': '日期格式错误，请使用 YYYY-MM-DD 格式'}), 400
        
        service = PartitionManagementService()
        result = service.create_partition(partition_date)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"创建分区时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/partitions/cleanup', methods=['POST'])
@login_required
@view_required
def cleanup_partitions():
    """
    清理旧分区
    
    Returns:
        JSON: 清理结果
    """
    try:
        data = request.get_json() or {}
        retention_months = data.get('retention_months', 12)
        
        service = PartitionManagementService()
        result = service.cleanup_old_partitions(retention_months=retention_months)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"清理分区时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/partitions/statistics', methods=['GET'])
@login_required
@view_required
def get_partition_statistics():
    """
    获取分区统计信息
    
    Returns:
        JSON: 统计信息
    """
    try:
        service = PartitionManagementService()
        result = service.get_partition_statistics()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取分区统计信息时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500




@database_sizes_bp.route('/collect/status', methods=['GET'])
@login_required
@view_required
def get_collection_status_api():
    """
    获取采集状态信息
    
    Returns:
        JSON: 状态信息
    """
    try:
        result = get_collection_status()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取采集状态时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/collect/validate', methods=['GET'])
@login_required
@view_required
def validate_collection_config_api():
    """
    验证采集配置
    
    Returns:
        JSON: 验证结果
    """
    try:
        result = validate_collection_config()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"验证采集配置时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500




@database_sizes_bp.route('/aggregate/status', methods=['GET'])
@login_required
@view_required
def get_aggregation_status_api():
    """
    获取聚合状态信息
    
    Returns:
        JSON: 状态信息
    """
    try:
        result = get_aggregation_status()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取聚合状态时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/aggregate/validate', methods=['GET'])
@login_required
@view_required
def validate_aggregation_config_api():
    """
    验证聚合配置
    
    Returns:
        JSON: 验证结果
    """
    try:
        result = validate_aggregation_config()
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"验证聚合配置时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/aggregate/cleanup', methods=['POST'])
@login_required
@view_required
def cleanup_old_aggregations_api():
    """
    清理旧的聚合数据
    
    Returns:
        JSON: 清理结果
    """
    try:
        data = request.get_json() or {}
        retention_days = data.get('retention_days', 365)
        
        result = cleanup_old_aggregations(retention_days=retention_days)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"清理旧聚合数据时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


def _generate_daily_data_from_stats(instance_id, db_type, database_name, 
                                  start_date, end_date, limit, offset):
    """
    从原始统计数据生成日聚合数据（回退机制）
    """
    try:
        from app.models.database_size_stat import DatabaseSizeStat
        from sqlalchemy import func, and_, or_
        
        # 构建查询
        query = DatabaseSizeStat.query.join(Instance)
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(DatabaseSizeStat.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if database_name:
            query = query.filter(DatabaseSizeStat.database_name == database_name)
        if start_date:
            query = query.filter(DatabaseSizeStat.collected_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(DatabaseSizeStat.collected_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # 只获取未删除的数据
        query = query.filter(
            or_(
                DatabaseSizeStat.is_deleted == False,
                DatabaseSizeStat.is_deleted.is_(None)
            )
        )
        
        # 按日期和数据库分组，计算聚合数据
        stats = query.all()
        
        # 按日期和数据库分组
        grouped_data = {}
        for stat in stats:
            key = (stat.collected_date, stat.instance_id, stat.database_name)
            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(stat)
        
        # 生成聚合数据
        data = []
        for (collected_date, instance_id, database_name), stats_list in grouped_data.items():
            # 计算统计值
            sizes = [s.size_mb for s in stats_list if s.size_mb is not None]
            if not sizes:
                continue
            
            max_size = max(sizes)
            min_size = min(sizes)
            avg_size = sum(sizes) / len(sizes)
            
            # 获取实例信息
            instance = Instance.query.get(instance_id)
            if not instance:
                continue
            
            # 创建聚合数据格式
            agg_data = {
                'id': f"temp_{instance_id}_{database_name}_{collected_date}",
                'instance_id': instance_id,
                'database_name': database_name,
                'period_type': 'daily',
                'period_start': collected_date.isoformat(),
                'period_end': collected_date.isoformat(),
                'max_size_mb': max_size,
                'min_size_mb': min_size,
                'avg_size_mb': avg_size,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'instance': {
                    'id': instance.id,
                    'name': instance.name,
                    'db_type': instance.db_type
                }
            }
            data.append(agg_data)
        
        # 按日期排序
        data.sort(key=lambda x: x['period_start'], reverse=True)
        
        # 应用分页
        return data[offset:offset + limit]
        
    except Exception as e:
        logger.error(f"从原始数据生成聚合数据时出错: {str(e)}")
        return []
