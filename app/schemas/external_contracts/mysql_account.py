"""MySQL 外部账户结构 adapter/normalizer.

目的：
- 收敛 MySQL 采集/驱动返回的“脏 dict”到 schema 层单入口。
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


def _default_roles_payload() -> dict[str, list[str]]:
    return {"direct": [], "default": []}


def _as_roles_payload(value: object) -> dict[str, list[str]]:
    if isinstance(value, dict):
        return {
            "direct": _as_str_list(value.get("direct")),
            "default": _as_str_list(value.get("default")),
        }

    # 兼容旧形状：list[str] 作为 direct roles。
    return {
        "direct": _as_str_list(value),
        "default": [],
    }


class MySQLPermissionSnapshotSchema(PayloadSchema):
    """MySQL 权限快照 schema（仅解析 + 默认值 + 形状规整）."""

    mysql_global_privileges: list[str] = Field(default_factory=list)
    mysql_database_privileges: dict[str, list[str]] = Field(default_factory=dict)
    mysql_granted_roles: dict[str, list[str]] = Field(default_factory=_default_roles_payload)
    type_specific: JsonDict = Field(default_factory=dict)

    @field_validator("mysql_global_privileges", mode="before")
    @classmethod
    def _parse_mysql_global_privileges(cls, value: object) -> list[str]:
        return _as_str_list(value)

    @field_validator("mysql_database_privileges", mode="before")
    @classmethod
    def _parse_mysql_database_privileges(cls, value: object) -> dict[str, list[str]]:
        return _as_dict_of_str_list(value)

    @field_validator("mysql_granted_roles", mode="before")
    @classmethod
    def _parse_mysql_granted_roles(cls, value: object) -> dict[str, list[str]]:
        return _as_roles_payload(value)

    @field_validator("type_specific", mode="before")
    @classmethod
    def _parse_type_specific(cls, value: object) -> JsonDict:
        return _as_dict(value)


class MySQLRawAccountSchema(PayloadSchema):
    """MySQL raw account schema（仅解析 + 默认值 + 形状规整）."""

    username: str
    is_superuser: bool = False
    is_locked: bool = False
    permissions: MySQLPermissionSnapshotSchema = Field(default_factory=MySQLPermissionSnapshotSchema)

    @field_validator("permissions", mode="before")
    @classmethod
    def _parse_permissions(cls, value: object) -> dict[str, Any]:
        return _as_dict(value)

    @model_validator(mode="after")
    def _normalize_type_specific_identity(self) -> MySQLRawAccountSchema:
        """确保 type_specific 内至少包含可用于 enrich 的 identity 字段."""
        username = self.username.strip()
        if "@" not in username:
            return self

        user_part, host_part = username.split("@", 1)

        type_specific = self.permissions.type_specific
        original_username_value = type_specific.get("original_username")
        if not isinstance(original_username_value, str) or not original_username_value.strip():
            type_specific["original_username"] = user_part

        host_value = type_specific.get("host")
        if not isinstance(host_value, str) or not host_value.strip():
            type_specific["host"] = host_part

        self.permissions.type_specific = type_specific
        return self


__all__ = [
    "MySQLPermissionSnapshotSchema",
    "MySQLRawAccountSchema",
]
