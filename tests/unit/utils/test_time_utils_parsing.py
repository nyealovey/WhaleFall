import pytest

from app.utils.time_utils import TimeUtils


@pytest.mark.unit
def test_to_china_invalid_iso_returns_none() -> None:
    assert TimeUtils.to_china("not-a-time") is None


@pytest.mark.unit
def test_format_china_time_invalid_returns_dash() -> None:
    assert TimeUtils.format_china_time("not-a-time") == "-"
