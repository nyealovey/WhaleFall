"""数据库统计服务.

提供仪表盘、统计页面等可复用的数据库聚合数据接口.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.core.exceptions import SystemError
from app.core.types.capacity_databases import DatabaseAggregationsFilters, DatabaseAggregationsSummaryFilters
from app.repositories.capacity_databases_repository import CapacityDatabasesRepository
from app.repositories.database_statistics_repository import DatabaseStatisticsRepository
from app.utils.structlog_config import log_error


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
        return DatabaseStatisticsRepository.fetch_summary(instance_id=instance_id)
    except Exception as exc:
        log_error("获取数据库统计失败", module="database_statistics", exception=exc)
        msg = "获取数据库统计失败"
        raise SystemError(msg) from exc


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
    repository = CapacityDatabasesRepository()
    page = max(1, int(getattr(params, "page", 1) or 1))
    per_page = max(1, int(getattr(params, "per_page", 20) or 20))
    if params.offset and params.offset >= 0 and page == 1:
        page = (int(params.offset) // per_page) + 1

    filters = DatabaseAggregationsFilters(
        instance_id=params.instance_id,
        db_type=params.db_type,
        database_name=params.database_name,
        database_id=params.database_id,
        period_type=params.period_type,
        start_date=params.start_date,
        end_date=params.end_date,
        page=page,
        limit=per_page,
        get_all=bool(params.get_all),
    )
    rows, total = repository.list_aggregations(filters)

    data = [
        {
            **aggregation.to_dict(),
            "instance": {
                "id": instance.id,
                "name": instance.name,
                "db_type": instance.db_type,
            },
        }
        for aggregation, instance in rows
    ]

    if params.get_all:
        per_page = len(rows)
        page = 1
        total_pages = 1
    else:
        total_pages = (int(total or 0) + per_page - 1) // per_page if per_page else 0

    return {
        "data": data,
        "total": int(total or 0),
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
    repository = CapacityDatabasesRepository()
    filters = DatabaseAggregationsSummaryFilters(
        instance_id=params.instance_id,
        db_type=params.db_type,
        database_name=params.database_name,
        database_id=params.database_id,
        period_type=params.period_type,
        start_date=params.start_date,
        end_date=params.end_date,
    )
    total_databases, total_instances, total_size_mb, avg_size_mb, max_size_mb = (
        repository.summarize_latest_aggregations(filters)
    )
    return {
        "total_databases": int(total_databases or 0),
        "total_instances": int(total_instances or 0),
        "total_size_mb": int(total_size_mb or 0),
        "avg_size_mb": float(avg_size_mb or 0),
        "max_size_mb": int(max_size_mb or 0),
        "growth_rate": 0,
    }
