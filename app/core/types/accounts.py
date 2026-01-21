"""账户同步相关的类型别名."""

from __future__ import annotations

from collections.abc import Mapping
from typing import NotRequired, TypedDict

from app.core.types.structures import JsonDict, JsonValue


class MySQLRolesSnapshot(TypedDict, total=False):
    """MySQL roles snapshot payload."""

    direct: list[str]
    default: list[str]


class PermissionSnapshot(TypedDict, total=False):
    """标准化的权限快照结构."""

    # MySQL
    mysql_granted_roles: list[str] | MySQLRolesSnapshot
    mysql_role_members: MySQLRolesSnapshot
    mysql_global_privileges: list[str]
    mysql_database_privileges: Mapping[str, list[str] | JsonValue]

    # PostgreSQL
    postgresql_database_privileges: Mapping[str, JsonValue]
    postgresql_predefined_roles: list[str]
    postgresql_role_attributes: Mapping[str, JsonValue]

    # SQL Server (legacy keys will be removed during refactor)
    database_permissions: Mapping[str, JsonValue]
    database_roles: Mapping[str, list[str]]
    server_roles: list[str]
    server_permissions: list[str]

    # Oracle
    oracle_roles: list[str]
    system_privileges: list[str]

    errors: list[str]
    type_specific: JsonDict
    extra: JsonDict


class RemoteAccount(TypedDict):
    """标准化远端账户结构."""

    username: str
    display_name: NotRequired[str | None]
    db_type: str
    is_superuser: bool
    is_active: bool
    is_locked: bool
    attributes: NotRequired[JsonDict]
    permissions: PermissionSnapshot
    metadata: NotRequired[JsonDict]


RawAccount = dict[str, JsonValue | JsonDict | PermissionSnapshot]

__all__ = ["PermissionSnapshot", "RawAccount", "RemoteAccount"]
