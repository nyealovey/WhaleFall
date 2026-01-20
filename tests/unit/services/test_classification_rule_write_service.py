from types import SimpleNamespace

import pytest

from app.core.exceptions import ValidationError
from app.models.account_classification import ClassificationRule
from app.models.instance_database import InstanceDatabase  # noqa: F401
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService


class _StubAccountsClassificationsRepository(AccountsClassificationsRepository):
    @staticmethod
    def add_rule(rule: ClassificationRule) -> ClassificationRule:
        return rule


@pytest.mark.unit
def test_validate_accepts_builtin_db_types(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    payload = {
        "rule_name": "pg_rule",
        "classification_id": 1,
        "db_type": "PG",
        "operator": "OR",
        "rule_expression": {
            "version": 4,
            "expr": {"fn": "has_role", "args": {"name": "admin"}},
        },
    }

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_rule_name_exists",
        staticmethod(lambda *, classification_id, db_type, rule_name, resource: False),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_expression_exists",
        staticmethod(lambda normalized_expression, *, classification_id, resource: False),
        raising=False,
    )

    rule = service.create_rule(payload)
    assert rule.db_type == "postgresql"


@pytest.mark.unit
def test_validate_blocks_duplicate_rules(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_get_db_type_options",
        lambda self: [{"value": "mysql"}],
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_rule_name_exists",
        staticmethod(lambda *, classification_id, db_type, rule_name, resource: True),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_expression_exists",
        staticmethod(lambda normalized_expression, *, classification_id, resource: False),
        raising=False,
    )

    payload = {
        "rule_name": "dup",
        "classification_id": 1,
        "db_type": "mysql",
        "operator": "AND",
        "rule_expression": {
            "version": 4,
            "expr": {"fn": "has_role", "args": {"name": "admin"}},
        },
    }

    with pytest.raises(ValidationError) as exc:
        service.create_rule(payload)

    assert exc.value.message_key == "NAME_EXISTS"


@pytest.mark.unit
def test_update_rule_does_not_overwrite_is_active_when_missing(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_rule_name_exists",
        staticmethod(lambda *, classification_id, db_type, rule_name, resource: False),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_expression_exists",
        staticmethod(lambda normalized_expression, *, classification_id, resource: False),
        raising=False,
    )

    existing = ClassificationRule(
        classification_id=1,
        db_type="postgresql",
        rule_name="old_rule",
        rule_expression='{"version":4,"expr":{"fn":"is_superuser","args":{}}}',
        is_active=False,
    )
    existing.id = 1
    existing.rule_group_id = "group-1"
    existing.rule_version = 1

    updated = service.update_rule(
        existing,
        {
            "rule_name": "new_rule",
            "classification_id": 1,
            "db_type": "postgresql",
            "operator": "OR",
        },
    )

    assert updated is existing
    assert existing.rule_name == "new_rule"
    assert existing.is_active is False
    assert existing.superseded_at is None


@pytest.mark.unit
def test_update_rule_blocks_classification_change(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_rule_name_exists",
        staticmethod(lambda *, classification_id, db_type, rule_name, resource: False),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_expression_exists",
        staticmethod(lambda normalized_expression, *, classification_id, resource: False),
        raising=False,
    )

    existing = ClassificationRule(
        classification_id=1,
        db_type="postgresql",
        rule_name="old_rule",
        rule_expression='{"version":4,"expr":{"fn":"is_superuser","args":{}}}',
        is_active=True,
    )
    existing.id = 1
    existing.rule_group_id = "group-1"
    existing.rule_version = 1

    with pytest.raises(ValidationError) as exc:
        service.update_rule(
            existing,
            {
                "rule_name": "new_rule",
                "classification_id": 2,
                "db_type": "postgresql",
                "operator": "OR",
            },
        )

    assert exc.value.message_key == "FORBIDDEN"


@pytest.mark.unit
def test_update_rule_blocks_db_type_change(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_rule_name_exists",
        staticmethod(lambda *, classification_id, db_type, rule_name, resource: False),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_expression_exists",
        staticmethod(lambda normalized_expression, *, classification_id, resource: False),
        raising=False,
    )

    existing = ClassificationRule(
        classification_id=1,
        db_type="postgresql",
        rule_name="old_rule",
        rule_expression='{"version":4,"expr":{"fn":"is_superuser","args":{}}}',
        is_active=True,
    )
    existing.id = 1
    existing.rule_group_id = "group-1"
    existing.rule_version = 1

    with pytest.raises(ValidationError) as exc:
        service.update_rule(
            existing,
            {
                "rule_name": "new_rule",
                "classification_id": 1,
                "db_type": "mysql",
                "operator": "OR",
            },
        )

    assert exc.value.message_key == "FORBIDDEN"


@pytest.mark.unit
def test_update_rule_does_not_create_new_version_when_expression_is_same(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_rule_name_exists",
        staticmethod(lambda *, classification_id, db_type, rule_name, resource: False),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_expression_exists",
        staticmethod(lambda normalized_expression, *, classification_id, resource: False),
        raising=False,
    )

    existing = ClassificationRule(
        classification_id=1,
        db_type="postgresql",
        rule_name="old_rule",
        rule_expression='{"expr":{"args":[{"args":{},"fn":"is_superuser"}],"op":"OR"},"version":4}',
        is_active=True,
    )
    existing.id = 1
    existing.rule_group_id = "group-1"
    existing.rule_version = 1

    updated = service.update_rule(
        existing,
        {
            "rule_name": "old_rule",
            "classification_id": 1,
            "db_type": "postgresql",
            "operator": "OR",
            "rule_expression": {"version": 4, "expr": {"op": "OR", "args": [{"fn": "is_superuser", "args": {}}]}},
        },
    )

    assert updated is existing
    assert existing.rule_version == 1
    assert existing.superseded_at is None


@pytest.mark.unit
def test_update_rule_creates_new_version_when_expression_changes(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_rule_name_exists",
        staticmethod(lambda *, classification_id, db_type, rule_name, resource: False),
        raising=False,
    )
    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_expression_exists",
        staticmethod(lambda normalized_expression, *, classification_id, resource: False),
        raising=False,
    )

    existing = ClassificationRule(
        classification_id=1,
        db_type="postgresql",
        rule_name="old_rule",
        rule_expression='{"expr":{"args":[{"args":{},"fn":"is_superuser"}],"op":"OR"},"version":4}',
        is_active=True,
    )
    existing.id = 1
    existing.rule_group_id = "group-1"
    existing.rule_version = 1

    updated = service.update_rule(
        existing,
        {
            "rule_name": "old_rule",
            "classification_id": 1,
            "db_type": "postgresql",
            "operator": "AND",
            "rule_expression": {"version": 4, "expr": {"op": "AND", "args": [{"fn": "is_superuser", "args": {}}]}},
        },
    )

    assert updated is not existing
    assert updated.rule_group_id == "group-1"
    assert updated.rule_version == 2
    assert existing.is_active is False
    assert existing.superseded_at is not None
