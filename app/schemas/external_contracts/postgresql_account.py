"""PostgreSQL 外部账户结构 adapter/normalizer.

目的：
- 收敛 PostgreSQL 采集返回的“脏 dict”到 schema 层单入口。
- Adapter/Service 层不再出现 `account.get(...) or {}` 这类 truthy 兜底链。
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

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


class PostgreSQLPermissionSnapshotSchema(PayloadSchema):
    """PostgreSQL 权限快照 schema（仅解析 + 默认值 + 形状规整）."""

    postgresql_predefined_roles: list[str] = Field(default_factory=list)
    postgresql_role_attributes: JsonDict = Field(default_factory=dict)
    postgresql_database_privileges: dict[str, list[str]] = Field(default_factory=dict)
    type_specific: JsonDict = Field(default_factory=dict)

    @field_validator("postgresql_predefined_roles", mode="before")
    @classmethod
    def _parse_postgresql_predefined_roles(cls, value: object) -> list[str]:
        return _as_str_list(value)

    @field_validator("postgresql_role_attributes", mode="before")
    @classmethod
    def _parse_postgresql_role_attributes(cls, value: object) -> JsonDict:
        return _as_dict(value)

    @field_validator("postgresql_database_privileges", mode="before")
    @classmethod
    def _parse_postgresql_database_privileges(cls, value: object) -> dict[str, list[str]]:
        return _as_dict_of_str_list(value)

    @field_validator("type_specific", mode="before")
    @classmethod
    def _parse_type_specific(cls, value: object) -> JsonDict:
        return _as_dict(value)


class PostgreSQLRawAccountSchema(PayloadSchema):
    """PostgreSQL raw account schema（仅解析 + 默认值 + 形状规整）."""

    username: str
    is_superuser: bool = False
    is_locked: bool = False
    permissions: PostgreSQLPermissionSnapshotSchema = Field(default_factory=PostgreSQLPermissionSnapshotSchema)

    @field_validator("permissions", mode="before")
    @classmethod
    def _parse_permissions(cls, value: object) -> dict[str, Any]:
        return _as_dict(value)


__all__ = [
    "PostgreSQLPermissionSnapshotSchema",
    "PostgreSQLRawAccountSchema",
]
