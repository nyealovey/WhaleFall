"""
分区管理 API 路由
提供数据库表分区创建、清理、统计等功能
"""

import logging
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, render_template
from app.utils.time_utils import time_utils
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
def partitions_page():
    """
    分区管理页面
    """
    return render_template('database_sizes/partitions.html')

# API 路由
@partition_bp.route('/api/info', methods=['GET'])
@login_required
@view_required
def get_partition_info():
    """
    获取分区信息API
    
    Returns:
        JSON: 分区信息
    """
    try:
        logger.info("开始获取分区信息")
        service = PartitionManagementService()
        result = service.get_partition_info()
        logger.info(f"分区信息获取结果: {result}")
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': time_utils.now().isoformat()
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

# API 路由

@partition_bp.route('/api/status', methods=['GET'])
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
                'timestamp': time_utils.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取分区状态时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500




@partition_bp.route('/api/create', methods=['POST'])
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

        # 仅允许创建当前及未来的分区
        today = time_utils.now_china().date()
        current_month_start = today.replace(day=1)
        if partition_date < current_month_start:
            return jsonify({'error': '只能创建当前或未来月份的分区'}), 400
        
        service = PartitionManagementService()
        result = service.create_partition(partition_date)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': time_utils.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"创建分区时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@partition_bp.route('/api/cleanup', methods=['POST'])
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
                'timestamp': time_utils.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"清理分区时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@partition_bp.route('/api/statistics', methods=['GET'])
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
                'timestamp': time_utils.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取分区统计信息时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@partition_bp.route('/api/create-future', methods=['POST'])
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
                'timestamp': time_utils.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"创建未来分区时出错: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500








@partition_bp.route('/api/aggregations/core-metrics', methods=['GET'])
@login_required
@view_required
def get_core_aggregation_metrics():
    """
    获取核心聚合指标数据
    返回4个核心指标：实例数总量、数据库数总量、实例日统计数量、数据库日统计数量
    """
    try:
        # 获取查询参数
        period_type = request.args.get('period_type', 'daily')
        days = request.args.get('days', 7, type=int)
        
        today_china = time_utils.now_china().date()
        
        def add_months(base_date: date, months: int) -> date:
            month = base_date.month - 1 + months
            year = base_date.year + month // 12
            month = month % 12 + 1
            return date(year, month, 1)
        
        def period_end(date_obj: date, months: int) -> date:
            """返回某个起始月增加指定月数后的前一天"""
            return add_months(date_obj, months) - timedelta(days=1)
        
        # 计算统计范围和聚合周期范围
        if period_type == 'daily':
            stats_end_date = today_china - timedelta(days=1)
            stats_start_date = stats_end_date - timedelta(days=days - 1)
            period_start_date = stats_start_date
            period_end_date = stats_end_date
            step_mode = 'daily'
        elif period_type == 'weekly':
            current_week_monday = today_china - timedelta(days=today_china.weekday())
            last_week_monday = current_week_monday - timedelta(weeks=1)
            period_end_date = last_week_monday
            period_start_date = last_week_monday - timedelta(weeks=days - 1)
            stats_start_date = period_start_date
            stats_end_date = period_end_date + timedelta(days=6)
            step_mode = 'weekly'
        elif period_type == 'monthly':
            current_month_start = today_china.replace(day=1)
            last_month_start = add_months(current_month_start, -1)
            period_end_date = last_month_start
            period_start_date = add_months(last_month_start, -(days - 1))
            stats_start_date = period_start_date
            stats_end_date = period_end(period_end_date, 1)
            step_mode = 'monthly'
        elif period_type == 'quarterly':
            current_quarter_month = ((today_china.month - 1) // 3) * 3 + 1
            current_quarter_start = date(today_china.year, current_quarter_month, 1)
            last_quarter_start = add_months(current_quarter_start, -3)
            period_end_date = last_quarter_start
            period_start_date = add_months(last_quarter_start, -3 * (days - 1))
            stats_start_date = period_start_date
            stats_end_date = period_end(period_end_date, 3)
            step_mode = 'quarterly'
        else:
            stats_end_date = today_china - timedelta(days=1)
            stats_start_date = stats_end_date - timedelta(days=days - 1)
            period_start_date = stats_start_date
            period_end_date = stats_end_date
            step_mode = 'daily'
        
        if stats_end_date < stats_start_date:
            stats_start_date = stats_end_date
        if period_end_date < period_start_date:
            period_start_date = period_end_date
        
        # 查询数据库聚合数据
        db_aggregations = DatabaseSizeAggregation.query.filter(
            DatabaseSizeAggregation.period_type == period_type,
            DatabaseSizeAggregation.period_start >= period_start_date,
            DatabaseSizeAggregation.period_start <= period_end_date
        ).all()
        
        # 查询实例聚合数据
        from app.models.instance_size_aggregation import InstanceSizeAggregation
        instance_aggregations = InstanceSizeAggregation.query.filter(
            InstanceSizeAggregation.period_type == period_type,
            InstanceSizeAggregation.period_start >= period_start_date,
            InstanceSizeAggregation.period_start <= period_end_date
        ).all()
        
        # 查询原始统计数据
        from app.models.database_size_stat import DatabaseSizeStat
        from app.models.instance_size_stat import InstanceSizeStat
        
        db_stats = DatabaseSizeStat.query.filter(
            DatabaseSizeStat.collected_date >= stats_start_date,
            DatabaseSizeStat.collected_date <= stats_end_date
        ).all()
        
        instance_stats = InstanceSizeStat.query.filter(
            InstanceSizeStat.collected_date >= stats_start_date,
            InstanceSizeStat.collected_date <= stats_end_date
        ).all()
        
        # 按日期统计4个核心指标
        from collections import defaultdict
        daily_metrics = defaultdict(lambda: {
            'instance_count': 0,      # 每天采集的实例数总量（日统计）或平均值（周/月/季统计）
            'database_count': 0,      # 每天采集的数据库数总量（日统计）或平均值（周/月/季统计）
            'instance_aggregation_count': 0,  # 聚合统计下的实例统计数量
            'database_aggregation_count': 0   # 聚合统计下的数据库统计数量
        })
        
        # 统计原始采集数据
        for stat in db_stats:
            date_str = stat.collected_date.strftime('%Y-%m-%d')
            daily_metrics[date_str]['database_count'] += 1
        
        for stat in instance_stats:
            date_str = stat.collected_date.strftime('%Y-%m-%d')
            daily_metrics[date_str]['instance_count'] += 1
        
        # 统计聚合数据
        for agg in db_aggregations:
            date_str = agg.period_start.strftime('%Y-%m-%d')
            daily_metrics[date_str]['database_aggregation_count'] += 1
        
        for agg in instance_aggregations:
            date_str = agg.period_start.strftime('%Y-%m-%d')
            daily_metrics[date_str]['instance_aggregation_count'] += 1
        
        # 对于周、月、季统计，需要计算平均值
        if period_type in ['weekly', 'monthly', 'quarterly']:
            # 计算每个周期内的平均值
            period_metrics = defaultdict(lambda: {
                'instance_count': 0,
                'database_count': 0,
                'instance_aggregation_count': 0,
                'database_aggregation_count': 0,
                'days_in_period': 0
            })
            
            # 按周期分组计算平均值
            for date_str, metrics in daily_metrics.items():
                period_start = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                if period_type == 'weekly':
                    # 计算周的开始日期（周一）
                    week_start = period_start - timedelta(days=period_start.weekday())
                    period_key = week_start.strftime('%Y-%m-%d')
                elif period_type == 'monthly':
                    # 计算月的开始日期
                    month_start = period_start.replace(day=1)
                    period_key = month_start.strftime('%Y-%m-%d')
                elif period_type == 'quarterly':
                    # 计算季度的开始日期
                    quarter_month = ((period_start.month - 1) // 3) * 3 + 1
                    quarter_start = period_start.replace(month=quarter_month, day=1)
                    period_key = quarter_start.strftime('%Y-%m-%d')
                
                period_metrics[period_key]['instance_count'] += metrics['instance_count']
                period_metrics[period_key]['database_count'] += metrics['database_count']
                period_metrics[period_key]['instance_aggregation_count'] += metrics['instance_aggregation_count']
                period_metrics[period_key]['database_aggregation_count'] += metrics['database_aggregation_count']
                period_metrics[period_key]['days_in_period'] += 1
            
            # 计算平均值并更新daily_metrics
            daily_metrics = defaultdict(lambda: {
                'instance_count': 0,
                'database_count': 0,
                'instance_aggregation_count': 0,
                'database_aggregation_count': 0
            })
            
            for period_key, metrics in period_metrics.items():
                if metrics['days_in_period'] > 0:
                    daily_metrics[period_key]['instance_count'] = round(metrics['instance_count'] / metrics['days_in_period'], 1)
                    daily_metrics[period_key]['database_count'] = round(metrics['database_count'] / metrics['days_in_period'], 1)
                    daily_metrics[period_key]['instance_aggregation_count'] = metrics['instance_aggregation_count']
                    daily_metrics[period_key]['database_aggregation_count'] = metrics['database_aggregation_count']
        
        # 生成时间序列数据
        labels = []
        instance_count_data = []
        database_count_data = []
        instance_aggregation_data = []
        database_aggregation_data = []
        
        def append_metrics_for_key(key_date: date):
            key_str = key_date.strftime('%Y-%m-%d')
            labels.append(key_str)
            metrics = daily_metrics[key_str]
            instance_count_data.append(metrics['instance_count'])
            database_count_data.append(metrics['database_count'])
            instance_aggregation_data.append(metrics['instance_aggregation_count'])
            database_aggregation_data.append(metrics['database_aggregation_count'])
        
        if step_mode == 'daily':
            current_date = stats_start_date
            while current_date <= stats_end_date:
                append_metrics_for_key(current_date)
                current_date += timedelta(days=1)
        elif step_mode == 'weekly':
            current_date = period_start_date
            while current_date <= period_end_date:
                append_metrics_for_key(current_date)
                current_date += timedelta(weeks=1)
        elif step_mode == 'monthly':
            current_date = period_start_date
            while current_date <= period_end_date:
                append_metrics_for_key(current_date)
                current_date = add_months(current_date, 1)
        elif step_mode == 'quarterly':
            current_date = period_start_date
            while current_date <= period_end_date:
                append_metrics_for_key(current_date)
                current_date = add_months(current_date, 3)
        
        # 根据统计周期确定标签
        if period_type == 'daily':
            instance_label = '实例数总量'
            database_label = '数据库数总量'
            instance_agg_label = '实例日统计数量'
            database_agg_label = '数据库日统计数量'
        elif period_type == 'weekly':
            instance_label = '实例数平均值（周）'
            database_label = '数据库数平均值（周）'
            instance_agg_label = '实例周统计数量'
            database_agg_label = '数据库周统计数量'
        elif period_type == 'monthly':
            instance_label = '实例数平均值（月）'
            database_label = '数据库数平均值（月）'
            instance_agg_label = '实例月统计数量'
            database_agg_label = '数据库月统计数量'
        elif period_type == 'quarterly':
            instance_label = '实例数平均值（季）'
            database_label = '数据库数平均值（季）'
            instance_agg_label = '实例季统计数量'
            database_agg_label = '数据库季统计数量'
        else:
            instance_label = '实例数总量'
            database_label = '数据库数总量'
            instance_agg_label = '实例统计数量'
            database_agg_label = '数据库统计数量'
        
        # 构建Chart.js数据集 - 使用高透明度实现颜色混合效果
        datasets = [
            # 实例数总量 - 蓝色实线，较粗，高透明度
            {
                'label': instance_label,
                'data': instance_count_data,
                'borderColor': 'rgba(54, 162, 235, 0.7)',  # 蓝色，70%透明度
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'borderWidth': 4,
                'pointStyle': 'circle',
                'tension': 0.1,
                'fill': False
            },
            # 实例日统计数量 - 红色实线，较细，高透明度叠加
            {
                'label': instance_agg_label,
                'data': instance_aggregation_data,
                'borderColor': 'rgba(255, 99, 132, 0.7)',  # 红色，70%透明度
                'backgroundColor': 'rgba(255, 99, 132, 0.05)',
                'borderWidth': 3,
                'pointStyle': 'triangle',
                'tension': 0.1,
                'fill': False
            },
            # 数据库数总量 - 绿色实线，较粗，高透明度
            {
                'label': database_label,
                'data': database_count_data,
                'borderColor': 'rgba(75, 192, 192, 0.7)',  # 绿色，70%透明度
                'backgroundColor': 'rgba(75, 192, 192, 0.1)',
                'borderWidth': 4,
                'pointStyle': 'rect',
                'tension': 0.1,
                'fill': False
            },
            # 数据库日统计数量 - 橙色实线，较细，高透明度叠加
            {
                'label': database_agg_label,
                'data': database_aggregation_data,
                'borderColor': 'rgba(255, 159, 64, 0.7)',  # 橙色，70%透明度
                'backgroundColor': 'rgba(255, 159, 64, 0.05)',
                'borderWidth': 3,
                'pointStyle': 'star',
                'tension': 0.1,
                'fill': False
            }
        ]
        
        time_range_text = '-'
        if labels:
            time_range_text = f'{labels[0]} - {labels[-1]}'
        
        return jsonify({
            'success': True,
            'labels': labels,
            'datasets': datasets,
            'dataPointCount': len(labels),
            'timeRange': time_range_text,
            'yAxisLabel': '数量',
            'chartTitle': f'{period_type.title()}核心指标统计',
            'periodType': period_type
        })
        
    except Exception as e:
        logger.error(f"获取核心聚合指标时出错: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'labels': [],
            'datasets': [],
            'dataPointCount': 0,
            'timeRange': '',
            'yAxisLabel': '数量',
            'chartTitle': '核心指标统计'
        }), 500

