"""Veeam 数据源 schema."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import Field, field_validator

from app.core.constants.validation_limits import HOST_MAX_LENGTH, PORT_MAX, PORT_MIN
from app.schemas.base import PayloadSchema


def _normalize_domain(value: str) -> str:
    return value.strip().strip(".").lower()


class VeeamSourceBindingPayload(PayloadSchema):
    """Veeam 数据源绑定 payload."""

    credential_id: int
    server_host: str
    server_port: int
    api_version: str
    verify_ssl: bool | None = None
    match_domains: list[str] = Field(default_factory=list)

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

    @field_validator("server_host", mode="before")
    @classmethod
    def _parse_server_host(cls, value: Any) -> str:
        if value is None:
            raise ValueError("server_host不能为空")
        resolved = str(value).strip()
        if not resolved:
            raise ValueError("server_host不能为空")
        return resolved

    @field_validator("server_host")
    @classmethod
    def _validate_server_host(cls, value: str) -> str:
        if len(value) > HOST_MAX_LENGTH:
            raise ValueError(f"server_host长度不能超过{HOST_MAX_LENGTH}个字符")
        return value

    @field_validator("server_port", mode="before")
    @classmethod
    def _parse_server_port(cls, value: Any) -> int:
        try:
            resolved = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("server_port必须是整数") from exc
        if resolved < PORT_MIN or resolved > PORT_MAX:
            raise ValueError("server_port必须在1-65535之间")
        return resolved

    @field_validator("api_version", mode="before")
    @classmethod
    def _parse_api_version(cls, value: Any) -> str:
        if value is None:
            raise ValueError("api_version不能为空")
        resolved = str(value).strip()
        if not resolved:
            raise ValueError("api_version不能为空")
        return resolved

    @field_validator("match_domains", mode="before")
    @classmethod
    def _parse_match_domains(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw_items = value.splitlines()
        elif isinstance(value, Iterable):
            raw_items = list(value)
        else:
            raw_items = [value]

        cleaned: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            normalized = _normalize_domain(str(item))
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(normalized)
        return cleaned
