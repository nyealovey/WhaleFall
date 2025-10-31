from datetime import date

import pytest

from app.services.aggregation.calculator import PeriodCalculator


@pytest.mark.unit
def test_get_current_period_weekly_returns_natural_week():
    calculator = PeriodCalculator(now_func=lambda: date(2024, 10, 31))

    start, end = calculator.get_current_period("weekly")

    assert start == date(2024, 10, 28)
    assert end == date(2024, 11, 3)


@pytest.mark.unit
def test_get_current_period_monthly_returns_month_end():
    calculator = PeriodCalculator(now_func=lambda: date(2024, 2, 15))

    start, end = calculator.get_current_period("monthly")

    assert start == date(2024, 2, 1)
    assert end == date(2024, 2, 29)  # 闰年


@pytest.mark.unit
def test_get_current_period_quarterly_returns_quarter_end():
    calculator = PeriodCalculator(now_func=lambda: date(2024, 10, 5))

    start, end = calculator.get_current_period("quarterly")

    assert start == date(2024, 10, 1)
    assert end == date(2024, 12, 31)
