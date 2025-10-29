"""
数据库统计 API 路由
提供数据库大小监控、历史数据、统计聚合等接口
专注于数据库层面的统计功能
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import and_, desc, func

from app import db
from app.errors import SystemError, ValidationError
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.services.database_type_service import DatabaseTypeService
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils
from app.config.filter_options import DATABASE_TYPES, PERIOD_TYPES
from app.utils.filter_data import get_instance_options, get_database_options

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
    
    selected_db_type = request.args.get('db_type', '')
    selected_instance = request.args.get('instance', '')
    selected_database_id = request.args.get('database_id', '')
    selected_database = request.args.get('database', '')
    if not selected_database_id and selected_database:
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

    instance_options = get_instance_options(selected_db_type or None) if selected_db_type else []
    try:
        instance_id_int = int(selected_instance) if selected_instance else None
    except ValueError:
        instance_id_int = None
    database_options = get_database_options(instance_id_int) if instance_id_int else []
    
    return render_template(
        'database_sizes/database_aggregations.html',
        database_type_options=database_type_options,
        instance_options=instance_options,
        database_options=database_options,
        period_type_options=PERIOD_TYPES,
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


@database_stats_bp.route('/api/instances/<int:instance_id>/database-sizes/summary', methods=['GET'])
@login_required
@view_required
def get_instance_database_summary(instance_id: int) -> Response:
    """获取指定实例的数据库大小汇总信息"""
    instance = Instance.query.get_or_404(instance_id)

    try:
        summary_payload = _build_instance_database_summary(instance_id)
    except Exception as exc:
        log_error(
            "获取实例数据库汇总信息失败",
            module="database_stats",
            instance_id=instance_id,
            error=str(exc),
        )
        raise SystemError("获取数据库大小汇总信息失败") from exc

    payload = {
        'data': summary_payload,
        'instance': {
            'id': instance.id,
            'name': instance.name,
            'db_type': instance.db_type,
        },
    }

    return jsonify_unified_success(data=payload, message="数据库大小汇总获取成功")


def _build_instance_database_summary(instance_id: int) -> Dict[str, Any]:
    thirty_days_ago = time_utils.now_china().date() - timedelta(days=30)

    recent_stats = DatabaseSizeStat.query.filter(
        DatabaseSizeStat.instance_id == instance_id,
        DatabaseSizeStat.collected_date >= thirty_days_ago,
    ).all()

    if not recent_stats:
        return {
            'total_databases': 0,
            'total_size_mb': 0,
            'average_size_mb': 0,
            'largest_database': None,
            'growth_rate': 0,
            'last_collected': None,
        }

    db_stats: Dict[str, List[DatabaseSizeStat]] = {}
    for stat in recent_stats:
        db_stats.setdefault(stat.database_name, []).append(stat)

    latest_db_sizes = {
        db_name: max(stats, key=lambda x: x.collected_date).size_mb
        for db_name, stats in db_stats.items()
    }

    total_databases = len(latest_db_sizes)
    total_size_mb = sum(latest_db_sizes.values())
    average_size_mb = total_size_mb / total_databases if total_databases else 0

    largest_database = None
    if latest_db_sizes:
        largest_db_name = max(latest_db_sizes, key=latest_db_sizes.get)
        largest_database = {
            'name': largest_db_name,
            'size_mb': latest_db_sizes[largest_db_name],
        }

    growth_rate = 0.0
    if len(recent_stats) >= 2:
        sorted_stats = sorted(recent_stats, key=lambda x: x.collected_date)
        oldest_date = sorted_stats[0].collected_date
        thirty_days_ago_stats = [s for s in recent_stats if s.collected_date <= oldest_date + timedelta(days=1)]
        if thirty_days_ago_stats:
            old_total = sum(s.size_mb for s in thirty_days_ago_stats)
            new_total = sum(s.size_mb for s in recent_stats)
            if old_total > 0:
                growth_rate = ((new_total - old_total) / old_total) * 100

    last_collected = max(recent_stats, key=lambda x: x.collected_date).collected_date

    return {
        'total_databases': total_databases,
        'total_size_mb': total_size_mb,
        'average_size_mb': average_size_mb,
        'largest_database': largest_database,
        'growth_rate': growth_rate,
        'last_collected': last_collected.isoformat() if last_collected else None,
    }


@database_stats_bp.route('/api/instances/<int:instance_id>/databases', methods=['GET'])
@login_required
@view_required
def get_instance_databases(instance_id: int) -> Response:
    """获取指定实例的数据库列表"""
    Instance.query.get_or_404(instance_id)

    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
    except ValueError as exc:
        raise ValidationError('limit/offset 必须为整数') from exc

    try:
        query = InstanceDatabase.query.filter(InstanceDatabase.instance_id == instance_id).order_by(InstanceDatabase.database_name)
        total_count = query.count()
        databases = query.offset(offset).limit(limit).all()
    except Exception as exc:
        log_error(
            "获取实例数据库列表失败",
            module="database_stats",
            instance_id=instance_id,
            error=str(exc),
        )
        raise SystemError("获取实例数据库列表失败") from exc

    data = [
        {
            'id': db.id,
            'database_name': db.database_name,
            'is_active': db.is_active,
            'first_seen_date': db.first_seen_date.isoformat() if db.first_seen_date else None,
            'last_seen_date': db.last_seen_date.isoformat() if db.last_seen_date else None,
            'deleted_at': db.deleted_at.isoformat() if db.deleted_at else None,
        }
        for db in databases
    ]

    payload = {
        'databases': data,
        'total_count': total_count,
        'limit': limit,
        'offset': offset,
    }

    return jsonify_unified_success(data=payload, message="实例数据库列表获取成功")


# 实例聚合API已移动到 instance_stats 模块中


# 实例聚合汇总API已移动到 instance_stats 模块中

@database_stats_bp.route('/api/databases/aggregations', methods=['GET'])
@login_required
@view_required
def get_databases_aggregations() -> Response:
    """获取数据库统计聚合数据（数据库统计层面）"""
    instance_id = request.args.get('instance_id', type=int)
    db_type = request.args.get('db_type')
    database_name = request.args.get('database_name')
    database_id = request.args.get('database_id', type=int)
    period_type = request.args.get('period_type')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    get_all = request.args.get('get_all', 'false').lower() == 'true'
    offset = (page - 1) * per_page

    start_date = _parse_date(start_date_str, 'start_date') if start_date_str else None
    end_date = _parse_date(end_date_str, 'end_date') if end_date_str else None

    if per_page <= 0:
        raise ValidationError('per_page 必须大于 0')
    if page <= 0:
        raise ValidationError('page 必须大于 0')

    try:
        payload = _fetch_database_aggregations(
            instance_id=instance_id,
            db_type=db_type,
            database_name=database_name,
            database_id=database_id,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            per_page=per_page,
            offset=offset,
            get_all=get_all,
        )
    except ValidationError:
        raise
    except Exception as exc:
        log_error(
            "获取数据库统计聚合数据失败",
            module="database_stats",
            error=str(exc),
        )
        raise SystemError("获取数据库统计聚合数据失败") from exc

    return jsonify_unified_success(data=payload, message="数据库统计聚合数据获取成功")


def _parse_date(value: str, field: str) -> date:
    try:
        parsed_dt = time_utils.to_china(value + 'T00:00:00')
        if parsed_dt is None:
            raise ValueError("无法解析日期")
        return parsed_dt.date()
    except Exception as exc:
        raise ValidationError(f'{field} 格式错误，应为 YYYY-MM-DD') from exc


def _fetch_database_aggregations(
    *,
    instance_id: Optional[int],
    db_type: Optional[str],
    database_name: Optional[str],
    database_id: Optional[int],
    period_type: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    page: int,
    per_page: int,
    offset: int,
    get_all: bool,
) -> Dict[str, Any]:
    query = DatabaseSizeAggregation.query.join(Instance)

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
        query = query.filter(DatabaseSizeAggregation.period_start >= start_date)
    if end_date:
        query = query.filter(DatabaseSizeAggregation.period_end <= end_date)

    if get_all:
        base_query = query.with_entities(
            DatabaseSizeAggregation.instance_id,
            DatabaseSizeAggregation.database_name,
            func.max(DatabaseSizeAggregation.avg_size_mb).label('max_avg_size_mb'),
        ).group_by(DatabaseSizeAggregation.instance_id, DatabaseSizeAggregation.database_name).subquery()

        top_pairs = db.session.query(
            base_query.c.instance_id,
            base_query.c.database_name,
        ).order_by(desc(base_query.c.max_avg_size_mb)).limit(100).all()

        if top_pairs:
            from sqlalchemy import tuple_

            pair_values = [(row.instance_id, row.database_name) for row in top_pairs]
            aggregations = (
                query.filter(tuple_(DatabaseSizeAggregation.instance_id, DatabaseSizeAggregation.database_name).in_(pair_values))
                .order_by(DatabaseSizeAggregation.period_start.asc())
                .all()
            )
            total = len(aggregations)
        else:
            aggregations = []
            total = 0
    else:
        query = query.order_by(desc(DatabaseSizeAggregation.period_start))
        total = query.count()
        aggregations = query.offset(offset).limit(per_page).all()

    data = []
    for agg in aggregations:
        agg_dict = agg.to_dict()
        agg_dict['instance'] = {
            'id': agg.instance.id,
            'name': agg.instance.name,
            'db_type': agg.instance.db_type,
        }
        data.append(agg_dict)

    total_pages = (total + per_page - 1) // per_page if not get_all else 1

    return {
        'data': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
    }


@database_stats_bp.route('/api/databases/aggregations/summary', methods=['GET'])
@login_required
@view_required
def get_databases_aggregations_summary() -> Response:
    """获取数据库统计聚合汇总信息"""
    instance_id = request.args.get('instance_id', type=int)
    db_type = request.args.get('db_type')
    database_name = request.args.get('database_name')
    database_id = request.args.get('database_id', type=int)
    period_type = request.args.get('period_type')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date = _parse_date(start_date_str, 'start_date') if start_date_str else None
    end_date = _parse_date(end_date_str, 'end_date') if end_date_str else None

    try:
        summary = _fetch_database_aggregation_summary(
            instance_id=instance_id,
            db_type=db_type,
            database_name=database_name,
            database_id=database_id,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
        )
    except ValidationError:
        raise
    except Exception as exc:
        log_error(
            "获取数据库统计聚合汇总信息失败",
            module="database_stats",
            error=str(exc),
        )
        raise SystemError("获取数据库统计聚合汇总信息失败") from exc

    return jsonify_unified_success(data={'summary': summary}, message="数据库统计聚合汇总获取成功")


def _fetch_database_aggregation_summary(
    *,
    instance_id: Optional[int],
    db_type: Optional[str],
    database_name: Optional[str],
    database_id: Optional[int],
    period_type: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
) -> Dict[str, Any]:
    query = DatabaseSizeAggregation.query.join(Instance)

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
        query = query.filter(DatabaseSizeAggregation.period_start >= start_date)
    if end_date:
        query = query.filter(DatabaseSizeAggregation.period_end <= end_date)

    aggregations = query.all()

    if not aggregations:
        return {
            'total_databases': 0,
            'total_instances': 0,
            'total_size_mb': 0,
            'average_size_mb': 0,
            'max_size_mb': 0,
            'growth_rate': 0,
        }

    total_databases = len({(agg.instance_id, agg.database_name) for agg in aggregations})
    total_instances = len({agg.instance_id for agg in aggregations})
    total_size_mb = sum(agg.avg_size_mb for agg in aggregations)
    average_size_mb = total_size_mb / total_databases if total_databases else 0
    max_size_mb = max((agg.max_size_mb or 0) for agg in aggregations)

    growth_rate = 0.0
    if len(aggregations) >= 2:
        sorted_agg = sorted(aggregations, key=lambda x: x.period_end)
        latest = sorted_agg[-1]
        previous = sorted_agg[-2]
        if previous.avg_size_mb and previous.avg_size_mb > 0:
            growth_rate = ((latest.avg_size_mb - previous.avg_size_mb) / previous.avg_size_mb) * 100

    return {
        'total_databases': total_databases,
        'total_instances': total_instances,
        'total_size_mb': total_size_mb,
        'average_size_mb': average_size_mb,
        'max_size_mb': max_size_mb,
        'growth_rate': growth_rate,
    }
