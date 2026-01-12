"""账户同步相关的类型别名."""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping
else:
    Mapping = dict

from app.core.types.structures import JsonDict, JsonValue


class PermissionSnapshot(TypedDict, total=False):
    """标准化的权限快照结构."""

    roles: list[str]
    global_privileges: list[str]
    database_privileges: Mapping[str, list[str] | JsonValue]
    database_privileges_pg: Mapping[str, JsonValue]
    database_permissions: Mapping[str, JsonValue]
    database_roles: Mapping[str, list[str]]
    server_roles: list[str]
    server_permissions: list[str]
    predefined_roles: list[str]
    role_attributes: Mapping[str, JsonValue]
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
