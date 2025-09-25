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
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
database_sizes_bp = Blueprint('database_sizes', __name__, url_prefix='/api/v1')

# 页面路由
@database_sizes_bp.route('/database-sizes/aggregations', methods=['GET'])
@login_required
@view_required
def aggregations():
    """统计聚合页面"""
    return render_template('database_sizes/aggregations.html')

@database_sizes_bp.route('/database-sizes/config', methods=['GET'])
@login_required
@view_required
def config():
    """配置管理页面"""
    return render_template('database_sizes/config.html')


@database_sizes_bp.route('/database-sizes/partitions', methods=['GET'])
@login_required
@view_required
def partitions():
    """分区管理页面"""
    return render_template('database_sizes/partitions.html')

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


@database_sizes_bp.route('/database-sizes/collect', methods=['POST'])
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


@database_sizes_bp.route('/database-sizes/aggregate', methods=['POST'])
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


@database_sizes_bp.route('/database-sizes/config', methods=['GET'])
@login_required
@view_required
def get_database_size_config():
    """
    获取数据库大小监控配置信息
    
    Returns:
        JSON: 配置信息
    """
    try:
        config = {
            'collect_enabled': current_app.config.get('COLLECT_DB_SIZE_ENABLED', True),
            'collect_hour': current_app.config.get('COLLECT_DB_SIZE_HOUR', '3'),
            'collect_timeout': current_app.config.get('COLLECT_DB_SIZE_TIMEOUT', 300),
            'aggregation_enabled': current_app.config.get('AGGREGATION_ENABLED', True),
            'aggregation_hour': current_app.config.get('AGGREGATION_HOUR', '5'),
            'partition_cleanup_enabled': current_app.config.get('PARTITION_CLEANUP_ENABLED', True),
            'partition_cleanup_hour': current_app.config.get('PARTITION_CLEANUP_HOUR', '4'),
            'partition_create_hour': current_app.config.get('PARTITION_CREATE_HOUR', '2'),
            'retention_days': current_app.config.get('DATABASE_SIZE_RETENTION_DAYS', 365),
            'retention_months': current_app.config.get('DATABASE_SIZE_RETENTION_MONTHS', 12),
            'collect_timeout': current_app.config.get('DB_SIZE_COLLECT_TIMEOUT', 30),
            'batch_size': current_app.config.get('DB_SIZE_COLLECT_BATCH_SIZE', 10),
            'retry_count': current_app.config.get('DB_SIZE_COLLECT_RETRY_COUNT', 3)
        }
        
        return jsonify({
            'config': config,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取数据库大小监控配置时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/database-sizes/partitions', methods=['GET'])
@login_required
@view_required
def get_partition_info():
    """
    获取分区信息
    
    Returns:
        JSON: 分区信息
    """
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
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取分区信息时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/database-sizes/partitions/status', methods=['GET'])
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


@database_sizes_bp.route('/database-sizes/partitions/create', methods=['POST'])
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


@database_sizes_bp.route('/database-sizes/partitions/cleanup', methods=['POST'])
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


@database_sizes_bp.route('/database-sizes/partitions/statistics', methods=['GET'])
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


@database_sizes_bp.route('/database-sizes/collect', methods=['POST'])
@login_required
@view_required
def trigger_collection():
    """
    手动触发数据库大小采集
    
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
            # 采集指定类型的数据库
            result = collect_database_sizes_by_type(db_type)
        else:
            # 采集所有实例
            result = collect_database_sizes()
        
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
        logger.error(f"触发数据库大小采集时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@database_sizes_bp.route('/database-sizes/collect/status', methods=['GET'])
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


@database_sizes_bp.route('/database-sizes/collect/validate', methods=['GET'])
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
