"""数据库统计服务.

提供仪表盘、统计页面等可复用的数据库聚合数据接口.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, desc, func, tuple_

from app import db
from app.errors import SystemError
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.utils.structlog_config import log_error

if TYPE_CHECKING:
    from datetime import date

    from sqlalchemy.orm import Query


@dataclass(slots=True)
class AggregationQueryParams:
    """数据库容量聚合查询参数."""

    instance_id: int | None = None
    db_type: str | None = None
    database_name: str | None = None
    database_id: int | None = None
    period_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    page: int = 1
    per_page: int = 20
    offset: int = 0
    get_all: bool = False


def _build_aggregation_filters(params: AggregationQueryParams) -> list[Any]:
    filters = []

    if params.instance_id:
        filters.append(DatabaseSizeAggregation.instance_id == params.instance_id)
    if params.db_type:
        filters.append(Instance.db_type == params.db_type)
    resolved_database_name = params.database_name
    if not resolved_database_name and params.database_id:
        db_record = InstanceDatabase.query.filter_by(id=params.database_id).first()
        if db_record:
            resolved_database_name = db_record.database_name
    if resolved_database_name:
        filters.append(DatabaseSizeAggregation.database_name == resolved_database_name)
    if params.period_type:
        filters.append(DatabaseSizeAggregation.period_type == params.period_type)
    if params.start_date:
        filters.append(DatabaseSizeAggregation.period_end >= params.start_date)
    if params.end_date:
        filters.append(DatabaseSizeAggregation.period_end <= params.end_date)

    return filters


def _apply_base_filters(params: AggregationQueryParams) -> Query:
    join_condition = and_(
        InstanceDatabase.instance_id == DatabaseSizeAggregation.instance_id,
        InstanceDatabase.database_name == DatabaseSizeAggregation.database_name,
    )

    query = (
        DatabaseSizeAggregation.query.join(Instance)
        .join(InstanceDatabase, join_condition)
        .filter(
            Instance.is_active.is_(True),
            Instance.deleted_at.is_(None),
            InstanceDatabase.is_active.is_(True),
        )
    )

    filters = _build_aggregation_filters(params)
    if filters:
        query = query.filter(*filters)
    return query


def fetch_summary(*, instance_id: int | None = None) -> dict[str, int]:
    """汇总数据库数量统计.

    统计活跃实例下的数据库总数、活跃数、非活跃数和已删除数.
    可选择性地只统计指定实例下的数据库.

    Args:
        instance_id: 可选的实例 ID,如果提供则仅统计该实例下的数据库.

    Returns:
        包含数据库统计信息的字典,格式如下:
        {
            'total_databases': 100,      # 数据库总数
            'active_databases': 85,      # 活跃数据库数
            'inactive_databases': 15,    # 非活跃数据库数
            'deleted_databases': 5       # 已删除数据库数
        }

    Raises:
        SystemError: 当数据库查询失败时抛出.

    """
    try:
        query = InstanceDatabase.query.join(Instance, Instance.id == InstanceDatabase.instance_id).filter(
            Instance.is_active.is_(True), Instance.deleted_at.is_(None),
        )

        if instance_id is not None:
            query = query.filter(InstanceDatabase.instance_id == instance_id)

        total_databases = query.count()
        active_databases = query.filter(InstanceDatabase.is_active.is_(True)).count()
        inactive_databases = max(total_databases - active_databases, 0)

        deleted_databases = (
            db.session.query(db.func.count(InstanceDatabase.id))
            .join(Instance, Instance.id == InstanceDatabase.instance_id)
            .filter(Instance.deleted_at.isnot(None))
        )
        if instance_id is not None:
            deleted_databases = deleted_databases.filter(InstanceDatabase.instance_id == instance_id)
        deleted_databases = deleted_databases.scalar() or 0

    except Exception as exc:
        log_error("获取数据库统计失败", module="database_statistics", exception=exc)
        msg = "获取数据库统计失败"
        raise SystemError(msg) from exc
    else:
        return {
            "total_databases": total_databases,
            "active_databases": active_databases,
            "inactive_databases": inactive_databases,
            "deleted_databases": deleted_databases,
        }


def empty_summary() -> dict[str, int]:
    """构造空的数据库统计结果.

    Returns:
        所有统计值为 0 的字典,格式与 fetch_summary 返回值相同.

    """
    return {
        "total_databases": 0,
        "active_databases": 0,
        "inactive_databases": 0,
        "deleted_databases": 0,
    }


def fetch_aggregations(params: AggregationQueryParams) -> dict[str, Any]:
    """获取数据库容量聚合数据.

    支持多种筛选条件和分页查询.当 get_all 为 True 时,返回 Top 100 数据库的所有聚合记录.

    Args:
        params: 聚合查询参数,可携带实例/数据库/周期/时间与分页筛选条件.

    Returns:
        包含聚合数据和分页信息的字典,格式如下:
        {
            'data': [
                {
                    'instance_id': 1,
                    'database_name': 'mydb',
                    'period_type': 'daily',
                    'avg_size_mb': 1024.5,
                    'instance': {
                        'id': 1,
                        'name': 'prod-db-01',
                        'db_type': 'mysql'
                    },
                    ...
                },
                ...
            ],
            'total': 150,
            'page': 1,
            'per_page': 20,
            'total_pages': 8,
            'has_prev': False,
            'has_next': True
        }

    """
    query = _apply_base_filters(params)

    if params.get_all:
        base_query = (
            query.with_entities(
                DatabaseSizeAggregation.instance_id,
                DatabaseSizeAggregation.database_name,
                func.max(DatabaseSizeAggregation.avg_size_mb).label("max_avg_size_mb"),
            )
            .group_by(DatabaseSizeAggregation.instance_id, DatabaseSizeAggregation.database_name)
            .subquery()
        )

        top_pairs = (
            db.session.query(
                base_query.c.instance_id,
                base_query.c.database_name,
            )
            .order_by(desc(base_query.c.max_avg_size_mb))
            .limit(100)
            .all()
        )

        if top_pairs:
            pair_values = [(row.instance_id, row.database_name) for row in top_pairs]
            aggregations = (
                query.filter(
                    tuple_(DatabaseSizeAggregation.instance_id, DatabaseSizeAggregation.database_name).in_(pair_values),
                )
                .order_by(DatabaseSizeAggregation.period_start.asc())
                .all()
            )
            total = len(aggregations)
        else:
            aggregations = []
            total = 0
        page = 1
        per_page = len(aggregations)
    else:
        query = query.order_by(desc(DatabaseSizeAggregation.period_start))
        total = query.count()
        aggregations = query.offset(params.offset).limit(params.per_page).all()
        page = params.page
        per_page = params.per_page

    data = [
        {
            **agg.to_dict(),
            "instance": {
                "id": agg.instance.id,
                "name": agg.instance.name,
                "db_type": agg.instance.db_type,
            },
        }
        for agg in aggregations
    ]

    total_pages = (total + per_page - 1) // per_page if not params.get_all else 1

    return {
        "data": data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def fetch_aggregation_summary(params: AggregationQueryParams) -> dict[str, Any]:
    """计算数据库容量聚合汇总统计.

    基于最新的聚合数据计算汇总指标,包括数据库总数、实例总数、
    总容量、平均容量、最大容量等.

    Args:
        params: 聚合查询参数,包含实例/数据库/周期/时间范围筛选条件.


    Returns:
        包含汇总统计信息的字典,格式如下:
        {
            'total_databases': 50,       # 数据库总数
            'total_instances': 10,       # 实例总数
            'total_size_mb': 102400.5,   # 总容量(MB)
            'avg_size_mb': 2048.01,      # 平均容量(MB)
            'max_size_mb': 10240.0,      # 最大容量(MB)
            'growth_rate': 0             # 增长率(暂未实现)
        }

    """
    filters = _build_aggregation_filters(params)

    join_condition = and_(
        InstanceDatabase.instance_id == DatabaseSizeAggregation.instance_id,
        InstanceDatabase.database_name == DatabaseSizeAggregation.database_name,
    )

    latest_entries = (
        db.session.query(
            DatabaseSizeAggregation.instance_id.label("instance_id"),
            DatabaseSizeAggregation.database_name.label("database_name"),
            DatabaseSizeAggregation.period_type.label("period_type"),
            func.max(DatabaseSizeAggregation.period_end).label("latest_period_end"),
        )
        .join(Instance)
        .join(InstanceDatabase, join_condition)
        .filter(Instance.is_active.is_(True), Instance.deleted_at.is_(None))
        .filter(InstanceDatabase.is_active.is_(True))
        .filter(*filters)
        .group_by(
            DatabaseSizeAggregation.instance_id,
            DatabaseSizeAggregation.database_name,
            DatabaseSizeAggregation.period_type,
        )
        .all()
    )

    if not latest_entries:
        return {
            "total_databases": 0,
            "total_instances": 0,
            "total_size_mb": 0,
            "avg_size_mb": 0,
            "max_size_mb": 0,
            "growth_rate": 0,
        }

    lookup_values = [
        (entry.instance_id, entry.database_name, entry.period_type, entry.latest_period_end) for entry in latest_entries
    ]

    aggregations = DatabaseSizeAggregation.query.filter(
        tuple_(
            DatabaseSizeAggregation.instance_id,
            DatabaseSizeAggregation.database_name,
            DatabaseSizeAggregation.period_type,
            DatabaseSizeAggregation.period_end,
        ).in_(lookup_values),
    ).all()

    if not aggregations:
        return {
            "total_databases": 0,
            "total_instances": 0,
            "total_size_mb": 0,
            "avg_size_mb": 0,
            "max_size_mb": 0,
            "growth_rate": 0,
        }

    total_databases = len({(entry.instance_id, entry.database_name) for entry in latest_entries})
    total_instances = len({entry.instance_id for entry in latest_entries})
    total_size_mb = sum(agg.avg_size_mb for agg in aggregations)
    average_size_mb = total_size_mb / total_databases if total_databases else 0
    max_size_mb = max((agg.max_size_mb or 0) for agg in aggregations)

    return {
        "total_databases": total_databases,
        "total_instances": total_instances,
        "total_size_mb": total_size_mb,
        "avg_size_mb": average_size_mb,
        "max_size_mb": max_size_mb,
        "growth_rate": 0,
    }
