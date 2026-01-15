import pytest

from app.schemas.internal_contracts.type_specific_v1 import normalize_type_specific_v1


@pytest.mark.unit
def test_normalize_type_specific_v1_injects_version() -> None:
    raw = {"host": "localhost"}
    normalized = normalize_type_specific_v1(raw)
    assert normalized["version"] == 1
    assert normalized["host"] == "localhost"

