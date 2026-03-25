"""JumpServer 数据源 schema."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from pydantic import field_validator

from app.core.constants.validation_limits import JUMPSERVER_BASE_URL_MAX_LENGTH
from app.schemas.base import PayloadSchema


class JumpServerSourceBindingPayload(PayloadSchema):
    """JumpServer 数据源绑定 payload."""

    credential_id: int
    base_url: str
    org_id: str | None = None
    verify_ssl: bool | None = None

    @field_validator("credential_id", mode="before")
    @classmethod
    def _parse_credential_id(cls, value: Any) -> int:
        try:
            resolved = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("credential_id必须是整数") from exc
        if resolved <= 0:
            raise ValueError("credential_id必须是正整数")
        return resolved

    @field_validator("base_url", mode="before")
    @classmethod
    def _parse_base_url(cls, value: Any) -> str:
        if value is None:
            raise ValueError("base_url不能为空")
        resolved = str(value).strip()
        if not resolved:
            raise ValueError("base_url不能为空")
        return resolved

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        if len(value) > JUMPSERVER_BASE_URL_MAX_LENGTH:
            raise ValueError(f"JumpServer URL长度不能超过{JUMPSERVER_BASE_URL_MAX_LENGTH}个字符")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("JumpServer URL必须是合法的 http/https 地址")
        return value

    @field_validator("org_id", mode="before")
    @classmethod
    def _parse_org_id(cls, value: Any) -> str | None:
        if value is None:
            return None
        resolved = str(value).strip()
        if not resolved:
            return None
        return resolved
