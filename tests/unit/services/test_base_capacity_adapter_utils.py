import pytest

from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter


@pytest.mark.unit
def test_safe_to_float_invalid_input_returns_zero() -> None:
    assert BaseCapacityAdapter._safe_to_float("not-a-number") == 0.0
    assert BaseCapacityAdapter._safe_to_float([]) == 0.0
