import pytest

from app.core.constants import DatabaseType
from app.models.instance import Instance
from app.services.accounts_sync.adapters.mysql_adapter import MySQLAccountAdapter


class _StubMySQLConnection:
    def __init__(
        self,
        *,
        user_rows: list[tuple],
        role_edges_rows: list[tuple] | None = None,
        default_roles_rows: list[tuple] | None = None,
    ) -> None:
        self._user_rows = list(user_rows)
        self._role_edges_rows = list(role_edges_rows or [])
        self._default_roles_rows = list(default_roles_rows or [])

    def execute_query(self, sql: str, params=None):  # type: ignore[no-untyped-def]
        sql_upper = sql.upper()

        if "FROM MYSQL.ROLE_EDGES" in sql_upper:
            return list(self._role_edges_rows)

        if "FROM MYSQL.DEFAULT_ROLES" in sql_upper:
            return list(self._default_roles_rows)

        if sql_upper.startswith("SHOW GRANTS FOR"):
            return [("GRANT USAGE ON *.* TO `demo`@`%`",)]

        if "FROM MYSQL.USER" in sql_upper and "ORDER BY USER, HOST" in sql_upper:
            return list(self._user_rows)

        if "FROM MYSQL.USER" in sql_upper and "WHERE USER = %S AND HOST = %S" in sql_upper:
            return [("N", "N", "N", "caching_sha2_password", None)]

        raise AssertionError(f"unexpected sql: {sql}")


@pytest.mark.unit
def test_mysql_adapter_fetch_raw_accounts_sets_account_kind_from_is_role() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        description=None,
        is_active=True,
    )

    connection = _StubMySQLConnection(
        user_rows=[
            ("demo", "%", "N", "N", "N", "caching_sha2_password", None, "N"),
            ("demo_role", "%", "N", "Y", "N", None, None, "Y"),
        ],
    )

    accounts = adapter._fetch_raw_accounts(instance, connection)

    assert {account["username"] for account in accounts} == {"demo@%", "demo_role@%"}
    kind_by_username = {
        account["username"]: account["permissions"]["type_specific"].get("account_kind") for account in accounts
    }
    assert kind_by_username == {"demo@%": "user", "demo_role@%": "role"}


@pytest.mark.unit
def test_mysql_adapter_enrich_permissions_includes_roles_direct_and_default() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        description=None,
        is_active=True,
    )

    connection = _StubMySQLConnection(
        user_rows=[],
        role_edges_rows=[("demo@%", "r1@%", 0)],
        default_roles_rows=[("demo@%", "r2@%")],
    )

    accounts = [
        {
            "username": "demo@%",
            "display_name": "demo@%",
            "db_type": DatabaseType.MYSQL,
            "is_superuser": False,
            "is_locked": False,
            "is_active": True,
            "permissions": {
                "global_privileges": [],
                "database_privileges": {},
                "type_specific": {
                    "host": "%",
                    "original_username": "demo",
                    "account_kind": "user",
                },
            },
        },
    ]

    enriched = adapter.enrich_permissions(instance, connection, accounts)

    permissions = enriched[0]["permissions"]
    assert permissions.get("roles") == {"direct": ["r1@%"], "default": ["r2@%"]}
    assert permissions.get("type_specific", {}).get("account_kind") == "user"
