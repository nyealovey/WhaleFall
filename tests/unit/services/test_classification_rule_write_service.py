from types import SimpleNamespace

import pytest

from app.errors import ValidationError
from app.models.account_classification import ClassificationRule
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService


class _StubAccountsClassificationsRepository(AccountsClassificationsRepository):
    def add_rule(self, rule: ClassificationRule) -> ClassificationRule:
        return rule


@pytest.mark.unit
def test_validate_uses_dynamic_db_types(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    from app.services import database_type_service

    monkeypatch.setattr(
        database_type_service.DatabaseTypeService,
        "get_active_types",
        staticmethod(lambda: [SimpleNamespace(name="mongodb", display_name="MongoDB")]),
    )

    payload = {
        "rule_name": "mongo_rule",
        "classification_id": 1,
        "db_type": "mongodb",
        "operator": "OR",
        "rule_expression": {"field": "env", "value": "prod"},
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
    assert rule.db_type == "mongodb"


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
        "rule_expression": {"field": "env", "value": "prod"},
    }

    with pytest.raises(ValidationError) as exc:
        service.create_rule(payload)

    assert exc.value.message_key == "NAME_EXISTS"
