"""
存储同步 API 路由
提供数据库大小监控、历史数据、统计聚合、趋势分析等接口
"""

import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import login_required, current_user
from sqlalchemy import and_, desc, func
from app.models.instance import Instance
from app.models.database_size_stat import DatabaseSizeStat
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




# API 路由


# 配置管理相关路由

@storage_sync_bp.route('/status', methods=['GET'])
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

@storage_sync_bp.route('/stats', methods=['GET'])
@login_required
@view_required
def get_stats():
    """
    获取数据库大小监控统计信息
    """
    try:
        # 获取基本统计
        total_stats = DatabaseSizeStat.query.count()
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

@storage_sync_bp.route('/test_connection', methods=['POST'])
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

@storage_sync_bp.route('/manual_collect', methods=['POST'])
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


@storage_sync_bp.route('/cleanup_partitions', methods=['POST'])
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

@storage_sync_bp.route('/instances', methods=['GET'])
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

@storage_sync_bp.route('/instances/<int:instance_id>/database-sizes/total', methods=['GET'])
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


@storage_sync_bp.route('/instances/<int:instance_id>/database-sizes', methods=['GET'])
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
                    'collected_at': stat.collected_at.isoformat()
                })
        else:
            # 查询所有数据（非latest_only模式）
            query = DatabaseSizeStat.query.filter(
                DatabaseSizeStat.instance_id == instance_id
            )
            
            # 应用数据库名称筛选
            if database_name:
                query = query.filter(DatabaseSizeStat.database_name.ilike(f'%{database_name}%'))
            
            # 应用日期筛选条件
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
                    'collected_at': stat.collected_at.isoformat()
                })
        
        # 从 instance_size_stats 表获取总容量信息
        from app.models.instance_size_stat import InstanceSizeStat
        latest_instance_stat = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.is_deleted == False
        ).order_by(InstanceSizeStat.collected_date.desc()).first()
        
        # 只从 instance_size_stats 表获取总容量信息
        if latest_instance_stat:
            total_size_mb = latest_instance_stat.total_size_mb
            database_count = latest_instance_stat.database_count
        else:
            # 如果没有实例统计数据，返回0
            total_size_mb = 0
            database_count = 0
        
        return jsonify({
            'data': data,
            'pagination': {
                'total': len(data),  # 使用实际数据长度
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < len(data)
            },
            'instance': {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'host': instance.host,
                'port': instance.port
            },
            'total_size_mb': total_size_mb,
            'database_count': database_count
        })
        
    except Exception as e:
        logger.error(f"获取实例 {instance_id} 数据库大小数据时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500




@storage_sync_bp.route('/instances/<int:instance_id>/database-sizes/summary', methods=['GET'])
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


@storage_sync_bp.route('/collect', methods=['POST'])
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








# 实例容量管理相关API
@storage_sync_bp.route("/instances/<int:instance_id>/sync-capacity", methods=['POST'])
@login_required
@view_required
def sync_instance_capacity(instance_id: int):
    """
    同步指定实例的数据库容量信息（包含数据库列表和大小信息）
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 同步结果
    """
    try:
        # 获取实例信息
        instance = Instance.query.get_or_404(instance_id)
        
        if not instance.is_active:
            logger.error(f"实例 {instance.name} 已禁用，无法同步容量信息")
            return jsonify({
                'success': False, 
                'error': '实例已禁用，无法同步容量信息'
            }), 400
        
        # 检查实例是否有凭据
        if not instance.credential:
            logger.error(f"实例 {instance.name} 缺少连接凭据，无法同步容量信息")
            return jsonify({
                'success': False, 
                'error': '实例缺少连接凭据，无法同步容量信息'
            }), 400
        
        logger.info(f"开始同步实例容量信息: {instance.name}")
        
        # 建立数据库连接（两个服务共享同一个连接）
        from app.services.connection_factory import ConnectionFactory
        
        db_connection = ConnectionFactory.create_connection(instance)
        
        if not db_connection.connect():
            error_msg = f"无法连接到实例 {instance.name} (类型: {instance.db_type})"
            logger.error(error_msg)
            return jsonify({
                'success': False, 
                'error': error_msg
            }), 400
        
        try:
            # 第一步：同步数据库列表
            from app.services.database_discovery_service import DatabaseDiscoveryService
            
            discovery_service = DatabaseDiscoveryService(instance)
            discovery_service.db_connection = db_connection  # 共享连接
            
            # 发现数据库列表
            databases = discovery_service.discover_databases()
            
            # 更新数据库列表
            databases_result = discovery_service.update_database_list(databases)
            
            logger.info(f"数据库列表同步完成: {databases_result}")
            
            # 第二步：同步数据库大小
            from app.services.database_size_collector_service import DatabaseSizeCollectorService
            
            collector = DatabaseSizeCollectorService(instance)
            collector.db_connection = db_connection  # 共享连接
            
            # 采集并保存数据库大小数据，同时保存实例大小统计
            saved_count = collector.collect_and_save()
            
            # 更新实例的最后连接时间
            instance.last_connected = datetime.utcnow()
            db.session.commit()
            
            # 获取最新的实例统计信息
            from app.models.instance_size_stat import InstanceSizeStat
            latest_stat = InstanceSizeStat.query.filter(
                InstanceSizeStat.instance_id == instance_id,
                InstanceSizeStat.is_deleted == False
            ).order_by(InstanceSizeStat.collected_date.desc()).first()
            
            total_size_mb = latest_stat.total_size_mb if latest_stat else 0
            database_count = latest_stat.database_count if latest_stat else 0
            
            logger.info(f"数据库大小同步完成: 保存数量 {saved_count}, 总大小 {total_size_mb}MB")
            
        finally:
            # 确保断开连接
            db_connection.disconnect()
        
        # 返回综合结果
        logger.info(f"实例容量同步完成: {instance.name}, 数据库数量: {database_count}, 保存数量: {saved_count}, 总大小: {total_size_mb}MB")
        
        return jsonify({
            'success': True,
            'message': f'成功同步容量信息，发现 {databases_result["databases_found"]} 个数据库，保存 {saved_count} 条大小记录',
            'data': {
                'instance_id': instance_id,
                'instance_name': instance.name,
                'databases_found': databases_result['databases_found'],
                'databases_added': databases_result['databases_added'],
                'databases_deleted': databases_result['databases_deleted'],
                'databases_updated': databases_result['databases_updated'],
                'databases_count': database_count,
                'saved_count': saved_count,
                'total_size_mb': total_size_mb
            }
        })
            
    except Exception as e:
        logger.error(f"同步实例容量失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'同步容量信息失败: {str(e)}'
        }), 500


@storage_sync_bp.route("/instances/<int:instance_id>/databases", methods=['GET'])
@login_required
@view_required
def get_instance_databases(instance_id: int):
    """
    获取指定实例的数据库列表
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON响应，包含数据库列表
    """
    try:
        # 获取实例信息
        instance = Instance.query.get_or_404(instance_id)
        
        # 获取该实例的所有数据库名称（从数据库大小统计中获取）
        from sqlalchemy import distinct
        
        # 获取所有不重复的数据库名称
        database_names = db.session.query(
            distinct(DatabaseSizeStat.database_name)
        ).filter_by(
            instance_id=instance_id
        ).filter(
            DatabaseSizeStat.is_deleted == False
        ).order_by(
            DatabaseSizeStat.database_name
        ).all()
        
        # 转换为列表格式
        databases = []
        for (db_name,) in database_names:
            databases.append({
                'name': db_name,
                'instance_id': instance_id,
                'instance_name': instance.name
            })
        
        return jsonify({
            'success': True,
            'databases': databases,
            'count': len(databases)
        })
        
    except Exception as e:
        logger.error(f"获取实例数据库列表失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'获取数据库列表失败: {str(e)}'
        }), 500


