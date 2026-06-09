from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from app.services.alerts.alert_event_candidates import DatabaseCapacityGrowthCandidate


@dataclass(slots=True)
class _Baseline:
    size_mb: int
    collected_date: date


@pytest.mark.unit
def test_database_capacity_growth_candidate_builds_payload_when_thresholds_match() -> None:
    candidate = DatabaseCapacityGrowthCandidate.from_row(
        row={
            "instance_id": "1",
            "instance_name": "prod-mysql-1",
            "database_name": " orders ",
            "size_mb": 145 * 1024,
            "collected_date": date(2026, 3, 17),
        },
        baseline=_Baseline(size_mb=100 * 1024, collected_date=date(2026, 3, 15)),
        percent_threshold=30,
        absolute_gb_threshold=20,
        lookback_days=3,
    )

    assert candidate is not None
    assert candidate.dedupe_key == "1:orders"
    assert candidate.payload_json() == {
        "instance_id": 1,
        "instance_name": "prod-mysql-1",
        "database_name": "orders",
        "current_size_mb": 145 * 1024,
        "baseline_size_mb": 100 * 1024,
        "size_change_mb": 45 * 1024,
        "size_change_percent": 45.0,
        "baseline_collected_date": "2026-03-15",
        "baseline_age_days": 2,
        "current_collected_date": "2026-03-17",
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("row", "baseline"),
    [
        ({"instance_id": 1, "database_name": "orders", "size_mb": 120, "collected_date": date(2026, 3, 17)}, None),
        ({"instance_id": 1, "database_name": "orders", "size_mb": 120, "collected_date": date(2026, 3, 17)}, _Baseline(0, date(2026, 3, 15))),
        ({"instance_id": 1, "database_name": "orders", "size_mb": 100, "collected_date": date(2026, 3, 17)}, _Baseline(120, date(2026, 3, 15))),
        ({"instance_id": 1, "database_name": "", "size_mb": 120, "collected_date": date(2026, 3, 17)}, _Baseline(100, date(2026, 3, 15))),
        ({"instance_id": 1, "database_name": "orders", "size_mb": 120, "collected_date": None}, _Baseline(100, date(2026, 3, 15))),
    ],
)
def test_database_capacity_growth_candidate_skips_invalid_or_non_growth_rows(row, baseline) -> None:
    assert (
        DatabaseCapacityGrowthCandidate.from_row(
            row=row,
            baseline=baseline,
            percent_threshold=30,
            absolute_gb_threshold=20,
            lookback_days=3,
        )
        is None
    )
