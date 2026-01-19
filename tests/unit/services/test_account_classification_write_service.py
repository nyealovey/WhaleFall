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
def test_create_classification_flags_duplicate_name(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_name_exists",
        lambda self, name, resource: True,
        raising=False,
    )

    with pytest.raises(ValidationError) as exc:
        service.create_classification(
            {
                "name": "高风险",
                "description": "",
                "risk_level": "high",
                "color": "primary",
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
        "_name_exists",
        lambda self, name, resource: False,
        raising=False,
    )

    classification = service.create_classification(
        {
            "name": "低风险",
            "description": "测试",
            "risk_level": "low",
            "color": "info",
            "icon_name": "fa-tag",
            "priority": 1,
        },
    )

    assert classification.name == "低风险"
    assert classification.display_name == "低风险"
    assert classification.priority == 1


@pytest.mark.unit
def test_create_classification_rejects_non_integer_priority(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_name_exists",
        lambda self, name, resource: False,
        raising=False,
    )

    with pytest.raises(ValidationError) as exc:
        service.create_classification(
            {
                "name": "低风险",
                "priority": "not-an-int",
            },
        )

    assert str(exc.value) == "优先级必须为整数"


@pytest.mark.unit
def test_update_classification_rejects_non_integer_priority(monkeypatch) -> None:
    service = AccountClassificationsWriteService(repository=_StubAccountsClassificationsRepository())

    monkeypatch.setattr(
        AccountClassificationsWriteService,
        "_name_exists",
        lambda self, name, resource: False,
        raising=False,
    )

    classification = AccountClassification(
        name="低风险",
        description="",
        risk_level="low",
        color="info",
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
        "_name_exists",
        lambda self, name, resource: False,
        raising=False,
    )

    classification = AccountClassification(
        name="LOW_RISK",
        display_name="低风险",
        description="",
        risk_level="low",
        color="info",
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
        "_name_exists",
        lambda self, name, resource: False,
        raising=False,
    )

    classification = AccountClassification(
        name="LOW_RISK",
        display_name="低风险",
        description="",
        risk_level="low",
        color="info",
        icon_name="fa-tag",
        priority=10,
    )

    updated = service.update_classification(
        classification,
        {
            # 兼容旧前端：name 代表展示名
            "name": "低风险(已改名)",
        },
    )

    assert updated.name == "LOW_RISK"
    assert updated.display_name == "低风险(已改名)"
