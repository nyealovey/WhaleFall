import pytest

from app.errors import ValidationError
from app.models.account_classification import AccountClassification
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService


class _StubAccountsClassificationsRepository(AccountsClassificationsRepository):
    def add_classification(self, classification: AccountClassification) -> AccountClassification:
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
    assert classification.priority == 1
