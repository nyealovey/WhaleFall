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


@partition_bp.route('/api/aggregations/summary', methods=['GET'])
@login_required
@view_required
def get_aggregations_summary():
    """
    获取聚合数据统计概览
    """
    try:
        # 获取每种周期类型的记录数
        daily_count = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.period_type == 'daily'
        ).count()
        
        weekly_count = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.period_type == 'weekly'
        ).count()
        
        monthly_count = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.period_type == 'monthly'
        ).count()
        
        quarterly_count = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.period_type == 'quarterly'
        ).count()
        
        return jsonify({
            'success': True,
            'daily': daily_count,
            'weekly': weekly_count,
            'monthly': monthly_count,
            'quarterly': quarterly_count
        })
        
    except Exception as e:
        logger.error(f"获取聚合数据概览时出错: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@partition_bp.route('/api/aggregations/chart', methods=['GET'])
@login_required
@view_required
def get_aggregations_chart():
    """
    获取聚合数据图表数据
    """
    try:
        from datetime import date, timedelta
        
        # 获取查询参数
        period_type = request.args.get('period_type', 'daily')
        days = request.args.get('days', 7, type=int)
        
        # 验证周期类型
        if period_type not in ['daily', 'weekly', 'monthly', 'quarterly']:
            return jsonify({'error': 'Invalid period_type'}), 400
        
        # 计算日期范围
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # 简化实现：直接查询主表，不使用复杂的UNION查询
        from app.models.database_size_aggregation import DatabaseSizeAggregation
        from app.models.instance_size_aggregation import InstanceSizeAggregation
        from app.models.database_size_stat import DatabaseSizeStat
        from app.models.instance_size_stat import InstanceSizeStat
        
        # 查询数据库聚合数据
        db_aggregations = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.period_type == period_type,
            DatabaseSizeAggregation.period_start >= start_date,
            DatabaseSizeAggregation.period_start <= end_date
        ).join(Instance).all()
        
        # 查询实例聚合数据
        instance_aggregations = InstanceSizeAggregation.query.filter(
            InstanceSizeAggregation.period_type == period_type,
            InstanceSizeAggregation.period_start >= start_date,
            InstanceSizeAggregation.period_start <= end_date
        ).join(Instance).all()
        
        # 查询数据库统计数据（daily类型）
        db_stats = []
        if period_type == 'daily':
            db_stats = DatabaseSizeStat.query.filter(
                DatabaseSizeStat.collected_date >= start_date,
                DatabaseSizeStat.collected_date <= end_date
            ).join(Instance).all()
        
        # 查询实例统计数据（daily类型）
        instance_stats = []
        if period_type == 'daily':
            instance_stats = InstanceSizeStat.query.filter(
                InstanceSizeStat.collected_date >= start_date,
                InstanceSizeStat.collected_date <= end_date
            ).join(Instance).all()
        
        # 处理数据为Chart.js格式 - 显示聚合数据数量统计
        processed_data = {}
        
        # 按日期统计聚合数据数量
        from collections import defaultdict
        daily_counts = defaultdict(lambda: defaultdict(int))  # {date: {instance: count}}
        
        # 统计数据库聚合数据数量
        for agg in db_aggregations:
            period_start_str = agg.period_start.strftime('%Y-%m-%d')
            instance_name = agg.instance.name if agg.instance else 'Unknown'
            daily_counts[period_start_str][f"📊 {instance_name} - 数据库聚合"] += 1
        
        # 统计实例聚合数据数量
        for agg in instance_aggregations:
            period_start_str = agg.period_start.strftime('%Y-%m-%d')
            instance_name = agg.instance.name if agg.instance else 'Unknown'
            daily_counts[period_start_str][f"🖥️ {instance_name} - 实例聚合"] += 1
        
        # 统计数据库统计数据数量（daily类型）
        for stat in db_stats:
            period_start_str = stat.collected_date.strftime('%Y-%m-%d')
            instance_name = stat.instance.name if stat.instance else 'Unknown'
            daily_counts[period_start_str][f"📈 {instance_name} - 数据库统计"] += 1
        
        # 统计实例统计数据数量（daily类型）
        for stat in instance_stats:
            period_start_str = stat.collected_date.strftime('%Y-%m-%d')
            instance_name = stat.instance.name if stat.instance else 'Unknown'
            daily_counts[period_start_str][f"📈 {instance_name} - 实例统计"] += 1
        
        # 转换为图表格式
        for date_str, instance_counts in daily_counts.items():
            for instance_key, count in instance_counts.items():
                if instance_key not in processed_data:
                    processed_data[instance_key] = {'labels': [], 'data': []}
                
                processed_data[instance_key]['labels'].append(date_str)
                processed_data[instance_key]['data'].append(count)

        # 生成所有唯一的日期标签
        all_labels = set()
        for key, value in processed_data.items():
            all_labels.update(value['labels'])
        labels = sorted(list(all_labels))
        
        # 生成Chart.js数据集
        datasets = []
        import random
        for key, value in processed_data.items():
            # 确保数据点与所有标签对齐，缺失的日期用0填充
            aligned_data = []
            data_map = dict(zip(value['labels'], value['data']))
            for lbl in labels:
                aligned_data.append(data_map.get(lbl, 0))

            datasets.append({
                'label': key,
                'data': aligned_data,
                'fill': False,
                'borderColor': '#'+''.join([random.choice('0123456789ABCDEF') for j in range(6)]),
                'tension': 0.1
            })
        
        return jsonify({
                   'labels': labels,
                   'datasets': datasets,
                   'dataPointCount': len(labels),
                   'timeRange': f'{start_date.strftime("%Y-%m-%d")} - {end_date.strftime("%Y-%m-%d")}',
                   'yAxisLabel': '聚合数据数量',
                   'chartTitle': f'{period_type.title()}聚合数据统计'
               })
        
    except Exception as e:
        logger.error(f"获取聚合数据图表时出错: {str(e)}", exc_info=True)
        return jsonify({
            'labels': [],
            'datasets': [],
            'dataPointCount': 0,
            'timeRange': '',
            'error': f'Failed to load chart data: {str(e)}'
        }), 500


