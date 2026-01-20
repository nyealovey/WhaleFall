from types import SimpleNamespace

import pytest

from app.utils.query_filter_utils import build_classification_options


@pytest.mark.unit
def test_build_classification_options_prefers_display_name() -> None:
    classifications = [SimpleNamespace(id=1, code="prod", display_name="生产库")]

    options = build_classification_options(classifications)

    assert options[0]["value"] == "1"
    assert options[0]["label"] == "生产库"
