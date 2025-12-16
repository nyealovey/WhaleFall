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

    result = adapter._aggregate_database_permissions(  # noqa: SLF001
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
