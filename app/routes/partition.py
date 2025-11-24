"""分区管理 API 路由"""

from datetime import date, timedelta

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import and_, desc, func, or_, text

from app import db
from app.errors import SystemError, ValidationError
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.services.partition_management_service import PartitionManagementService
from app.services.statistics.partition_statistics_service import PartitionStatisticsService
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils

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
    return render_template('admin/partitions/index.html')

# API 路由
@partition_bp.route('/api/info', methods=['GET'])
@login_required
@view_required
def get_partition_info() -> Response:
    """获取分区信息API"""
    log_info("开始获取分区信息", module="partition", user_id=getattr(current_user, "id", None))
    stats_service = PartitionStatisticsService()
    result = stats_service.get_partition_info()
    payload = {
        'data': result,
        'timestamp': time_utils.now().isoformat(),
    }
    log_info("分区信息获取成功", module="partition")
    return jsonify_unified_success(data=payload, message="分区信息获取成功")

# API 路由


def _safe_int(value: str | None, default: int, *, minimum: int = 1, maximum: int = 100) -> int:
    """解析并限制整数参数范围"""
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def _build_partition_status(stats_service: PartitionStatisticsService) -> dict[str, object]:
    partition_info = stats_service.get_partition_info()
    stats = stats_service.get_partition_statistics()

    current_date = date.today()
    required_partitions: list[str] = []
    for offset in range(3):
        month_date = (current_date.replace(day=1) + timedelta(days=offset * 32)).replace(day=1)
        required_partitions.append(
            f"database_size_stats_{time_utils.format_china_time(month_date, '%Y_%m')}"
        )

    existing_partitions = {partition["name"] for partition in partition_info["partitions"]}
    missing_partitions = [name for name in required_partitions if name not in existing_partitions]

    status = "healthy" if not missing_partitions else "warning"
    return {
        "status": status,
        "total_partitions": stats["total_partitions"],
        "total_size": stats["total_size"],
        "total_records": stats["total_records"],
        "missing_partitions": missing_partitions,
        "partitions": partition_info["partitions"],
    }


@partition_bp.route('/api/status', methods=['GET'])
@login_required
@view_required
def get_partition_status() -> Response:
    """获取分区管理状态"""

    stats_service = PartitionStatisticsService()
    try:
        result = _build_partition_status(stats_service)
    except Exception as exc:  # noqa: BLE001
        log_error("获取分区管理状态失败", module="partition", exception=exc)
        raise SystemError("获取分区管理状态失败") from exc

    if result.get('status') != 'healthy':
        log_warning(
            "分区状态存在告警",
            module="partition",
            status=result.get('status'),
            missing_partitions=result.get('missing_partitions'),
        )

    payload = {
        'data': result,
        'timestamp': time_utils.now().isoformat(),
    }
    log_info("获取分区状态成功", module="partition")
    return jsonify_unified_success(data=payload, message="分区状态获取成功")


@partition_bp.route('/api/partitions', methods=['GET'])
@login_required
@view_required
def list_partitions() -> Response:
    """分页返回分区列表，供 Grid.js 使用"""

    stats_service = PartitionStatisticsService()
    partition_info = stats_service.get_partition_info()
    partitions = list(partition_info.get('partitions', []))

    search_term = (request.args.get('search') or '').strip().lower()
    table_type = (request.args.get('table_type') or '').strip().lower()
    status_filter = (request.args.get('status') or '').strip().lower()

    if table_type:
        partitions = [
            partition
            for partition in partitions
            if (partition.get('table_type') or '').lower() == table_type
        ]

    if status_filter:
        partitions = [
            partition
            for partition in partitions
            if (partition.get('status') or '').lower() == status_filter
        ]

    if search_term:
        partitions = [
            partition
            for partition in partitions
            if search_term in (partition.get('name') or '').lower()
            or search_term in (partition.get('display_name') or '').lower()
        ]

    sort_field = (request.args.get('sort') or 'name').lower()
    sort_order = (request.args.get('order') or 'asc').lower()
    sortable_fields = {
        'name': lambda item: (item.get('name') or '').lower(),
        'table_type': lambda item: (item.get('table_type') or '').lower(),
        'size': lambda item: item.get('size_bytes') or 0,
        'size_bytes': lambda item: item.get('size_bytes') or 0,
        'record_count': lambda item: item.get('record_count') or 0,
        'status': lambda item: (item.get('status') or '').lower(),
        'date': lambda item: item.get('date') or '',
    }
    sort_resolver = sortable_fields.get(sort_field, sortable_fields['date'])
    partitions.sort(key=sort_resolver, reverse=(sort_order == 'desc'))

    limit = _safe_int(request.args.get('limit'), default=20, minimum=1, maximum=200)
    total = len(partitions)
    pages = max((total + limit - 1) // limit, 1)
    page = _safe_int(request.args.get('page'), default=1, minimum=1, maximum=pages)

    start = (page - 1) * limit
    end = start + limit
    items = partitions[start:end]

    payload = {
        'items': items,
        'total': total,
        'page': page,
        'pages': pages,
        'limit': limit,
    }

    log_info(
        "获取分区列表成功",
        module="partition",
        total=total,
        page=page,
        limit=limit,
    )
    return jsonify_unified_success(data=payload, message="分区列表获取成功")




@partition_bp.route('/api/create', methods=['POST'])
@login_required
@view_required
@require_csrf
def create_partition() -> Response:
    """创建分区任务。

    Returns:
        Response: 包含分区创建结果的 JSON 响应。
    """
    data = request.get_json() or {}
    partition_date_str = data.get('date')

    if not partition_date_str:
        raise ValidationError('缺少日期参数')

    try:
        parsed_dt = time_utils.to_china(partition_date_str + 'T00:00:00')
        if parsed_dt is None:
            raise ValueError("无法解析日期")
        partition_date = parsed_dt.date()
    except Exception as exc:
        raise ValidationError('日期格式错误，请使用 YYYY-MM-DD 格式') from exc

    today = time_utils.now_china().date()
    current_month_start = today.replace(day=1)
    if partition_date < current_month_start:
        raise ValidationError('只能创建当前或未来月份的分区')

    service = PartitionManagementService()
    result = service.create_partition(partition_date)

    payload = {
        'result': result,
        'timestamp': time_utils.now().isoformat(),
    }

    log_info(
        "创建分区成功",
        module="partition",
        partition_date=str(partition_date),
        user_id=getattr(current_user, 'id', None),
    )
    return jsonify_unified_success(data=payload, message='分区创建任务已触发')


@partition_bp.route('/api/cleanup', methods=['POST'])
@login_required
@view_required
@require_csrf
def cleanup_partitions() -> Response:
    """清理旧分区。

    Returns:
        Response: 包含清理任务执行结果的 JSON 响应。
    """
    data = request.get_json() or {}
    raw_retention = data.get('retention_months', 12)
    try:
        retention_months = int(raw_retention)
    except (TypeError, ValueError) as exc:
        raise ValidationError('retention_months 必须为数字') from exc

    service = PartitionManagementService()
    result = service.cleanup_old_partitions(retention_months=retention_months)

    payload = {
        'result': result,
        'timestamp': time_utils.now().isoformat(),
    }

    log_info(
        "清理旧分区成功",
        module="partition",
        retention_months=retention_months,
        user_id=getattr(current_user, 'id', None),
    )
    return jsonify_unified_success(data=payload, message='旧分区清理任务已触发')


@partition_bp.route('/api/statistics', methods=['GET'])
@login_required
@view_required
def get_partition_statistics() -> Response:
    """获取分区统计信息"""
    service = PartitionStatisticsService()
    result = service.get_partition_statistics()

    payload = {
        'data': result,
        'timestamp': time_utils.now().isoformat(),
    }

    log_info("获取分区统计信息成功", module="partition")
    return jsonify_unified_success(data=payload, message="分区统计信息获取成功")








@partition_bp.route('/api/aggregations/core-metrics', methods=['GET'])
@login_required
@view_required
def get_core_aggregation_metrics() -> Response:
    """获取核心聚合指标数据"""
    try:
        period_type = request.args.get('period_type', 'daily')
        days = request.args.get('days', 7, type=int)

        today_china = time_utils.now_china().date()

        def add_months(base_date: date, months: int) -> date:
            month = base_date.month - 1 + months
            year = base_date.year + month // 12
            month = month % 12 + 1
            return date(year, month, 1)

        def period_end(date_obj: date, months: int) -> date:
            return add_months(date_obj, months) - timedelta(days=1)

        valid_periods = {'daily', 'weekly', 'monthly', 'quarterly'}
        if period_type not in valid_periods:
            log_warning("无效的 period_type，默认使用 daily", module="partition", period_type=period_type)
            period_type = 'daily'

        if period_type == 'daily':
            stats_end_date = today_china
            stats_start_date = stats_end_date - timedelta(days=days - 1)
            period_start_date = stats_start_date
            period_end_date = stats_end_date
            step_mode = 'daily'
        elif period_type == 'weekly':
            current_week_monday = today_china - timedelta(days=today_china.weekday())
            period_end_date = current_week_monday
            period_start_date = current_week_monday - timedelta(weeks=days - 1)
            stats_start_date = period_start_date
            stats_end_date = period_end_date + timedelta(days=6)
            step_mode = 'weekly'
        elif period_type == 'monthly':
            current_month_start = today_china.replace(day=1)
            period_end_date = current_month_start
            period_start_date = add_months(current_month_start, -(days - 1))
            stats_start_date = period_start_date
            stats_end_date = period_end(period_end_date, 1)
            step_mode = 'monthly'
        else:  # quarterly
            current_quarter_month = ((today_china.month - 1) // 3) * 3 + 1
            current_quarter_start = date(today_china.year, current_quarter_month, 1)
            period_end_date = current_quarter_start
            period_start_date = add_months(current_quarter_start, -3 * (days - 1))
            stats_start_date = period_start_date
            stats_end_date = period_end(period_end_date, 3)
            step_mode = 'quarterly'
        
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
        instance_aggregations = InstanceSizeAggregation.query.filter(
            InstanceSizeAggregation.period_type == period_type,
            InstanceSizeAggregation.period_start >= period_start_date,
            InstanceSizeAggregation.period_start <= period_end_date
        ).all()
        
        # 查询原始统计数据
        
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
            date_str = stat.collected_date.isoformat()
            daily_metrics[date_str]['database_count'] += 1
        
        for stat in instance_stats:
            date_str = stat.collected_date.isoformat()
            daily_metrics[date_str]['instance_count'] += 1
        
        # 统计聚合数据
        for agg in db_aggregations:
            date_str = agg.period_start.isoformat()
            daily_metrics[date_str]['database_aggregation_count'] += 1
        
        for agg in instance_aggregations:
            date_str = agg.period_start.isoformat()
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
                parsed_dt = time_utils.to_china(date_str + 'T00:00:00')
                if parsed_dt is None:
                    continue
                period_start = parsed_dt.date()
                
                if period_type == 'weekly':
                    # 计算周的开始日期（周一）
                    week_start = period_start - timedelta(days=period_start.weekday())
                    period_key = week_start.isoformat()
                elif period_type == 'monthly':
                    # 计算月的开始日期
                    month_start = period_start.replace(day=1)
                    period_key = month_start.isoformat()
                elif period_type == 'quarterly':
                    # 计算季度的开始日期
                    quarter_month = ((period_start.month - 1) // 3) * 3 + 1
                    quarter_start = period_start.replace(month=quarter_month, day=1)
                    period_key = quarter_start.isoformat()
                
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
        
        def get_label_date(key_date: date) -> date:
            if step_mode == 'daily':
                return key_date
            if step_mode == 'weekly':
                return key_date + timedelta(days=6)
            if step_mode == 'monthly':
                return period_end(key_date, 1)
            if step_mode == 'quarterly':
                return period_end(key_date, 3)
            return key_date

        def append_metrics_for_key(key_date: date):
            key_str = key_date.isoformat()
            display_date = get_label_date(key_date).isoformat()
            labels.append(display_date)
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
        
        payload = {
            'labels': labels,
            'datasets': datasets,
            'dataPointCount': len(labels),
            'timeRange': time_range_text,
            'yAxisLabel': '数量',
            'chartTitle': f'{period_type.title()}核心指标统计',
            'periodType': period_type,
        }

        log_info(
            "核心聚合指标获取成功",
            module="partition",
            period_type=period_type,
            points=len(labels),
        )
        return jsonify_unified_success(data=payload, message="核心聚合指标获取成功")

    except ValidationError:
        raise
    except Exception as exc:
        log_error("获取核心聚合指标失败", module="partition", error=str(exc))
        raise SystemError("获取核心聚合指标失败") from exc
