from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core.types.listing import PaginatedResult
from app.services.history_account_change_logs.history_account_change_logs_read_service import (
    HistoryAccountChangeLogsReadService,
)


@pytest.mark.unit
def test_list_logs_returns_minimal_message_and_no_diffs_for_add() -> None:
    class _Repository:
        @staticmethod
        def list_logs(_filters):  # type: ignore[no-untyped-def]
            log_entry = SimpleNamespace(
                id=1,
                instance_id=123,
                db_type="mysql",
                username="demo@%",
                change_type="add",
                status="success",
                message="账户 demo@% 新增账户,赋予 999 项权限;其他变更:数据库特性 从 a:b 调整为 a:c",
                change_time=None,
                session_id=None,
                privilege_diff={
                    "version": 1,
                    "entries": [
                        {"field": "roles", "label": "角色", "object": "x", "action": "GRANT", "permissions": ["p"]}
                    ],
                },
                other_diff={
                    "version": 1,
                    "entries": [
                        {
                            "field": "type_specific",
                            "label": "数据库特性",
                            "before": "a:b",
                            "after": "a:c",
                            "description": "x",
                        }
                    ],
                },
            )
            return PaginatedResult(
                items=[(log_entry, "inst-1", 42)],
                total=1,
                page=1,
                pages=1,
                limit=50,
            )

        @staticmethod
        def get_log(_log_id: int):  # type: ignore[no-untyped-def]
            raise AssertionError("not used")

    service = HistoryAccountChangeLogsReadService(repository=cast(Any, _Repository()))
    result = service.list_logs(
        cast(
            Any,
            SimpleNamespace(
                page=1,
                limit=50,
                sort_field="change_time",
                sort_order="desc",
                search_term="",
                instance_id=None,
                db_type=None,
                change_type=None,
                status=None,
                hours=None,
            ),
        ),
    )

    assert result.items[0].message == "新增账户"
    assert result.items[0].privilege_diff_count == 0
    assert result.items[0].other_diff_count == 0


@pytest.mark.unit
def test_get_log_detail_returns_minimal_payload_for_add() -> None:
    class _Repository:
        @staticmethod
        def list_logs(_filters):  # type: ignore[no-untyped-def]
            raise AssertionError("not used")

        @staticmethod
        def get_log(_log_id: int):  # type: ignore[no-untyped-def]
            return SimpleNamespace(
                id=1,
                instance_id=123,
                db_type="mysql",
                username="demo@%",
                change_type="add",
                status="success",
                message="账户 demo@% 新增账户,赋予 999 项权限;其他变更:数据库特性 从 a:b 调整为 a:c",
                change_time=None,
                session_id=None,
                privilege_diff={
                    "version": 1,
                    "entries": [
                        {"field": "roles", "label": "角色", "object": "x", "action": "GRANT", "permissions": ["p"]}
                    ],
                },
                other_diff={
                    "version": 1,
                    "entries": [
                        {
                            "field": "type_specific",
                            "label": "数据库特性",
                            "before": "a:b",
                            "after": "a:c",
                            "description": "x",
                        }
                    ],
                },
            )

    service = HistoryAccountChangeLogsReadService(repository=cast(Any, _Repository()))
    payload = service.get_log_detail(1)
    log = cast(Any, payload.get("log"))

    assert log["change_type"] == "add"
    assert log["message"] == "新增账户"
    assert log["privilege_diff"] == []
    assert log["other_diff"] == []
