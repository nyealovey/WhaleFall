import pytest

from app.services.account_classification.orchestrator import AccountClassificationService


@pytest.mark.unit
def test_orchestrator_skips_dsl_v4_rules_when_flag_disabled() -> None:
    class _StubRule:
        id = 1
        db_type = "mysql"

        @staticmethod
        def get_rule_expression() -> dict:
            return {
                "version": 4,
                "expr": {
                    "op": "OR",
                    "args": [
                        {"fn": "has_privilege", "args": {"name": "SELECT", "scope": "global"}},
                    ],
                },
            }

    class _StubAccount:
        pass

    assert AccountClassificationService()._evaluate_rule(_StubAccount(), _StubRule()) is False


@pytest.mark.unit
def test_orchestrator_skips_legacy_rule_expressions() -> None:
    class _StubRule:
        db_type = "mysql"

        @staticmethod
        def get_rule_expression() -> dict:
            return {"operator": "OR", "global_privileges": ["SELECT"]}

    class _StubAccount:
        def get_permissions_by_db_type(self) -> dict[str, object]:
            return {"global_privileges": ["SELECT"]}

    assert AccountClassificationService()._evaluate_rule(_StubAccount(), _StubRule()) is False
