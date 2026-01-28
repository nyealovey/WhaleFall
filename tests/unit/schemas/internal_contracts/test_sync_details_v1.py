import pytest

from app.schemas.internal_contracts.sync_details_v1 import normalize_sync_details_v1


@pytest.mark.unit
def test_normalize_sync_details_v1_rejects_missing_version() -> None:
    raw = {"inventory": {"created": 1}}
    with pytest.raises(ValueError):
        normalize_sync_details_v1(raw)
