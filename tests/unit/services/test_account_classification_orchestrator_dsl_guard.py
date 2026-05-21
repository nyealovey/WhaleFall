from typing import Any, cast

import pytest

from app.core.exceptions import ValidationError
from app.core.types.account_scope import AccountScope
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

    assert AccountClassificationService()._evaluate_rule(cast(Any, _StubAccount()), cast(Any, _StubRule())) is True


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
        AccountClassificationService()._evaluate_rule(cast(Any, _StubAccount()), cast(Any, _StubRule()))


@pytest.mark.unit
def test_orchestrator_scoped_auto_classify_cleans_only_selected_accounts() -> None:
    class _StubRule:
        id = 7
        classification_id = 3
        db_type = "sqlserver"
        rule_name = "sysadmin"

        @staticmethod
        def get_rule_expression() -> dict:
            return {
                "version": 4,
                "expr": {"fn": "has_capability", "args": {"name": "SUPERUSER"}},
            }

    class _StubAccount:
        id = 42
        instance = type("_Instance", (), {"db_type": "sqlserver"})()
        permission_facts = {"capabilities": ["SUPERUSER"]}

    class _StubRepository:
        cleaned_account_ids: list[int] = []

        def fetch_active_rules(self) -> list[_StubRule]:
            return [_StubRule()]

        @staticmethod
        def serialize_rules(rules: list[_StubRule]) -> list[dict]:
            del rules
            return []

        def fetch_accounts(self, instance_id=None, *, account_scope=None):
            assert instance_id is None
            assert account_scope == AccountScope(owner_type="sqlserver_ag", owner_id=9)
            return [_StubAccount()]

        def cleanup_all_assignments(self) -> int:
            raise AssertionError("scoped auto classify must not clean all assignments")

        def cleanup_assignments_for_accounts(self, account_ids) -> int:
            self.cleaned_account_ids = list(account_ids)
            return len(self.cleaned_account_ids)

        def upsert_assignments(self, matched_accounts, classification_id, *, rule_id=None) -> int:
            assert classification_id == 3
            assert rule_id == 7
            return len(matched_accounts)

    class _StubCache:
        @staticmethod
        def get_rules() -> list[dict]:
            return []

        @staticmethod
        def set_rules(rules: list[dict]) -> None:
            del rules

    repository = _StubRepository()
    result = AccountClassificationService(repository=cast(Any, repository), cache_backend=cast(Any, _StubCache())).auto_classify_accounts(
        account_scope=AccountScope(owner_type="sqlserver_ag", owner_id=9),
    )

    assert result["success"] is True
    assert repository.cleaned_account_ids == [42]
