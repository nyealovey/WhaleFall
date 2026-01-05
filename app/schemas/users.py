"""用户写路径 schema."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import StrictStr, field_validator, model_validator

from app.constants import UserRole
from app.models.user import MIN_USER_PASSWORD_LENGTH
from app.schemas.base import PayloadSchema
from app.types.converters import as_bool

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
_ALLOWED_ROLES = {UserRole.ADMIN, UserRole.USER}


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise ValueError("参数格式错误")
    return data


def _validate_username(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("用户名不能为空")
    if not _USERNAME_PATTERN.match(cleaned):
        raise ValueError("用户名只能包含字母、数字和下划线,长度为3-20位")
    return cleaned


def _validate_role(value: str) -> str:
    cleaned = value.strip()
    if cleaned not in _ALLOWED_ROLES:
        raise ValueError("角色只能是管理员或普通用户")
    return cleaned


def _validate_password_strength(password: str) -> None:
    if len(password) < MIN_USER_PASSWORD_LENGTH:
        raise ValueError(f"密码长度至少{MIN_USER_PASSWORD_LENGTH}位")
    if not any(char.isupper() for char in password):
        raise ValueError("密码必须包含大写字母")
    if not any(char.islower() for char in password):
        raise ValueError("密码必须包含小写字母")
    if not any(char.isdigit() for char in password):
        raise ValueError("密码必须包含数字")


class UserCreatePayload(PayloadSchema):
    """创建用户 payload."""

    username: StrictStr
    role: StrictStr
    password: StrictStr
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        username = mapping.get("username")
        role = mapping.get("role")
        password = mapping.get("password")
        if username is None or (isinstance(username, str) and not username.strip()):
            raise ValueError("用户名不能为空")
        if role is None or (isinstance(role, str) and not role.strip()):
            raise ValueError("角色不能为空")
        if password is None or password == "":
            raise ValueError("请设置初始密码")
        return data

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        return _validate_username(value)

    @field_validator("role")
    @classmethod
    def _validate_role(cls, value: str) -> str:
        return _validate_role(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        _validate_password_strength(value)
        return value

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool:
        if value is None:
            return True
        return as_bool(value, default=True)


class UserUpdatePayload(PayloadSchema):
    """更新用户 payload."""

    username: StrictStr
    role: StrictStr
    password: StrictStr | None = None
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        username = mapping.get("username")
        role = mapping.get("role")
        if username is None or (isinstance(username, str) and not username.strip()):
            raise ValueError("用户名不能为空")
        if role is None or (isinstance(role, str) and not role.strip()):
            raise ValueError("角色不能为空")
        return data

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        return _validate_username(value)

    @field_validator("role")
    @classmethod
    def _validate_role(cls, value: str) -> str:
        return _validate_role(value)

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
        _validate_password_strength(value)
        return value

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool | None:
        if value is None:
            return None
        return as_bool(value, default=False)
