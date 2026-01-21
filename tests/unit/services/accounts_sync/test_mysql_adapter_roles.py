from typing import cast

import pytest

from app.core.constants import DatabaseType
from app.core.types import RemoteAccount
from app.models.instance import Instance
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.accounts_sync.adapters.mysql_adapter import MySQLAccountAdapter


class _StubMySQLConnection:
    def __init__(
        self,
        *,
        user_rows: list[tuple],
        role_edges_rows: list[tuple] | None = None,
        default_roles_rows: list[tuple] | None = None,
        forbid_information_schema: bool = False,
        forbid_roles_tables: bool = False,
        forbid_is_role_column: bool = False,
    ) -> None:
        self._user_rows = list(user_rows)
        self._role_edges_rows = list(role_edges_rows or [])
        self._default_roles_rows = list(default_roles_rows or [])
        self._forbid_information_schema = bool(forbid_information_schema)
        self._forbid_roles_tables = bool(forbid_roles_tables)
        self._forbid_is_role_column = bool(forbid_is_role_column)
        self.queries: list[str] = []

    def execute_query(self, sql: str, _params=None):  # type: ignore[no-untyped-def]
        sql_upper = sql.upper()
        self.queries.append(sql_upper)

        result = None

        if "FROM INFORMATION_SCHEMA.COLUMNS" in sql_upper:
            if self._forbid_information_schema:
                raise AssertionError(f"information_schema query forbidden: {sql}")
            result = []

        elif "FROM MYSQL.ROLE_EDGES" in sql_upper:
            if self._forbid_roles_tables:
                raise AssertionError(f"roles tables query forbidden: {sql}")
            # role_edges_rows 按 mysql.role_edges 真实列顺序模拟：
            # FROM_USER / FROM_HOST / TO_USER / TO_HOST / WITH_ADMIN_OPTION
            uses_to_as_grantee = "CONCAT(TO_USER" in sql_upper
            output = []
            for from_user, from_host, to_user, to_host, with_admin_option in self._role_edges_rows:
                grantee_user, grantee_host = (to_user, to_host) if uses_to_as_grantee else (from_user, from_host)
                role_user, role_host = (from_user, from_host) if uses_to_as_grantee else (to_user, to_host)
                output.append((f"{grantee_user}@{grantee_host}", f"{role_user}@{role_host}", with_admin_option))
            result = output

        elif "FROM MYSQL.DEFAULT_ROLES" in sql_upper:
            if self._forbid_roles_tables:
                raise AssertionError(f"roles tables query forbidden: {sql}")
            # default_roles_rows 按 mysql.default_roles 真实列顺序模拟：
            # USER / HOST / DEFAULT_ROLE_USER / DEFAULT_ROLE_HOST
            result = [
                (f"{user}@{host}", f"{role_user}@{role_host}")
                for user, host, role_user, role_host in self._default_roles_rows
            ]

        elif sql_upper.startswith("SHOW GRANTS FOR"):
            result = [("GRANT USAGE ON *.* TO `demo`@`%`",)]

        elif "FROM MYSQL.USER" in sql_upper and "ORDER BY USER, HOST" in sql_upper:
            if self._forbid_is_role_column and "IS_ROLE" in sql_upper:
                raise ConnectionAdapterError("(1054, \"Unknown column 'is_role' in 'field list'\")")
            result = list(self._user_rows)

        elif "FROM MYSQL.USER" in sql_upper and "WHERE USER = %S AND HOST = %S" in sql_upper:
            result = [("N", "N", "N", "caching_sha2_password", None)]

        if result is None:
            raise AssertionError(f"unexpected sql: {sql}")
        return result


class _FailingConnection:
    def execute_query(self, _sql: str, _params=None):  # type: ignore[no-untyped-def]
        raise ConnectionAdapterError("boom")


@pytest.mark.unit
def test_mysql_adapter_fetch_raw_accounts_sets_account_kind_from_is_role() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        main_version="8.0",
        description=None,
        is_active=True,
    )

    connection = _StubMySQLConnection(
        forbid_information_schema=True,
        user_rows=[
            ("demo", "%", "N", "N", "N", "caching_sha2_password", None, "N"),
            ("demo_role", "%", "N", "Y", "N", None, None, "Y"),
        ],
    )

    accounts = adapter._fetch_raw_accounts(instance, connection)

    usernames: set[str] = set()
    kind_by_username: dict[str, str] = {}
    for account in accounts:
        username = account.get("username")
        assert isinstance(username, str)
        usernames.add(username)

        permissions = account.get("permissions")
        assert isinstance(permissions, dict)
        type_specific = permissions.get("type_specific")
        assert isinstance(type_specific, dict)

        account_kind = type_specific.get("account_kind")
        assert isinstance(account_kind, str)
        kind_by_username[username] = account_kind

    assert usernames == {"demo@%", "demo_role@%"}
    assert kind_by_username == {"demo@%": "user", "demo_role@%": "role"}


@pytest.mark.unit
def test_mysql_adapter_enrich_permissions_includes_roles_direct_and_default() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        main_version="8.0",
        description=None,
        is_active=True,
    )

    connection = _StubMySQLConnection(
        forbid_information_schema=True,
        user_rows=[],
        role_edges_rows=[("r1", "%", "demo", "%", 0)],
        default_roles_rows=[("demo", "%", "r2", "%")],
    )

    accounts = cast(
        list[RemoteAccount],
        [
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
        ],
    )

    enriched = adapter.enrich_permissions(instance, connection, accounts)

    permissions = enriched[0]["permissions"]
    assert permissions.get("roles") == {"direct": ["r1@%"], "default": ["r2@%"]}
    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)
    assert type_specific.get("account_kind") == "user"


@pytest.mark.unit
def test_mysql_adapter_enrich_permissions_includes_role_members_for_role_accounts() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        main_version="8.0",
        description=None,
        is_active=True,
    )

    # r1@% 被授予给 demo@%（直授）且也被配置为默认角色（default_roles）。
    connection = _StubMySQLConnection(
        forbid_information_schema=True,
        user_rows=[],
        role_edges_rows=[("r1", "%", "demo", "%", 0)],
        default_roles_rows=[("demo", "%", "r1", "%")],
    )

    accounts = cast(
        list[RemoteAccount],
        [
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
            {
                "username": "r1@%",
                "display_name": "r1@%",
                "db_type": DatabaseType.MYSQL,
                "is_superuser": False,
                "is_locked": False,
                "is_active": True,
                "permissions": {
                    "global_privileges": [],
                    "database_privileges": {},
                    "type_specific": {
                        "host": "%",
                        "original_username": "r1",
                        "account_kind": "role",
                    },
                },
            },
        ],
    )

    enriched = adapter.enrich_permissions(instance, connection, accounts)
    role_account = next(item for item in enriched if item.get("username") == "r1@%")
    role_permissions = role_account.get("permissions")
    assert isinstance(role_permissions, dict)

    assert role_permissions.get("role_members") == {"direct": ["demo@%"], "default": ["demo@%"]}

    user_account = next(item for item in enriched if item.get("username") == "demo@%")
    user_permissions = user_account.get("permissions")
    assert isinstance(user_permissions, dict)
    assert "role_members" not in user_permissions


@pytest.mark.unit
def test_mysql_adapter_fetch_raw_accounts_raises_on_query_failure() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        main_version="8.0",
        description=None,
        is_active=True,
    )

    with pytest.raises(ConnectionAdapterError):
        adapter._fetch_raw_accounts(instance, _FailingConnection())


@pytest.mark.unit
def test_mysql_adapter_does_not_assume_is_role_on_mariadb_versions() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        database_version="10.4.12-MariaDB",
        main_version="10.4",
        description=None,
        is_active=True,
    )

    connection = _StubMySQLConnection(
        forbid_information_schema=True,
        user_rows=[
            ("demo", "%", "N", "N", "N", "caching_sha2_password", None),
        ],
    )

    accounts = adapter._fetch_raw_accounts(instance, connection)
    assert len(accounts) == 1
    permissions = accounts[0]["permissions"]
    assert isinstance(permissions, dict)
    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)
    assert type_specific.get("account_kind") == "user"


@pytest.mark.unit
def test_mysql_adapter_fetch_raw_accounts_falls_back_when_mysql_user_missing_is_role() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        database_version="8.0.32",
        main_version="8.0",
        description=None,
        is_active=True,
    )

    connection = _StubMySQLConnection(
        forbid_information_schema=True,
        forbid_is_role_column=True,
        user_rows=[
            ("demo", "%", "N", "N", "N", "caching_sha2_password", None),
            ("r1", "%", "N", "Y", "N", None, None),
        ],
        role_edges_rows=[("r1", "%", "demo", "%", 0)],
    )

    accounts = adapter._fetch_raw_accounts(instance, connection)

    kind_by_username: dict[str, str] = {}
    for account in accounts:
        username = account.get("username")
        assert isinstance(username, str)
        permissions = account.get("permissions")
        assert isinstance(permissions, dict)
        type_specific = permissions.get("type_specific")
        assert isinstance(type_specific, dict)
        account_kind = type_specific.get("account_kind")
        assert isinstance(account_kind, str)
        kind_by_username[username] = account_kind

    assert kind_by_username == {"demo@%": "user", "r1@%": "role"}


@pytest.mark.unit
def test_mysql57_enrich_permissions_skips_roles_tables() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type=DatabaseType.MYSQL,
        host="127.0.0.1",
        port=3306,
        main_version="5.7",
        description=None,
        is_active=True,
    )

    connection = _StubMySQLConnection(
        forbid_information_schema=True,
        forbid_roles_tables=True,
        user_rows=[],
    )

    accounts = cast(
        list[RemoteAccount],
        [
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
        ],
    )

    enriched = adapter.enrich_permissions(instance, connection, accounts)
    assert enriched[0]["permissions"].get("roles") == {"direct": [], "default": []}
