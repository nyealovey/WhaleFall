"""AD 域配置 payload schema."""

from __future__ import annotations

from typing import Any

from ldap3.core.exceptions import LDAPInvalidDnError  # type: ignore[import-untyped]
from ldap3.utils.dn import parse_dn  # type: ignore[import-untyped]
from pydantic import StrictStr, field_validator

from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_text
from app.utils.payload_converters import as_bool


class AdDomainConfigPayload(PayloadSchema):
    """新增/更新 AD 域配置 payload."""

    name: StrictStr
    netbios_name: StrictStr
    domain_controllers: list[StrictStr]
    ldap_port: int = 636
    use_ssl: bool = True
    verify_ssl: bool | None = None
    base_dn: StrictStr
    credential_id: int
    is_enabled: bool = True
    description: str | None = None

    @field_validator("name", "netbios_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("字段不能为空")
        return cleaned

    @field_validator("base_dn")
    @classmethod
    def _validate_base_dn(cls, value: str) -> str:
        return validate_ad_base_dn(value)

    @field_validator("domain_controllers", mode="before")
    @classmethod
    def _parse_domain_controllers(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            controllers = [item.strip() for item in value.split(",") if item.strip()]
        elif isinstance(value, list):
            controllers = [str(item).strip() for item in value if str(item).strip()]
        else:
            controllers = []
        if not controllers:
            raise ValueError("domain_controllers不能为空")
        return controllers

    @field_validator("ldap_port", "credential_id", mode="before")
    @classmethod
    def _parse_positive_int(cls, value: Any) -> int:
        parsed = parse_int(value, default=0)
        if parsed <= 0:
            raise ValueError("字段必须为正整数")
        return parsed

    @field_validator("use_ssl", "is_enabled", mode="before")
    @classmethod
    def _parse_bool(cls, value: Any) -> bool:
        return as_bool(value, default=True)

    @field_validator("verify_ssl", mode="before")
    @classmethod
    def _parse_optional_bool(cls, value: Any) -> bool | None:
        if value in (None, ""):
            return None
        return as_bool(value, default=True)

    @field_validator("description", mode="before")
    @classmethod
    def _parse_optional_text(cls, value: Any) -> str | None:
        cleaned = parse_text(value)
        return cleaned or None


class AdDomainEnabledPayload(PayloadSchema):
    """启停 AD 域配置 payload."""

    is_enabled: bool

    @field_validator("is_enabled", mode="before")
    @classmethod
    def _parse_enabled(cls, value: Any) -> bool:
        return as_bool(value, default=True)


def validate_ad_base_dn(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("字段不能为空")
    try:
        parts = parse_dn(cleaned)
    except LDAPInvalidDnError:
        raise ValueError("Base DN 格式无效,例如 DC=user,DC=chint,DC=com") from None

    has_dc = False
    for attr, component, _separator in parts:
        if str(attr).upper() != "DC":
            continue
        has_dc = True
        dc_label = str(component).strip()
        if not dc_label:
            raise ValueError("Base DN 的 DC 片段不能为空")
        if "." in dc_label:
            raise ValueError("Base DN 的 DC 片段不能包含点号,请拆成 DC=chint,DC=com")
    if not has_dc:
        raise ValueError("Base DN 必须包含 DC 片段")
    return cleaned
