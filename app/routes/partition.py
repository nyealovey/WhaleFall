"""
分区管理 API 路由
提供数据库表分区创建、清理、统计等功能
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func, desc, text
from app.services.partition_management_service import PartitionManagementService
from app.tasks.partition_management_tasks import get_partition_management_status
from app.tasks.database_size_aggregation_tasks import cleanup_old_aggregations
from app.models.instance import Instance
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.utils.decorators import view_required
from app import db

logger = logging.getLogger(__name__)

# 创建蓝图
partition_bp = Blueprint('partition', __name__)

# 页面路由
@partition_bp.route('/', methods=['GET'])
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
            logger.info("开始获取分区信息")
            service = PartitionManagementService()
            result = service.get_partition_info()
            logger.info(f"分区信息获取结果: {result}")
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': result,
                    'timestamp': datetime.utcnow().isoformat()
                })
            else:
                logger.error(f"分区信息获取失败: {result}")
                return jsonify({
                    'success': False,
                    'error': result.get('message', '获取分区信息失败'),
                    'details': result
                }), 500
                
        except Exception as e:
            logger.error(f"获取分区信息时出错: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'获取分区信息失败: {str(e)}',
                'message': '系统内部错误'
            }), 500
    else:
        # 无查询参数，返回HTML页面
        return render_template('database_sizes/partitions.html')

# API 路由

@partition_bp.route('/status', methods=['GET'])
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


@partition_bp.route('/test', methods=['GET'])
@login_required
@view_required
def test_partition_service():
    """
    测试分区管理服务（调试用）
    
    Returns:
        JSON: 测试结果
    """
    try:
        logger.info("开始测试分区管理服务")
        
        # 测试数据库连接
        try:
            db.session.execute(text("SELECT 1"))
            logger.info("数据库连接正常")
        except Exception as db_error:
            logger.error(f"数据库连接失败: {str(db_error)}")
            return jsonify({
                'success': False,
                'error': f'数据库连接失败: {str(db_error)}'
            }), 500
        
        # 测试分区管理服务
        service = PartitionManagementService()
        result = service.get_partition_info()
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"测试分区管理服务时出错: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'测试失败: {str(e)}'
        }), 500


@partition_bp.route('/create', methods=['POST'])
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
            from datetime import datetime
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


@partition_bp.route('/cleanup', methods=['POST'])
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


@partition_bp.route('/statistics', methods=['GET'])
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


@partition_bp.route('/create-future', methods=['POST'])
@login_required
@view_required
def create_future_partitions():
    """
    创建未来分区
    
    Returns:
        JSON: 创建结果
    """
    try:
        data = request.get_json() or {}
        months_ahead = data.get('months_ahead', 3)
        
        service = PartitionManagementService()
        result = service.create_future_partitions(months_ahead=months_ahead)
        
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
        logger.error(f"创建未来分区时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@partition_bp.route('/aggregations/latest', methods=['GET'])
@login_required
@view_required
def get_latest_aggregations():
    """
    获取最新的日、周、月、季度聚合数据（用于快速检查异常）
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        database_name = request.args.get('database_name')
        
        # 构建查询
        query = DatabaseSizeAggregation.query.join(Instance)
        
        # 过滤掉已删除的数据库
        latest_stats_subquery = db.session.query(
            DatabaseSizeStat.instance_id,
            DatabaseSizeStat.database_name,
            DatabaseSizeStat.is_deleted,
            func.row_number().over(
                partition_by=[DatabaseSizeStat.instance_id, DatabaseSizeStat.database_name],
                order_by=DatabaseSizeStat.collected_date.desc()
            ).label('rn')
        ).subquery()
        
        active_databases_subquery = db.session.query(
            latest_stats_subquery.c.instance_id,
            latest_stats_subquery.c.database_name
        ).filter(
            and_(
                latest_stats_subquery.c.rn == 1,
                or_(
                    latest_stats_subquery.c.is_deleted == False,
                    latest_stats_subquery.c.is_deleted.is_(None)
                )
            )
        ).subquery()
        
        query = query.join(
            active_databases_subquery,
            and_(
                DatabaseSizeAggregation.instance_id == active_databases_subquery.c.instance_id,
                DatabaseSizeAggregation.database_name == active_databases_subquery.c.database_name
            )
        )
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(DatabaseSizeAggregation.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if database_name:
            query = query.filter(DatabaseSizeAggregation.database_name == database_name)
        
        # 获取每种周期类型的最新数据
        latest_data = {}
        period_types = ['daily', 'weekly', 'monthly', 'quarterly']
        
        for period_type in period_types:
            # 获取该周期类型的最新数据
            period_query = query.filter(DatabaseSizeAggregation.period_type == period_type)
            period_query = period_query.order_by(desc(DatabaseSizeAggregation.period_start))
            
            # 获取每个实例-数据库组合的最新记录
            latest_period_data = {}
            for agg in period_query.all():
                key = f"{agg.instance.name}_{agg.database_name}"
                if key not in latest_period_data:
                    latest_period_data[key] = {
                        'instance': {
                            'id': agg.instance.id,
                            'name': agg.instance.name,
                            'db_type': agg.instance.db_type
                        },
                        'database_name': agg.database_name,
                        'period_type': agg.period_type,
                        'period_start': agg.period_start.isoformat(),
                        'period_end': agg.period_end.isoformat(),
                        'max_size_mb': agg.max_size_mb,
                        'min_size_mb': agg.min_size_mb,
                        'avg_size_mb': agg.avg_size_mb,
                        'data_count': agg.data_count,
                        'calculated_at': agg.calculated_at.isoformat() if agg.calculated_at else None
                    }
            
            latest_data[period_type] = list(latest_period_data.values())
        
        # 计算统计信息
        total_records = sum(len(data) for data in latest_data.values())
        
        return jsonify({
            'success': True,
            'data': latest_data,
            'total_records': total_records,
            'period_types': period_types,
            'summary': {
                'daily': len(latest_data.get('daily', [])),
                'weekly': len(latest_data.get('weekly', [])),
                'monthly': len(latest_data.get('monthly', [])),
                'quarterly': len(latest_data.get('quarterly', []))
            }
        })
        
    except Exception as e:
        logger.error(f"获取最新聚合数据时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@partition_bp.route('/aggregations/cleanup', methods=['POST'])
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
