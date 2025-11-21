"""
数据库统计 API 路由
提供数据库大小监控、历史数据、统计聚合等接口
专注于数据库层面的统计功能
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import and_, func

from app.errors import SystemError, ValidationError
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.services.database_type_service import DatabaseTypeService
from app.services.statistics.database_statistics_service import (
    fetch_aggregation_summary,
    fetch_aggregations,
)
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils
from app.constants import DATABASE_TYPES, PERIOD_TYPES
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
        payload = fetch_aggregations(
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
        summary = fetch_aggregation_summary(
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
