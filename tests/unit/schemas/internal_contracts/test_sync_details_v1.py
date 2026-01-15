import pytest

from app.schemas.internal_contracts.sync_details_v1 import normalize_sync_details_v1


@pytest.mark.unit
def test_normalize_sync_details_v1_injects_version_when_missing() -> None:
    raw = {"inventory": {"created": 1}}
    normalized = normalize_sync_details_v1(raw)
    assert normalized is not None
    assert normalized["version"] == 1
    assert normalized["inventory"] == {"created": 1}
