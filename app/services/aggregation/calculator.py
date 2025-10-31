"""
Period calculation utilities used by aggregation services.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Tuple

from app.utils.time_utils import time_utils

VALID_PERIODS = {"daily", "weekly", "monthly", "quarterly"}


class PeriodCalculator:
    """负责计算不同统计周期的日期范围。"""

    def __init__(self, now_func=None) -> None:
        # 允许在测试时注入时间提供者
        self._now_func = now_func or (lambda: time_utils.now_china().date())

    def today(self) -> date:
        return self._now_func()

    def get_last_period(self, period_type: str) -> Tuple[date, date]:
        """获取上一周期的开始和结束日期。"""
        normalized = self._normalize(period_type)
        today = self.today()

        if normalized == "daily":
            previous_day = today - timedelta(days=1)
            return previous_day, previous_day
        if normalized == "weekly":
            days_since_monday = today.weekday()
            start_date = today - timedelta(days=days_since_monday + 7)
            end_date = start_date + timedelta(days=6)
            return start_date, end_date
        if normalized == "monthly":
            if today.month == 1:
                start_date = date(today.year - 1, 12, 1)
                end_date = date(today.year - 1, 12, 31)
            else:
                start_date = date(today.year, today.month - 1, 1)
                end_day = monthrange(today.year, today.month - 1)[1]
                end_date = date(today.year, today.month - 1, end_day)
            return start_date, end_date
        # quarterly
        current_quarter = (today.month - 1) // 3 + 1
        if current_quarter == 1:
            start_date = date(today.year - 1, 10, 1)
            end_date = date(today.year - 1, 12, 31)
        else:
            quarter_start_month = (current_quarter - 2) * 3 + 1
            start_date = date(today.year, quarter_start_month, 1)
            end_month = quarter_start_month + 2
            end_day = monthrange(today.year, end_month)[1]
            end_date = date(today.year, end_month, end_day)
        return start_date, end_date

    def get_current_period(self, period_type: str) -> Tuple[date, date]:
        """获取当前周期(包含至今天)的起止日期。"""
        normalized = self._normalize(period_type)
        today = self.today()

        if normalized == "daily":
            return today, today
        if normalized == "weekly":
            start_date = today - timedelta(days=today.weekday())
            return start_date, today
        if normalized == "monthly":
            start_date = date(today.year, today.month, 1)
            return start_date, today
        # quarterly
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = date(today.year, quarter_start_month, 1)
        return start_date, today

    def get_previous_period(self, period_type: str, start_date: date, end_date: date) -> Tuple[date, date]:
        """根据当前周期起止日期推算上一周期范围。"""
        normalized = self._normalize(period_type)

        if normalized == "daily":
            if start_date == end_date:
                prev_end = start_date - timedelta(days=1)
                return prev_end, prev_end
            duration = end_date - start_date
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - duration
            return prev_start, prev_end

        if normalized == "weekly":
            duration = end_date - start_date
            prev_end = start_date - timedelta(days=1)
            prev_start = prev_end - duration
            return prev_start, prev_end

        if normalized == "monthly":
            if start_date.month == 1:
                prev_start = date(start_date.year - 1, 12, 1)
                prev_end = date(start_date.year - 1, 12, 31)
            else:
                prev_start = date(start_date.year, start_date.month - 1, 1)
                prev_end = date(start_date.year, start_date.month, 1) - timedelta(days=1)
            return prev_start, prev_end

        if normalized == "quarterly":
            quarter = (start_date.month - 1) // 3 + 1
            if quarter == 1:
                prev_start = date(start_date.year - 1, 10, 1)
                prev_end = date(start_date.year - 1, 12, 31)
            else:
                prev_quarter_start_month = (quarter - 2) * 3 + 1
                prev_start = date(start_date.year, prev_quarter_start_month, 1)
                prev_end = date(start_date.year, prev_quarter_start_month + 2, 1) - timedelta(days=1)
            return prev_start, prev_end

        # fallback - treat as same duration sliding window
        duration = end_date - start_date
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - duration
        return prev_start, prev_end

    def _normalize(self, period_type: str) -> str:
        normalized = (period_type or "").lower()
        if normalized not in VALID_PERIODS:
            raise ValueError(f"Unsupported period type: {period_type!r}")
        return normalized


__all__ = ["PeriodCalculator"]
