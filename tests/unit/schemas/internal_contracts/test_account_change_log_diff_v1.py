import pytest

from app.schemas.internal_contracts.account_change_log_diff_v1 import extract_diff_entries


@pytest.mark.unit
def test_extract_diff_entries_supports_legacy_list_shape() -> None:
    raw = [{"action": "GRANT", "object": "db"}]
    assert extract_diff_entries(raw) == raw


@pytest.mark.unit
def test_extract_diff_entries_supports_v1_dict_shape() -> None:
    raw = {"version": 1, "entries": [{"action": "GRANT", "object": "db"}]}
    assert extract_diff_entries(raw) == [{"action": "GRANT", "object": "db"}]

