import pytest

from app.core.exceptions import ValidationError
from app.models.account_classification import AccountClassification
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService


class _StubAccountsClassificationsRepository(AccountsClassificationsRepository):
    @staticmethod
    def add_classification(classification: AccountClassification) -> AccountClassification:
        return classification


@pytest.mark.unit
def test_create_classification_flags_duplicate_code(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_code_exists",
        lambda self, code, resource: True,
        raising=False,
    )

    with pytest.raises(ValidationError) as exc:
        service.create_classification(
            {
                "code": "demo",
                "display_name": "高风险",
                "description": "",
                "risk_level": 1,
                "icon_name": "fa-shield-alt",
                "priority": 10,
            },
        )

    assert exc.value.message_key == "NAME_EXISTS"


@pytest.mark.unit
def test_create_classification_succeeds(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_code_exists",
        lambda self, code, resource: False,
        raising=False,
    )

    classification = service.create_classification(
        {
            "code": "low_risk",
            "display_name": "低风险",
            "description": "测试",
            "risk_level": 6,
            "icon_name": "fa-tag",
            "priority": 1,
        },
    )

    assert classification.code == "low_risk"
    assert classification.display_name == "低风险"
    assert classification.priority == 1


@pytest.mark.unit
def test_create_classification_rejects_non_integer_priority(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_code_exists",
        lambda self, code, resource: False,
        raising=False,
    )

    with pytest.raises(ValidationError) as exc:
        service.create_classification(
            {
                "code": "low_risk",
                "display_name": "低风险",
                "priority": "not-an-int",
            },
        )

    assert str(exc.value) == "优先级必须为整数"


@pytest.mark.unit
def test_update_classification_rejects_non_integer_priority(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_code_exists",
        lambda self, code, resource: False,
        raising=False,
    )

    classification = AccountClassification(
        code="low_risk",
        display_name="低风险",
        description="",
        risk_level=6,
        icon_name="fa-tag",
        priority=10,
    )

    with pytest.raises(ValidationError) as exc:
        service.update_classification(
            classification,
            {
                "priority": "not-an-int",
            },
        )

    assert str(exc.value) == "优先级必须为整数"


@pytest.mark.unit
def test_update_classification_rejects_code_change(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_code_exists",
        lambda self, code, resource: False,
        raising=False,
    )

    classification = AccountClassification(
        code="low_risk",
        display_name="低风险",
        description="",
        risk_level=6,
        icon_name="fa-tag",
        priority=10,
    )

    with pytest.raises(ValidationError) as exc:
        service.update_classification(
            classification,
            {
                "code": "NEW_CODE",
            },
        )

    assert exc.value.message_key == "FORBIDDEN"


@pytest.mark.unit
def test_update_classification_allows_display_name_change(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_code_exists",
        lambda self, code, resource: False,
        raising=False,
    )

    classification = AccountClassification(
        code="low_risk",
        display_name="低风险",
        description="",
        risk_level=6,
        icon_name="fa-tag",
        priority=10,
    )

    updated = service.update_classification(
        classification,
        {
            "display_name": "低风险(已改名)",
        },
    )

    assert updated.code == "low_risk"
    assert updated.display_name == "低风险(已改名)"


@pytest.mark.unit
def test_update_system_classification_rejects_risk_level_change(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_code_exists",
        lambda self, code, resource: False,
        raising=False,
    )

    classification = AccountClassification(
        code="super",
        display_name="超高风险",
        description="",
        risk_level=1,
        icon_name="fa-crown",
        priority=10,
        is_system=True,
    )

    with pytest.raises(ValidationError) as exc:
        service.update_classification(
            classification,
            {"risk_level": 2},
        )

    assert exc.value.message_key == "FORBIDDEN"
