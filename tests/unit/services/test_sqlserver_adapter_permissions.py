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
