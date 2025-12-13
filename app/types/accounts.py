"""账户同步相关的类型别名."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping
else:
    Mapping = dict

from app.types.structures import JsonDict, JsonValue


class PermissionSnapshot(TypedDict, total=False):
    """标准化的权限快照结构."""

    roles: list[str]
    global_privileges: list[str]
    database_privileges: Mapping[str, list[str] | JsonValue]
    type_specific: JsonDict
    extra: JsonDict


class RemoteAccount(TypedDict, total=False):
    """标准化远端账户结构."""

    username: str
    display_name: str | None
    db_type: str
    is_superuser: bool
    is_active: bool
    is_locked: bool
    attributes: JsonDict
    permissions: PermissionSnapshot
    metadata: JsonDict


RawAccount = dict[str, JsonValue | JsonDict | PermissionSnapshot]

__all__ = ["PermissionSnapshot", "RawAccount", "RemoteAccount"]
