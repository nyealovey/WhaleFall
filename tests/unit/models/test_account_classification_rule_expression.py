from types import SimpleNamespace

import pytest

from app.models.account_classification import ClassificationRule


@pytest.mark.unit
def test_get_rule_expression_invalid_json_is_not_silent_fallback() -> None:
    rule = SimpleNamespace(rule_expression="{not-json")
    with pytest.raises(ValueError):
        ClassificationRule.get_rule_expression(rule)  # type: ignore[arg-type]
