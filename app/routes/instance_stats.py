"""实例统计 API 路由"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import and_, desc, func, tuple_

from app import db
from app.constants.system_constants import SuccessMessages
from app.errors import NotFoundError, SystemError, ValidationError as AppValidationError
from app.models.instance import Instance
from app.models.instance_size_stat import InstanceSizeStat
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info, log_warning
from app.utils.time_utils import time_utils
from app.constants.filter_options import DATABASE_TYPES, PERIOD_TYPES
from app.utils.query_filter_utils import get_instance_options

# 创建蓝图
instance_stats_bp = Blueprint('instance_stats', __name__)


def _get_instance(instance_id: int) -> Instance:
    instance = Instance.query.filter_by(id=instance_id).first()
    if instance is None:
        raise NotFoundError("实例不存在")
    return instance


def _parse_iso_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as exc:
        raise AppValidationError(f"{field_name} 格式错误，需使用 YYYY-MM-DD") from exc


# 页面路由
@instance_stats_bp.route('/instance', methods=['GET'])
@login_required
@view_required
def instance_aggregations():
    """
    实例统计聚合页面（实例统计层面）
    返回HTML页面
    """
    # 读取已选择的筛选条件以便回填
    selected_db_type = request.args.get('db_type', '')
    selected_instance = request.args.get('instance', '')
    selected_period_type = request.args.get('period_type', 'daily')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    from app.services.database_type_service import DatabaseTypeService
    database_type_configs = DatabaseTypeService.get_active_types()
    if database_type_configs:
        database_type_options = [
            {
                'value': config.name,
                'label': config.display_name,
            }
            for config in database_type_configs
        ]
    else:
        database_type_options = [
            {
                'value': item['name'],
                'label': item['display_name'],
            }
            for item in DATABASE_TYPES
        ]

    instance_options = get_instance_options(selected_db_type or None) if selected_db_type else []

    
    return render_template(
        'database_sizes/instance_aggregations.html',
        instance_options=instance_options,
        database_type_options=database_type_options,
        period_type_options=PERIOD_TYPES,
        db_type=selected_db_type,
        instance=selected_instance,
        period_type=selected_period_type,
        start_date=start_date,
        end_date=end_date,
    )

@instance_stats_bp.route('/api/instances/<int:instance_id>/database-sizes/total', methods=['GET'])
@login_required
@view_required
def get_instance_total_size(instance_id: int) -> Response:
    """
    获取指定实例的数据库总大小（从InstanceSizeStat表获取）
    
    Args:
        instance_id: 实例ID
        
    Returns:
        JSON: 实例总大小信息
    """
    try:
        # 验证实例是否存在
        instance = _get_instance(instance_id)
        
        # 从InstanceSizeStat表获取最新的实例大小统计数据
        latest_stat = InstanceSizeStat.query.filter(
            InstanceSizeStat.instance_id == instance_id,
            InstanceSizeStat.is_deleted == False
        ).order_by(InstanceSizeStat.collected_date.desc()).first()
        
        if not latest_stat:
            payload = {
                'total_size_mb': 0,
                'database_count': 0,
                'last_collected': None,
            }
            return jsonify_unified_success(data=payload, message="实例总大小获取成功")
        
        # 直接使用实例大小统计数据
        total_size_mb = latest_stat.total_size_mb
        database_count = latest_stat.database_count
        last_collected = latest_stat.collected_date
        
        payload = {
            'total_size_mb': total_size_mb,
            'database_count': database_count,
            'last_collected': last_collected.isoformat() if last_collected else None,
        }
        log_info("获取实例总大小成功", module="instance_stats", instance_id=instance_id)
        return jsonify_unified_success(data=payload, message="实例总大小获取成功")

    except Exception as exc:
        log_error("获取实例总大小失败", module="instance_stats", instance_id=instance_id, error=str(exc))
        raise SystemError("获取实例总大小失败") from exc


@instance_stats_bp.route('/api/instance-options', methods=['GET'])
@login_required
@view_required
def get_instance_options() -> Response:
    """
    提供实例下拉选项，支持按数据库类型过滤
    """
    try:
        db_type = request.args.get('db_type')

        query = Instance.query.filter(Instance.is_active.is_(True))
        if db_type:
            db_type_lower = db_type.lower()
            query = query.filter(func.lower(Instance.db_type) == db_type_lower)

        instances = query.order_by(Instance.name.asc()).all()

        options = [
            {
                'id': instance.id,
                'name': instance.name,
                'db_type': instance.db_type,
                'display_name': f"{instance.name} ({instance.db_type.upper()})",
            }
            for instance in instances
        ]

        log_info("加载实例选项成功", module="instance_stats", count=len(options))
        return jsonify_unified_success(data={'instances': options}, message="实例选项获取成功")
    except Exception as exc:
        log_error("加载实例选项失败", module="instance_stats", error=str(exc))
        raise SystemError("加载实例选项失败") from exc


@instance_stats_bp.route('/api/instances/aggregations', methods=['GET'])
@login_required
@view_required
def get_instances_aggregations():
    """
    获取实例聚合数据（实例统计层面）
    原 /api/instance/data 功能
    
    Returns:
        JSON: 实例聚合数据
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        period_type = request.args.get('period_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        time_range = request.args.get('time_range')
        
        # 处理time_range参数，转换为start_date和end_date
        if time_range and not start_date and not end_date:
            end_date_obj = time_utils.now_china()
            start_date_obj = end_date_obj - timedelta(days=int(time_range))
            start_date = time_utils.format_china_time(start_date_obj, '%Y-%m-%d')
            end_date = time_utils.format_china_time(end_date_obj, '%Y-%m-%d')
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        # 是否返回所有数据（用于图表显示）
        get_all = request.args.get('get_all', 'false').lower() == 'true'
        
        # 计算offset
        offset = (page - 1) * per_page
        limit = per_page
        
        # 构建查询 - 查询实例统计聚合表
        from app.models.instance_size_aggregation import InstanceSizeAggregation
        query = InstanceSizeAggregation.query.join(Instance)
        
        # 应用过滤条件
        if instance_id:
            query = query.filter(InstanceSizeAggregation.instance_id == instance_id)
        if db_type:
            query = query.filter(Instance.db_type == db_type)
        if period_type:
            query = query.filter(InstanceSizeAggregation.period_type == period_type)
        start_date_obj = None
        end_date_obj = None
        if start_date:
            start_date_obj = _parse_iso_date(start_date, 'start_date')
            query = query.filter(InstanceSizeAggregation.period_start >= start_date_obj)
        if end_date:
            end_date_obj = _parse_iso_date(end_date, 'end_date')
            query = query.filter(InstanceSizeAggregation.period_end <= end_date_obj)
        
        # 排序和分页
        if get_all:
            # 用于图表显示：按总大小排序获取TOP N实例
            # 先按实例分组，获取每个实例的最大容量
            subquery = query.with_entities(
                InstanceSizeAggregation.instance_id,
                func.max(InstanceSizeAggregation.total_size_mb).label('max_total_size_mb')
            ).group_by(InstanceSizeAggregation.instance_id).subquery()
            
            # 获取TOP 100实例的ID
            top_instances = db.session.query(subquery.c.instance_id).order_by(
                desc(subquery.c.max_total_size_mb)
            ).limit(100).all()
            top_instance_ids = [row[0] for row in top_instances]
            
            # 获取这些实例的所有聚合数据
            aggregations = query.filter(
                InstanceSizeAggregation.instance_id.in_(top_instance_ids)
            ).order_by(desc(InstanceSizeAggregation.total_size_mb)).all()
            total = len(aggregations)
        else:
            # 用于表格显示：按时间排序分页
            query = query.order_by(desc(InstanceSizeAggregation.period_start))
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
            # 为了兼容前端，添加 avg_size_mb 字段
            agg_dict['avg_size_mb'] = agg_dict.get('total_size_mb', 0)
            data.append(agg_dict)
        
        return jsonify_unified_success(
            data={
                'items': data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page,
                'has_prev': page > 1,
                'has_next': page < (total + per_page - 1) // per_page,
            },
            message=SuccessMessages.OPERATION_SUCCESS,
        )
        
    except AppValidationError:
        raise
    except Exception as exc:
        log_error("获取实例聚合数据时出错", module="instance_stats", error=str(exc))
        raise SystemError("获取实例聚合数据失败") from exc


@instance_stats_bp.route('/api/instances/aggregations/summary', methods=['GET'])
@login_required
@view_required
def get_instances_aggregations_summary():
    """
    获取实例聚合汇总信息（实例统计层面）
    原 /api/instance/summary 功能
    
    Returns:
        JSON: 实例聚合汇总信息
    """
    try:
        # 获取查询参数
        instance_id = request.args.get('instance_id', type=int)
        db_type = request.args.get('db_type')
        period_type = request.args.get('period_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        time_range = request.args.get('time_range')
        
        # 处理time_range参数，转换为start_date和end_date
        if time_range and not start_date and not end_date:
            end_date_obj = time_utils.now_china()
            start_date_obj = end_date_obj - timedelta(days=int(time_range))
            start_date = time_utils.format_china_time(start_date_obj, '%Y-%m-%d')
            end_date = time_utils.format_china_time(end_date_obj, '%Y-%m-%d')
        
        # 解析日期参数
        start_date_obj = None
        end_date_obj = None
        if start_date:
            start_date_obj = _parse_iso_date(start_date, 'start_date')
        if end_date:
            end_date_obj = _parse_iso_date(end_date, 'end_date')

        # 优先使用实例大小统计表（与容量同步实时同步）
        stat_query = InstanceSizeStat.query.join(Instance).filter(
            InstanceSizeStat.is_deleted.is_(False)
        )
        if instance_id:
            stat_query = stat_query.filter(InstanceSizeStat.instance_id == instance_id)
        if db_type:
            stat_query = stat_query.filter(Instance.db_type == db_type)
        if start_date_obj:
            stat_query = stat_query.filter(InstanceSizeStat.collected_date >= start_date_obj)
        if end_date_obj:
            stat_query = stat_query.filter(InstanceSizeStat.collected_date <= end_date_obj)

        stats = stat_query.all()
        latest_stats_by_instance: Dict[int, InstanceSizeStat] = {}
        for stat in stats:
            existing = latest_stats_by_instance.get(stat.instance_id)
            current_ts = stat.collected_at or datetime.combine(
                stat.collected_date, datetime.min.time()
            )
            if not existing:
                latest_stats_by_instance[stat.instance_id] = stat
                continue
            existing_ts = existing.collected_at or datetime.combine(
                existing.collected_date, datetime.min.time()
            )
            if current_ts > existing_ts:
                latest_stats_by_instance[stat.instance_id] = stat

        total_instances = len(latest_stats_by_instance)
        total_size_mb = sum(
            stat.total_size_mb or 0 for stat in latest_stats_by_instance.values()
        )
        avg_size_mb = total_size_mb / total_instances if total_instances else 0
        max_size_mb = (
            max(stat.total_size_mb or 0 for stat in latest_stats_by_instance.values())
            if latest_stats_by_instance
            else 0
        )

        summary_payload = {
            'total_instances': total_instances,
            'total_size_mb': total_size_mb,
            'avg_size_mb': avg_size_mb,
            'max_size_mb': max_size_mb,
            'period_type': period_type or 'all',
            'source': 'instance_size_stats',
        }

        return jsonify_unified_success(
            data={'summary': summary_payload},
            message=SuccessMessages.OPERATION_SUCCESS,
        )
        
    except AppValidationError:
        raise
    except Exception as exc:
        log_error("获取实例聚合汇总时出错", module="instance_stats", error=str(exc))
        raise SystemError("获取实例聚合汇总失败") from exc
