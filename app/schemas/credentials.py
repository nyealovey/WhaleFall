"""凭据写路径 schema."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import StrictStr, field_validator, model_validator

from app.constants import DatabaseType
from app.schemas.base import PayloadSchema
from app.types.converters import as_bool

_ALLOWED_CREDENTIAL_TYPES: set[str] = {"database", "ssh", "windows", "api", "ldap"}


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise TypeError("参数格式错误")
    return data


def _require_fields(data: Any, *, required: tuple[str, ...]) -> Any:
    mapping = _ensure_mapping(data)
    for field in required:
        value = mapping.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{field}不能为空")
    return data


def _normalize_credential_type(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("credential_type不能为空")
    if normalized not in _ALLOWED_CREDENTIAL_TYPES:
        raise ValueError(f"不支持的凭据类型: {value}")
    return normalized


def _validate_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("name不能为空")
    return cleaned


def _validate_username(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("用户名不能为空")
    if len(normalized) < 3:
        raise ValueError("用户名长度至少3个字符")
    if len(normalized) > 50:
        raise ValueError("用户名长度不能超过50个字符")
    if not re.match(r"^[a-zA-Z0-9_.-]+$", normalized):
        raise ValueError("用户名只能包含字母、数字、下划线、连字符和点")
    return normalized


def _validate_password(value: str) -> str:
    if not value.strip():
        raise ValueError("密码不能为空")
    if len(value) < 6:
        raise ValueError("密码长度至少6个字符")
    if len(value) > 128:
        raise ValueError("密码长度不能超过128个字符")
    return value


def _parse_optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value).strip() or None


def _validate_db_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = DatabaseType.normalize(value)
    allowed = {DatabaseType.normalize(item) for item in DatabaseType.RELATIONAL}
    if normalized not in allowed:
        raise ValueError(f"不支持的数据库类型: {value}")
    return normalized


class CredentialCreatePayload(PayloadSchema):
    """创建凭据 payload."""

    name: StrictStr
    credential_type: StrictStr
    username: StrictStr
    password: StrictStr
    db_type: StrictStr | None = None
    description: StrictStr | None = None
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        return _require_fields(data, required=("name", "credential_type", "username", "password"))

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("credential_type")
    @classmethod
    def _validate_credential_type(cls, value: str) -> str:
        return _normalize_credential_type(value)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        return _validate_username(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        return _validate_password(value)

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("db_type")
    @classmethod
    def _validate_db_type(cls, value: str | None) -> str | None:
        return _validate_db_type(value)

    @field_validator("description", mode="before")
    @classmethod
    def _parse_description(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool:
        if value is None:
            return True
        return as_bool(value, default=True)


class CredentialUpdatePayload(PayloadSchema):
    """更新凭据 payload."""

    name: StrictStr
    credential_type: StrictStr
    username: StrictStr
    password: StrictStr | None = None
    db_type: StrictStr | None = None
    description: StrictStr | None = None
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        return _require_fields(data, required=("name", "credential_type", "username"))

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("credential_type")
    @classmethod
    def _validate_credential_type(cls, value: str) -> str:
        return _normalize_credential_type(value)

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        return _validate_username(value)

    @field_validator("password", mode="before")
    @classmethod
    def _parse_password(cls, value: Any) -> str | None:
        if value in (None, ""):
            return None
        if isinstance(value, str):
            return value
        return str(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_password(value)

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("db_type")
    @classmethod
    def _validate_db_type(cls, value: str | None) -> str | None:
        return _validate_db_type(value)

    @field_validator("description", mode="before")
    @classmethod
    def _parse_description(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool | None:
        if value is None:
            return None
        return as_bool(value, default=False)
