"""Period calculation utilities used by aggregation services."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import TYPE_CHECKING

from app.utils.time_utils import time_utils

VALID_PERIODS = {"daily", "weekly", "monthly", "quarterly"}


if TYPE_CHECKING:
    from collections.abc import Callable


class PeriodCalculator:
    """负责计算不同统计周期的日期范围.

    支持日、周、月、季度四种统计周期,提供当前周期、上一周期和前一周期的日期范围计算.

    Attributes:
        _now_func: 时间提供函数,用于获取当前日期,可在测试时注入.

    """

    def __init__(self, now_func: Callable[[], date] | None = None) -> None:
        """初始化周期计算器.

        Args:
            now_func: 可选的时间提供函数,默认使用中国时区的当前日期.

        """
        # 允许在测试时注入时间提供者
        self._now_func = now_func or (lambda: time_utils.now_china().date())

    def today(self) -> date:
        """获取当前日期.

        Returns:
            当前日期对象.

        """
        return self._now_func()

    def get_last_period(self, period_type: str) -> tuple[date, date]:
        """获取上一周期的开始和结束日期.

        Args:
            period_type: 周期类型,可选值:'daily'、'weekly'、'monthly'、'quarterly'.

        Returns:
            包含开始日期和结束日期的元组.

        Raises:
            ValueError: 当周期类型不支持时抛出.

        Example:
            >>> calc = PeriodCalculator()
            >>> start, end = calc.get_last_period('weekly')
            >>> print(f"{start} to {end}")

        """
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

    def get_current_period(self, period_type: str) -> tuple[date, date]:
        """获取当前周期的自然起止日期.

        注意:period_end 指向该周期的自然结束日,可能晚于今天.

        Args:
            period_type: 周期类型,可选值:'daily'、'weekly'、'monthly'、'quarterly'.

        Returns:
            包含开始日期和结束日期的元组.

        Raises:
            ValueError: 当周期类型不支持时抛出.

        """
        normalized = self._normalize(period_type)
        today = self.today()

        if normalized == "daily":
            return today, today
        if normalized == "weekly":
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            return start_date, end_date
        if normalized == "monthly":
            start_date = date(today.year, today.month, 1)
            end_day = monthrange(today.year, today.month)[1]
            end_date = date(today.year, today.month, end_day)
            return start_date, end_date
        # quarterly
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = date(today.year, quarter_start_month, 1)
        end_month = quarter_start_month + 2
        end_day = monthrange(today.year, end_month)[1]
        end_date = date(today.year, end_month, end_day)
        return start_date, end_date

    def get_previous_period(self, period_type: str, start_date: date, end_date: date) -> tuple[date, date]:
        """根据当前周期起止日期推算上一周期范围.

        Args:
            period_type: 周期类型,可选值:'daily'、'weekly'、'monthly'、'quarterly'.
            start_date: 当前周期开始日期.
            end_date: 当前周期结束日期.

        Returns:
            包含上一周期开始日期和结束日期的元组.

        Raises:
            ValueError: 当周期类型不支持时抛出.

        """
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

        msg = f"不支持的周期类型: {period_type!r}"
        raise ValueError(msg)

    def _normalize(self, period_type: str) -> str:
        """规范化周期类型字符串.

        Args:
            period_type: 周期类型字符串.

        Returns:
            小写的周期类型字符串.

        Raises:
            ValueError: 当周期类型不在支持列表中时抛出.

        """
        normalized = (period_type or "").lower()
        if normalized not in VALID_PERIODS:
            msg = f"不支持的周期类型: {period_type!r}"
            raise ValueError(msg)
        return normalized


__all__ = ["PeriodCalculator"]
