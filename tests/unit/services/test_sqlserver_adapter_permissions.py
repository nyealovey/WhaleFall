from typing import cast

import pytest

from app.services.accounts_sync.adapters.sqlserver_adapter import SQLServerAccountAdapter


@pytest.mark.unit
def test_aggregate_database_permissions_writes_entries():
    """验证数据库权限聚合能将权限写入结果结构."""
    adapter = SQLServerAccountAdapter()

    usernames = ["CHINTCrm"]
    role_rows: list[tuple] = []
    permission_rows = [
        ("ECDATA", "CONNECT", 10, None, None, "DATABASE", None, None, None),
        ("ECDATA", "SELECT", 10, None, None, "OBJECT", "dbo", "table1", None),
        ("ECDATA", "UPDATE", 10, None, 1, "COLUMN", "dbo", "table1", "col1"),
    ]
    principal_lookup = {"ECDATA": {10: ["CHINTCrm"]}}

    result = adapter._aggregate_database_permissions(
        usernames,
        role_rows,
        permission_rows,
        principal_lookup,
    )

    typed_result = cast(dict[str, dict[str, dict[str, dict[str, list[str]]]]], result)

    class PermissionScopes(dict):
        database: list[str]
        table: dict[str, list[str]]
        column: dict[str, list[str]]

    permissions = cast(PermissionScopes, typed_result["CHINTCrm"]["permissions"]["ECDATA"])
    assert permissions["database"] == ["CONNECT"]
    assert permissions["table"]["dbo.table1"] == ["SELECT"]
    assert permissions["column"]["dbo.table1.col1"] == ["UPDATE"]


@pytest.mark.unit
def test_get_all_users_database_permissions_batch_uses_database_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证数据库权限批量查询会按 batch_size 分批执行."""
    adapter = SQLServerAccountAdapter()

    database_list = [f"DB{i}" for i in range(41)]
    monkeypatch.setattr(adapter, "_get_accessible_databases", lambda _conn: database_list)
    monkeypatch.setattr(adapter, "_map_sids_to_logins", lambda _conn, _usernames: ({b"\x01": ["user1"]}, '["0x01"]'))
    monkeypatch.setattr(adapter, "_is_permissions_empty", lambda _result: False)

    batch_sizes: list[int] = []

    def fake_build_database_permission_queries(database_batch: list[str]) -> tuple[str, str, str]:
        batch_sizes.append(len(database_batch))
        return "P", "R", "M"

    monkeypatch.setattr(adapter, "_build_database_permission_queries", fake_build_database_permission_queries)

    fetch_calls = 0

    def fake_fetch_principal_data(
        _conn: object,
        _principal_sql: str,
        _roles_sql: str,
        _perms_sql: str,
        sid_payload: str,
    ) -> tuple[list[tuple], list[tuple], list[tuple]]:
        nonlocal fetch_calls
        fetch_calls += 1
        assert sid_payload == '["0x01"]'
        return [], [], []

    monkeypatch.setattr(adapter, "_fetch_principal_data", fake_fetch_principal_data)

    result = adapter._get_all_users_database_permissions_batch(object(), ["user1"])
    assert batch_sizes == [20, 20, 1]
    assert fetch_calls == 3
    assert result["user1"]["roles"] == {}
    assert result["user1"]["permissions"] == {}


class _DummySQLServerConnection:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows
        self.last_sql: str | None = None
        self.last_params: object = None

    def execute_query(self, sql: str, params: object = None) -> list[tuple]:
        self.last_sql = sql
        self.last_params = params
        return self._rows


@pytest.mark.unit
def test_fetch_raw_accounts_collects_sqlserver_login_status_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = SQLServerAccountAdapter()
    monkeypatch.setattr(adapter.filter_manager, "get_filter_rules", lambda _db: {})

    class _DummyInstance:
        name = "inst"

    conn = _DummySQLServerConnection(
        [
            ("login1", "SQL_LOGIN", 0, 0, "DENY", 1, 0, 1, 0, 1),
        ],
    )

    accounts = adapter._fetch_raw_accounts(_DummyInstance(), conn)
    assert len(accounts) == 1

    type_specific = cast(dict[str, object], accounts[0]["permissions"]["type_specific"])
    assert type_specific["is_disabled"] is False
    assert type_specific["connect_to_engine"] == "DENY"
    assert type_specific["password_policy_enforced"] is True
    assert type_specific["password_expiration_enforced"] is False
    assert type_specific["is_locked_out"] is True
    assert type_specific["is_password_expired"] is False
    assert type_specific["must_change_password"] is True


@pytest.mark.unit
def test_normalize_account_does_not_infer_sqlserver_is_locked_from_type_specific() -> None:
    adapter = SQLServerAccountAdapter()

    normalized = adapter._normalize_account(
        object(),
        {
            "username": "login1",
            "is_superuser": False,
            "permissions": {
                "type_specific": {
                    "is_disabled": False,
                    "connect_to_engine": "DENY",
                },
            },
        },
    )

    assert normalized["is_locked"] is False


@pytest.mark.unit
def test_normalize_account_does_not_infer_sqlserver_is_locked_from_is_disabled() -> None:
    adapter = SQLServerAccountAdapter()

    normalized = adapter._normalize_account(
        object(),
        {
            "username": "login1",
            "is_superuser": False,
            "permissions": {
                "type_specific": {
                    "is_disabled": True,
                },
            },
        },
    )

    assert normalized["is_locked"] is False
