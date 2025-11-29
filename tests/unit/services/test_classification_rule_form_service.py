import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.form_service.classification_rule_service import ClassificationRuleFormService


@pytest.mark.unit
def test_validate_uses_dynamic_db_types(monkeypatch) -> None:
    service = ClassificationRuleFormService()

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
        ClassificationRuleFormService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )

    monkeypatch.setattr(
        ClassificationRuleFormService,
        "_rule_name_exists",
        lambda self, data, resource: False,
        raising=False,
    )
    monkeypatch.setattr(
        ClassificationRuleFormService,
        "_expression_exists",
        lambda self, expr, classification_id, resource: False,
        raising=False,
    )

    result = service.validate(payload, resource=None)
    assert result.success is True
    assert result.data["db_type"] == "mongodb"


@pytest.mark.unit
def test_validate_blocks_duplicate_rules(monkeypatch) -> None:
    service = ClassificationRuleFormService()

    monkeypatch.setattr(
        ClassificationRuleFormService,
        "_get_classification_by_id",
        lambda self, _: SimpleNamespace(id=1),
        raising=False,
    )
    monkeypatch.setattr(
        ClassificationRuleFormService,
        "_get_db_type_options",
        lambda self: [{"value": "mysql"}],
        raising=False,
    )
    monkeypatch.setattr(
        ClassificationRuleFormService,
        "_rule_name_exists",
        lambda self, data, resource: True,
        raising=False,
    )

    payload = {
        "rule_name": "dup",
        "classification_id": 1,
        "db_type": "mysql",
        "operator": "AND",
        "rule_expression": {"field": "env", "value": "prod"},
    }

    result = service.validate(payload, resource=None)
    assert result.success is False
    assert result.message_key == "NAME_EXISTS"
