from types import SimpleNamespace

import pytest

from app.models.database_type_config import DatabaseTypeConfig


@pytest.mark.unit
def test_features_list_invalid_json_is_not_silent_fallback() -> None:
    cfg = SimpleNamespace(features="[not-json")
    with pytest.raises(ValueError):
        _ = DatabaseTypeConfig.features_list.fget(cfg)  # type: ignore[arg-type]
