"""日志统计服务."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.repositories.log_statistics_repository import LogStatisticsRepository, LogTrendBucketSpec
from app.utils.structlog_config import log_error
from app.utils.time_utils import CHINA_TZ, time_utils

LOG_STATISTICS_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    ValueError,
    TypeError,
)


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
        china_today = time_utils.now_china().date()
        start_date = china_today - timedelta(days=days - 1)

        bucket_specs: list[LogTrendBucketSpec] = []
        labels: list[tuple[datetime, str, str]] = []
        for offset in range(days):
            day = start_date + timedelta(days=offset)
            start_dt = datetime(day.year, day.month, day.day, tzinfo=CHINA_TZ)
            end_dt = start_dt + timedelta(days=1)
            start_utc = time_utils.to_utc(start_dt)
            end_utc = time_utils.to_utc(end_dt)
            if start_utc is None or end_utc is None:
                continue
            suffix = time_utils.format_china_time(start_dt, "%Y%m%d")
            error_label = f"error_{suffix}"
            warning_label = f"warning_{suffix}"
            bucket_specs.append(
                LogTrendBucketSpec(
                    start_utc=start_utc,
                    end_utc=end_utc,
                    error_label=error_label,
                    warning_label=warning_label,
                ),
            )
            labels.append((start_dt, error_label, warning_label))

        if not bucket_specs:
            return []

        with db.session.begin_nested():
            result_mapping = LogStatisticsRepository.fetch_trend_counts(bucket_specs)

        for day, error_label, warning_label in labels:
            trend_data.append(
                {
                    "date": time_utils.format_china_time(day, "%Y-%m-%d"),
                    "error_count": int(result_mapping.get(error_label, 0) or 0),
                    "warning_count": int(result_mapping.get(warning_label, 0) or 0),
                },
            )

    except LOG_STATISTICS_EXCEPTIONS as exc:
        safe_exc = exc if isinstance(exc, Exception) else Exception(str(exc))
        log_error("获取日志趋势数据失败", module="log_statistics", exception=safe_exc)
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
        with db.session.begin_nested():
            level_stats = LogStatisticsRepository.fetch_level_distribution()
        return [{"level": stat.level.value, "count": stat.count} for stat in level_stats]
    except LOG_STATISTICS_EXCEPTIONS as exc:
        safe_exc = exc if isinstance(exc, Exception) else Exception(str(exc))
        log_error("获取日志级别分布失败", module="log_statistics", exception=safe_exc)
        return []
