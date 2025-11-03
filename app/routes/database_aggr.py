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
from app.constants.filter_options import DATABASE_TYPES, PERIOD_TYPES
from app.utils.query_filter_utils import get_instance_options, get_database_options

# 创建蓝图
database_aggr_bp = Blueprint('database_aggr', __name__)


@database_aggr_bp.route('/', methods=['GET'])
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
        'statistics/database_aggregations.html',
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


@database_aggr_bp.route('/api/databases/aggregations', methods=['GET'])
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
            module="database_aggr",
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


@database_aggr_bp.route('/api/databases/aggregations/summary', methods=['GET'])
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
            module="database_aggr",
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
    filters = []

    if instance_id:
        filters.append(DatabaseSizeAggregation.instance_id == instance_id)
    if db_type:
        filters.append(Instance.db_type == db_type)
    resolved_database_name = database_name
    if not resolved_database_name and database_id:
        from app.models.instance_database import InstanceDatabase

        db_record = InstanceDatabase.query.filter_by(id=database_id).first()
        if db_record:
            resolved_database_name = db_record.database_name
    if resolved_database_name:
        filters.append(DatabaseSizeAggregation.database_name == resolved_database_name)
    if period_type:
        filters.append(DatabaseSizeAggregation.period_type == period_type)
    if start_date:
        filters.append(DatabaseSizeAggregation.period_end >= start_date)
    if end_date:
        filters.append(DatabaseSizeAggregation.period_end <= end_date)

    latest_entries_query = (
        db.session.query(
            DatabaseSizeAggregation.instance_id.label("instance_id"),
            DatabaseSizeAggregation.database_name.label("database_name"),
            DatabaseSizeAggregation.period_type.label("period_type"),
            func.max(DatabaseSizeAggregation.period_end).label("latest_period_end"),
        )
        .join(Instance)
        .filter(*filters)
        .group_by(
            DatabaseSizeAggregation.instance_id,
            DatabaseSizeAggregation.database_name,
            DatabaseSizeAggregation.period_type,
        )
    )

    latest_entries = latest_entries_query.all()

    if not latest_entries:
        return {
            'total_databases': 0,
            'total_instances': 0,
            'total_size_mb': 0,
            'avg_size_mb': 0,
            'average_size_mb': 0,
            'max_size_mb': 0,
            'growth_rate': 0,
        }

    from sqlalchemy import tuple_

    lookup_values = [
        (entry.instance_id, entry.database_name, entry.period_type, entry.latest_period_end)
        for entry in latest_entries
    ]

    aggregations = (
        DatabaseSizeAggregation.query.filter(
            tuple_(
                DatabaseSizeAggregation.instance_id,
                DatabaseSizeAggregation.database_name,
                DatabaseSizeAggregation.period_type,
                DatabaseSizeAggregation.period_end,
            ).in_(lookup_values)
        ).all()
    )

    if not aggregations:
        return {
            'total_databases': 0,
            'total_instances': 0,
            'total_size_mb': 0,
            'avg_size_mb': 0,
            'average_size_mb': 0,
            'max_size_mb': 0,
            'growth_rate': 0,
        }

    total_databases = len({(entry.instance_id, entry.database_name) for entry in latest_entries})
    total_instances = len({entry.instance_id for entry in latest_entries})
    total_size_mb = sum(agg.avg_size_mb for agg in aggregations)
    average_size_mb = total_size_mb / total_databases if total_databases else 0
    max_size_mb = max((agg.max_size_mb or 0) for agg in aggregations)

    growth_rate = 0.0

    return {
        'total_databases': total_databases,
        'total_instances': total_instances,
        'total_size_mb': total_size_mb,
        'avg_size_mb': average_size_mb,
        'average_size_mb': average_size_mb,
        'max_size_mb': max_size_mb,
        'growth_rate': growth_rate,
    }
