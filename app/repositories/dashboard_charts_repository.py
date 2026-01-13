"""Dashboard 图表读模型 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func

from app import db
from app.models.sync_session import SyncSession
from app.utils.time_utils import CHINA_TZ, time_utils


class DashboardChartsRepository:
    """仪表板图表数据查询 Repository."""

    def fetch_sync_trend(self, *, days: int = 7) -> list[dict[str, int | str]]:
        """获取最近 N 天同步趋势数据."""
        window_days = max(1, min(int(days), 90))
        trend_data: list[dict[str, int | str]] = []

        end_date = time_utils.now_china().date()
        start_date = end_date - timedelta(days=window_days - 1)

        date_buckets: list[tuple[datetime, Any, Any]] = []
        for offset in range(window_days):
            day = start_date + timedelta(days=offset)
            start_dt = datetime(
                year=day.year,
                month=day.month,
                day=day.day,
                tzinfo=CHINA_TZ,
            )
            end_dt = start_dt + timedelta(days=1)
            start_utc = time_utils.to_utc(start_dt)
            end_utc = time_utils.to_utc(end_dt)
            if start_utc is None or end_utc is None:
                continue
            date_buckets.append((start_dt, start_utc, end_utc))

        if not date_buckets:
            return []

        select_columns = []
        labels: list[tuple[datetime, str]] = []
        for start_dt, start_utc, end_utc in date_buckets:
            label = f"sync_{time_utils.format_china_time(start_dt, '%Y%m%d')}"
            select_columns.append(
                func.sum(
                    case(
                        (
                            and_(
                                SyncSession.created_at >= start_utc,
                                SyncSession.created_at < end_utc,
                            ),
                            1,
                        ),
                        else_=0,
                    ),
                ).label(label),
            )
            labels.append((start_dt, label))

        if not select_columns:
            return []

        result = (
            db.session.query(*select_columns)
            .filter(
                SyncSession.created_at >= date_buckets[0][1],
                SyncSession.created_at < date_buckets[-1][2],
            )
            .one_or_none()
        )
        result_mapping: dict[str, Any] = {}
        if result is not None:
            label_keys = [label for _, label in labels]
            result_mapping = {label: getattr(result, label, 0) for label in label_keys}

        for start_dt, label in labels:
            trend_data.append(
                {
                    "date": time_utils.format_china_time(start_dt, "%Y-%m-%d"),
                    "count": int(result_mapping.get(label) or 0),
                },
            )

        return trend_data
