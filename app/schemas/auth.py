"""认证/密码相关 schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import StrictStr, model_validator

from app.core.constants.validation_limits import USER_PASSWORD_MAX_LENGTH, USER_PASSWORD_MIN_LENGTH
from app.schemas.base import PayloadSchema
from app.schemas.validation import SchemaMessageKeyError


class LoginPayload(PayloadSchema):
    """登录 payload."""

    username: StrictStr
    password: StrictStr

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            raise SchemaMessageKeyError("用户名和密码不能为空", message_key="VALIDATION_ERROR")

        username = data.get("username")
        password = data.get("password")
        if username is None or password is None:
            raise SchemaMessageKeyError("用户名和密码不能为空", message_key="VALIDATION_ERROR")
        if isinstance(username, str) and not username.strip():
            raise SchemaMessageKeyError("用户名和密码不能为空", message_key="VALIDATION_ERROR")
        if isinstance(password, str) and password == "":
            raise SchemaMessageKeyError("用户名和密码不能为空", message_key="VALIDATION_ERROR")

        return data


class ChangePasswordPayload(PayloadSchema):
    """修改密码 payload."""

    old_password: StrictStr
    new_password: StrictStr
    confirm_password: StrictStr

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            raise SchemaMessageKeyError("所有字段都不能为空", message_key="VALIDATION_ERROR")
        for field in ("old_password", "new_password", "confirm_password"):
            value = data.get(field)
            if value is None or value == "":
                raise SchemaMessageKeyError("所有字段都不能为空", message_key="VALIDATION_ERROR")
        return data

    @model_validator(mode="after")
    def _validate_consistency(self) -> ChangePasswordPayload:
        if self.new_password != self.confirm_password:
            raise SchemaMessageKeyError("两次输入的新密码不一致", message_key="PASSWORD_MISMATCH")
        if self.new_password == self.old_password:
            raise SchemaMessageKeyError("新密码不能与当前密码相同", message_key="PASSWORD_DUPLICATED")
        _validate_basic_password(self.new_password)
        return self


def _validate_basic_password(password: str) -> None:
    if not password.strip():
        raise SchemaMessageKeyError("密码不能为空", message_key="PASSWORD_INVALID")
    if len(password) < USER_PASSWORD_MIN_LENGTH:
        raise SchemaMessageKeyError(f"密码长度至少{USER_PASSWORD_MIN_LENGTH}个字符", message_key="PASSWORD_INVALID")
    if len(password) > USER_PASSWORD_MAX_LENGTH:
        raise SchemaMessageKeyError(f"密码长度不能超过{USER_PASSWORD_MAX_LENGTH}个字符", message_key="PASSWORD_INVALID")
