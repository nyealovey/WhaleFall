"""日志统计 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, case, func

from app import db
from app.models.unified_log import LogLevel, UnifiedLog


@dataclass(frozen=True, slots=True)
class LogTrendBucketSpec:
    """日志趋势统计桶规格."""

    start_utc: datetime
    end_utc: datetime
    error_label: str
    warning_label: str


class LogStatisticsRepository:
    """日志统计读模型 Repository."""

    @staticmethod
    def fetch_trend_counts(bucket_specs: list[LogTrendBucketSpec]) -> dict[str, int]:
        """按桶规格统计趋势数量."""
        if not bucket_specs:
            return {}

        select_columns = []
        label_names: list[str] = []
        relevant_levels = [LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL]

        for bucket in bucket_specs:
            select_columns.append(
                func.sum(
                    case(
                        (
                            and_(
                                UnifiedLog.timestamp >= bucket.start_utc,
                                UnifiedLog.timestamp < bucket.end_utc,
                                UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL]),
                            ),
                            1,
                        ),
                        else_=0,
                    ),
                ).label(bucket.error_label),
            )
            select_columns.append(
                func.sum(
                    case(
                        (
                            and_(
                                UnifiedLog.timestamp >= bucket.start_utc,
                                UnifiedLog.timestamp < bucket.end_utc,
                                UnifiedLog.level == LogLevel.WARNING,
                            ),
                            1,
                        ),
                        else_=0,
                    ),
                ).label(bucket.warning_label),
            )
            label_names.extend([bucket.error_label, bucket.warning_label])

        result = (
            db.session.query(*select_columns)
            .filter(
                UnifiedLog.timestamp >= bucket_specs[0].start_utc,
                UnifiedLog.timestamp < bucket_specs[-1].end_utc,
                UnifiedLog.level.in_(relevant_levels),
            )
            .one_or_none()
        )
        if result is None:
            return {}
        return {label: int(getattr(result, label, 0) or 0) for label in label_names}

    @staticmethod
    def fetch_level_distribution() -> list[Any]:
        """统计日志等级分布."""
        return (
            db.session.query(UnifiedLog.level, db.func.count(UnifiedLog.id).label("count"))
            .filter(UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.WARNING, LogLevel.CRITICAL]))
            .group_by(UnifiedLog.level)
            .all()
        )
