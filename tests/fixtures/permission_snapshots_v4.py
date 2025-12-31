"""Account permission snapshot fixtures (v4).

These fixtures represent the *target* v4 snapshot schema described in:
- `docs/plans/2025-12-30-account-permissions-refactor-v4.md`

They are intentionally JSON-serializable dictionaries so they can be used in:
- unit tests (facts builder / DSL evaluator)
- contract tests (schema expectations)
- scripts (consistency verification)
"""

from __future__ import annotations

from typing import Any

JsonDict = dict[str, Any]


def _base_snapshot(*, adapter: str, collected_at: str) -> JsonDict:
    return {
        "version": 4,
        "categories": {},
        "type_specific": {},
        "extra": {},
        "errors": [],
        "meta": {
            "adapter": adapter,
            "adapter_version": "v4",
            "collected_at": collected_at,
        },
    }


MYSQL_SNAPSHOT_V4_BASIC: JsonDict = {
    **_base_snapshot(adapter="mysql", collected_at="2025-12-30T00:00:00Z"),
    "categories": {
        "roles": {
            "direct": ["'app_role'@'%'"],
            "default": ["'app_role'@'%'"],
            "closure_enabled": False,
        },
        "global_privileges": {
            "granted": ["SELECT", "INSERT"],
            "grantable": ["SELECT"],
            "denied": [],
        },
        "database_privileges": {
            "db1": {"granted": ["CREATE"], "grantable": [], "denied": []},
        },
    },
    "type_specific": {
        "mysql": {
            "account": {"host": "%", "plugin": "mysql_native_password"},
        },
    },
    "extra": {
        "mysql": {
            "raw_grants": [
                "GRANT SELECT ON *.* TO 'user'@'%' WITH GRANT OPTION",
            ],
        },
    },
    "errors": ["MYSQL_ROLE_CLOSURE_DISABLED"],
}


MYSQL_SNAPSHOT_V4_EMPTY_PERMISSIONS: JsonDict = {
    **_base_snapshot(adapter="mysql", collected_at="2025-12-30T00:00:00Z"),
    "categories": {
        "roles": {
            "direct": [],
            "default": [],
            "closure_enabled": False,
        },
        "global_privileges": {"granted": [], "grantable": [], "denied": []},
        "database_privileges": {},
    },
    "errors": ["MYSQL_ROLE_CLOSURE_DISABLED"],
}


POSTGRESQL_SNAPSHOT_V4_BASIC: JsonDict = {
    **_base_snapshot(adapter="postgresql", collected_at="2025-12-30T00:00:00Z"),
    "categories": {
        "predefined_roles": ["pg_read_all_data", "pg_write_all_data"],
        "role_attributes": {"rolsuper": False, "rolcreaterole": True},
        "database_privileges": {
            "db1": {"granted": ["CONNECT"], "grantable": []},
        },
    },
    "type_specific": {"postgresql": {"oid": 12345}},
}


SQLSERVER_SNAPSHOT_V4_BASIC: JsonDict = {
    **_base_snapshot(adapter="sqlserver", collected_at="2025-12-30T00:00:00Z"),
    "categories": {
        "server_roles": ["securityadmin"],
        "server_permissions": ["CONTROL SERVER"],
        "database_roles": {"db1": ["db_owner"]},
        "database_permissions": {"db1": ["SELECT", "INSERT"]},
    },
    "type_specific": {"sqlserver": {"login_type": "SQL_LOGIN"}},
}


ORACLE_SNAPSHOT_V4_BASIC: JsonDict = {
    **_base_snapshot(adapter="oracle", collected_at="2025-12-30T00:00:00Z"),
    "categories": {
        "oracle_roles": ["DBA"],
        "system_privileges": ["GRANT ANY PRIVILEGE", "UNLIMITED TABLESPACE"],
    },
    "type_specific": {"oracle": {"profile": "DEFAULT"}},
}


V4_SNAPSHOT_FIXTURES: dict[str, JsonDict] = {
    "mysql_basic": MYSQL_SNAPSHOT_V4_BASIC,
    "mysql_empty_permissions": MYSQL_SNAPSHOT_V4_EMPTY_PERMISSIONS,
    "postgresql_basic": POSTGRESQL_SNAPSHOT_V4_BASIC,
    "sqlserver_basic": SQLSERVER_SNAPSHOT_V4_BASIC,
    "oracle_basic": ORACLE_SNAPSHOT_V4_BASIC,
}


def iter_v4_snapshot_fixtures() -> list[tuple[str, JsonDict]]:
    """Return fixtures as a stable list for parametrized tests."""
    return sorted(V4_SNAPSHOT_FIXTURES.items(), key=lambda item: item[0])
