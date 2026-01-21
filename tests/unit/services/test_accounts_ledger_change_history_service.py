from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.services.ledgers.accounts_ledger_change_history_service import AccountsLedgerChangeHistoryService


@pytest.mark.unit
def test_get_change_history_strips_redundant_username_prefix_in_message() -> None:
    class _Repository:
        @staticmethod
        def get_account_by_instance_account_id(_account_id: int):  # type: ignore[no-untyped-def]
            return SimpleNamespace(username="demo@%", db_type="mysql", instance_id=123)

        @staticmethod
        def list_change_logs(*, instance_id: int, username: str, db_type: str):  # type: ignore[no-untyped-def]
            assert instance_id == 123
            assert username == "demo@%"
            assert db_type == "mysql"
            return [
                SimpleNamespace(
                    id=1,
                    change_type="modify_other",
                    change_time=None,
                    status="success",
                    message="账户 demo@% 权限更新:新增 1 项授权",
                    privilege_diff=None,
                    other_diff=None,
                    session_id=None,
                ),
            ]

    service = AccountsLedgerChangeHistoryService(repository=cast(Any, _Repository()))
    result = service.get_change_history(42)

    assert result.history[0].message == "权限更新:新增 1 项授权"

