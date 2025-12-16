import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.services.form_service.classification_service import ClassificationFormService


@pytest.mark.unit
def test_validate_flags_duplicate_name(monkeypatch) -> None:
    service = ClassificationFormService()

    monkeypatch.setattr(
        ClassificationFormService,
        "_name_exists",
        lambda self, name, resource: True,
        raising=False,
    )

    result = service.validate(
        {
            "name": "高风险",
            "description": "",
            "risk_level": "high",
            "color": "primary",
            "icon_name": "fa-shield-alt",
            "priority": 10,
        },
        resource=None,
    )

    assert result.success is False
    assert result.message_key == "NAME_EXISTS"


@pytest.mark.unit
def test_validate_sets_is_create_flag(monkeypatch) -> None:
    service = ClassificationFormService()

    monkeypatch.setattr(
        ClassificationFormService,
        "_name_exists",
        lambda self, name, resource: False,
        raising=False,
    )

    result = service.validate(
        {
            "name": "低风险",
            "description": "测试",
            "risk_level": "low",
            "color": "info",
            "icon_name": "fa-tag",
            "priority": 1,
        },
        resource=None,
    )

    assert result.success is True
    assert result.data is not None
    assert result.data["_is_create"] is True
