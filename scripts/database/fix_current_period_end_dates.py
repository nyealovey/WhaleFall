"""
修复聚合表中当前周期记录的 period_end，使其指向周期自然结束日。

使用方法：
    uv run python scripts/database/fix_current_period_end_dates.py
"""

from __future__ import annotations

import sys
from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy.orm import joinedload

from app import create_app, db
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance_size_aggregation import InstanceSizeAggregation

SUPPORTED_PERIODS = ("weekly", "monthly", "quarterly")


def _expected_period_end(period_type: str, period_start: date) -> date:
    if period_type == "weekly":
        return period_start + timedelta(days=6)
    if period_type == "monthly":
        end_day = monthrange(period_start.year, period_start.month)[1]
        return date(period_start.year, period_start.month, end_day)
    if period_type == "quarterly":
        quarter_index = (period_start.month - 1) // 3
        end_month = quarter_index * 3 + 3
        end_day = monthrange(period_start.year, end_month)[1]
        return date(period_start.year, end_month, end_day)
    raise ValueError(f"Unsupported period type: {period_type}")


def _fix_model(model, label: str) -> int:
    updated = 0
    query = (
        model.query.options(joinedload(model.instance))
        if hasattr(model, "instance")
        else model.query
    )
    for aggregation in query.filter(model.period_type.in_(SUPPORTED_PERIODS)).yield_per(500):
        expected_end = _expected_period_end(aggregation.period_type, aggregation.period_start)
        if aggregation.period_end == expected_end:
            continue

        aggregation.period_end = expected_end
        updated += 1

    if updated:
        db.session.commit()
    return updated


def main() -> int:
    app = create_app()
    with app.app_context():
        db_updates = _fix_model(DatabaseSizeAggregation, "database")
        instance_updates = _fix_model(InstanceSizeAggregation, "instance")

        print(
            f"修复完成：database_size_aggregations 更新 {db_updates} 条，"
            f"instance_size_aggregations 更新 {instance_updates} 条"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
