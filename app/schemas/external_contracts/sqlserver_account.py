"""SQL Server 外部账户结构 adapter/normalizer.

目的：
- 收敛 SQL Server 采集返回的“脏 dict”到 schema 层单入口。
- Adapter/Service 层不再出现 `account.get(...) or {}` 这类 truthy 兜底链。
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from app.schemas.base import PayloadSchema

JsonDict = dict[str, Any]


def _as_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _as_dict_of_str_list(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, list[str]] = {}
    for key, entry in value.items():
        if not isinstance(key, str) or not key:
            continue
        output[key] = _as_str_list(entry)
    return output


class SQLServerPermissionSnapshotSchema(PayloadSchema):
    """SQL Server 权限快照 schema（仅解析 + 默认值 + 形状规整）."""

    server_roles: list[str] = Field(default_factory=list)
    server_permissions: list[str] = Field(default_factory=list)
    database_roles: dict[str, list[str]] = Field(default_factory=dict)
    database_permissions: dict[str, Any] = Field(default_factory=dict)
    type_specific: JsonDict = Field(default_factory=dict)

    @field_validator("server_roles", mode="before")
    @classmethod
    def _parse_server_roles(cls, value: object) -> list[str]:
        return _as_str_list(value)

    @field_validator("server_permissions", mode="before")
    @classmethod
    def _parse_server_permissions(cls, value: object) -> list[str]:
        return _as_str_list(value)

    @field_validator("database_roles", mode="before")
    @classmethod
    def _parse_database_roles(cls, value: object) -> dict[str, list[str]]:
        return _as_dict_of_str_list(value)

    @field_validator("database_permissions", mode="before")
    @classmethod
    def _parse_database_permissions(cls, value: object) -> dict[str, Any]:
        return _as_dict(value)

    @field_validator("type_specific", mode="before")
    @classmethod
    def _parse_type_specific(cls, value: object) -> JsonDict:
        return _as_dict(value)


class SQLServerRawAccountSchema(PayloadSchema):
    """SQL Server raw account schema（仅解析 + 默认值 + 形状规整）."""

    username: str
    is_superuser: bool = False
    is_locked: bool = False
    is_disabled: bool = False
    permissions: SQLServerPermissionSnapshotSchema = Field(default_factory=SQLServerPermissionSnapshotSchema)

    @field_validator("permissions", mode="before")
    @classmethod
    def _parse_permissions(cls, value: object) -> dict[str, Any]:
        return _as_dict(value)

    @model_validator(mode="after")
    def _normalize_type_specific_flags(self) -> SQLServerRawAccountSchema:
        type_specific = self.permissions.type_specific
        is_disabled_value = type_specific.get("is_disabled")
        if isinstance(is_disabled_value, bool):
            return self

        type_specific["is_disabled"] = self.is_disabled
        self.permissions.type_specific = type_specific
        return self


__all__ = [
    "SQLServerPermissionSnapshotSchema",
    "SQLServerRawAccountSchema",
]

