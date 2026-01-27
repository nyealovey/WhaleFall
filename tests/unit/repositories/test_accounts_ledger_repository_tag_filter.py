from typing import Any, cast

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.ledgers import accounts_ledger_repository as accounts_ledger_repository_module
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository


@pytest.mark.unit
def test_apply_tag_filter_returns_original_query_when_join_fails(monkeypatch) -> None:
    class DummyQuery:
        def join(self, *_args: object, **_kwargs: object):
            raise SQLAlchemyError("boom")

    logged: list[tuple[str, dict[str, object]]] = []

    def _fake_log_warning(message: str, **kwargs: object) -> None:
        logged.append((message, dict(kwargs)))

    monkeypatch.setattr(accounts_ledger_repository_module, "log_warning", _fake_log_warning)

    query = DummyQuery()
    returned = AccountsLedgerRepository._apply_tag_filter(cast(Any, query), tags=["t1"])

    assert returned is query
    assert logged
    message, kwargs = logged[0]
    assert message == "标签过滤失败"
    assert kwargs.get("action") == "_apply_tag_filter"
    assert kwargs.get("tags") == ["t1"]
