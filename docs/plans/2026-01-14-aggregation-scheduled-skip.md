# Aggregation Scheduled Skip Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix scheduled aggregation job false-positive "all periods already aggregated" by adopting Plan A: only skip when the target period is aggregated for all active instances.

**Architecture:** Tighten the "has_aggregation_for_period" predicate to require full active-instance coverage for both instance-level and database-level aggregation tables. Add unit tests that reproduce the partial-coverage false positive and validate the corrected behavior.

**Tech Stack:** Python, Flask, SQLAlchemy, pytest(`-m unit`), Ruff, Pyright.

---

### Task 1: Add failing unit test for partial coverage

**Files:**
- Create: `tests/unit/services/test_aggregation_tasks_read_service_period_completeness.py`

**Step 1: Write failing test (partial coverage must not be treated as completed)**

```python
from __future__ import annotations

from datetime import date

import pytest

from app.services.aggregation.aggregation_tasks_read_service import AggregationTasksReadService


@pytest.mark.unit
def test_has_aggregation_for_period_requires_all_active_instances(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AggregationTasksReadService()

    # Two active instances exist, but only one is aggregated -> should be treated as NOT completed.
    monkeypatch.setattr(service, "count_active_instances", lambda: 2)

    # Simulate the old behavior: "any record exists" => True (this is the bug we are fixing).
    monkeypatch.setattr(service._aggregation_repository, "has_aggregation_for_period", lambda **_: True)

    # Simulate the new completeness signals (Plan A): only 1 instance covered.
    monkeypatch.setattr(
        service._aggregation_repository,
        "count_active_instances_with_database_size_aggregation",
        lambda **_: 1,
        raising=False,
    )
    monkeypatch.setattr(
        service._aggregation_repository,
        "count_active_instances_with_instance_size_aggregation",
        lambda **_: 1,
        raising=False,
    )

    assert service.has_aggregation_for_period(period_type="weekly", period_start=date(2026, 1, 5)) is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_aggregation_tasks_read_service_period_completeness.py -v`
Expected: FAIL (current implementation returns True for partial coverage)

---

### Task 2: Implement Plan A completeness check

**Files:**
- Modify: `app/services/aggregation/aggregation_tasks_read_service.py`
- Modify: `app/repositories/aggregation_repository.py`

**Step 1: Implement active-instance coverage checks**

- In `AggregationRepository`, add two count helpers:
  - `count_active_instances_with_database_size_aggregation(period_type, period_start)`
  - `count_active_instances_with_instance_size_aggregation(period_type, period_start)`
- In `AggregationTasksReadService.has_aggregation_for_period`, compare:
  - `expected_instances = count_active_instances()`
  - `database_aggregated_instances >= expected_instances`
  - `instance_aggregated_instances >= expected_instances`

**Step 2: Run the unit test to verify it passes**

Run: `uv run pytest -m unit tests/unit/services/test_aggregation_tasks_read_service_period_completeness.py -v`
Expected: PASS

---

### Task 3: Add passing unit test for full coverage

**Files:**
- Modify: `tests/unit/services/test_aggregation_tasks_read_service_period_completeness.py`

**Step 1: Add test for full coverage**

- Stub both aggregated counts to match `expected_instances`.
- Expect `has_aggregation_for_period(...)` returns True.

**Step 2: Run tests**

Run: `uv run pytest -m unit tests/unit/services/test_aggregation_tasks_read_service_period_completeness.py -v`
Expected: PASS

---

### Task 4: Verify minimal regression surface

Run: `uv run pytest -m unit`
Expected: PASS
