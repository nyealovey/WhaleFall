"""日志统计服务."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func

from app import db
from app.models.unified_log import LogLevel, UnifiedLog
from app.utils.structlog_config import log_error
from app.utils.time_utils import CHINA_TZ, time_utils


def fetch_log_trend_data(*, days: int = 7) -> list[dict[str, int | str]]:
    """获取最近 N 天的错误/告警日志趋势.

    统计每天的错误和告警日志数量,返回时间序列数据.

    Args:
        days: 统计天数,默认为 7 天.

    Returns:
        日志趋势数据列表,每个元素包含日期、错误数和告警数,格式如下:
        [
            {
                'date': '2025-11-24',
                'error_count': 10,
                'warning_count': 5
            },
            ...
        ]
        查询失败时返回空列表.

    """
    trend_data: list[dict[str, int | str]] = []
    try:
        db.session.rollback()

        china_today = time_utils.now_china().date()
        start_date = china_today - timedelta(days=days - 1)

        date_buckets: list[tuple[datetime, Any, Any]] = []
        for offset in range(days):
            day = start_date + timedelta(days=offset)
            start_dt = datetime(day.year, day.month, day.day, tzinfo=CHINA_TZ)
            end_dt = start_dt + timedelta(days=1)
            start_utc = time_utils.to_utc(start_dt)
            end_utc = time_utils.to_utc(end_dt)
            if start_utc is None or end_utc is None:
                continue
            date_buckets.append((start_dt, start_utc, end_utc))

        if not date_buckets:
            return []

        select_columns = []
        labels: list[tuple[datetime, str, str]] = []
        for day, start_utc, end_utc in date_buckets:
            suffix = time_utils.format_china_time(day, "%Y%m%d")
            error_label = f"error_{suffix}"
            warning_label = f"warning_{suffix}"
            select_columns.append(
                func.sum(
                    case(
                        (
                            and_(
                                UnifiedLog.timestamp >= start_utc,
                                UnifiedLog.timestamp < end_utc,
                                UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL]),
                            ),
                            1,
                        ),
                        else_=0,
                    ),
                ).label(error_label),
            )
            select_columns.append(
                func.sum(
                    case(
                        (
                            and_(
                                UnifiedLog.timestamp >= start_utc,
                                UnifiedLog.timestamp < end_utc,
                                UnifiedLog.level == LogLevel.WARNING,
                            ),
                            1,
                        ),
                        else_=0,
                    ),
                ).label(warning_label),
            )
            labels.append((day, error_label, warning_label))

        if not select_columns:
            return []

        relevant_levels = [LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL]
        result = (
            db.session.query(*select_columns)
            .filter(
                UnifiedLog.timestamp >= date_buckets[0][1],
                UnifiedLog.timestamp < date_buckets[-1][2],
                UnifiedLog.level.in_(relevant_levels),
            )
            .one_or_none()
        )
        result_mapping: dict[str, Any] = {}
        if result is not None:
            result_mapping = dict(result._mapping)

        for day, error_label, warning_label in labels:
            trend_data.append(
                {
                    "date": time_utils.format_china_time(day, "%Y-%m-%d"),
                    "error_count": int(result_mapping.get(error_label) or 0),
                    "warning_count": int(result_mapping.get(warning_label) or 0),
                },
            )

    except Exception as exc:
        log_error("获取日志趋势数据失败", module="log_statistics", exception=exc)
        return []

    return trend_data


def fetch_log_level_distribution() -> list[dict[str, int | str]]:
    """统计错误/告警日志级别分布.

    统计各日志级别(ERROR、WARNING、CRITICAL)的数量.

    Returns:
        日志级别分布列表,每个元素包含级别和数量,格式如下:
        [
            {'level': 'ERROR', 'count': 100},
            {'level': 'WARNING', 'count': 50},
            {'level': 'CRITICAL', 'count': 5}
        ]
        查询失败时返回空列表.

    """
    try:
        db.session.rollback()

        level_stats = (
            db.session.query(UnifiedLog.level, db.func.count(UnifiedLog.id).label("count"))
            .filter(UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL]))
            .group_by(UnifiedLog.level)
            .all()
        )

        return [{"level": stat.level.value, "count": stat.count} for stat in level_stats]
    except Exception as exc:
        log_error("获取日志级别分布失败", module="log_statistics", exception=exc)
        return []
