import pytest

from app.errors import ValidationError
from app.services.account_classification.orchestrator import AccountClassificationService


@pytest.mark.unit
def test_orchestrator_accepts_dsl_v4_rules() -> None:
    class _StubRule:
        db_type = "mysql"

        @staticmethod
        def get_rule_expression() -> dict:
            return {
                "version": 4,
                "expr": {"fn": "has_capability", "args": {"name": "SUPERUSER"}},
            }

    class _StubAccount:
        permission_facts = {"capabilities": ["SUPERUSER"]}

    assert AccountClassificationService()._evaluate_rule(_StubAccount(), _StubRule()) is True


@pytest.mark.unit
def test_orchestrator_rejects_legacy_rule_expressions() -> None:
    class _StubRule:
        db_type = "mysql"

        @staticmethod
        def get_rule_expression() -> dict:
            return {"operator": "OR", "global_privileges": ["SELECT"]}

    class _StubAccount:
        permission_facts = {}

    with pytest.raises(ValidationError):
        AccountClassificationService()._evaluate_rule(_StubAccount(), _StubRule())
