"""实例写路径 schema."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import Field, StrictStr, field_validator, model_validator

from app.constants import DatabaseType
from app.schemas.base import PayloadSchema
from app.types.converters import as_bool


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise TypeError("参数格式错误")
    return data


def _validate_required_fields(data: Any, *, required: tuple[str, ...]) -> Any:
    mapping = _ensure_mapping(data)
    missing: list[str] = []
    for field in required:
        value = mapping.get(field)
        if value is None:
            missing.append(field)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(field)
    if missing:
        raise ValueError(f"字段 '{', '.join(missing)}' 是必填的")
    return data


def _validate_instance_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("实例名称不能为空")
    if len(cleaned) > 100:
        raise ValueError("实例名称长度不能超过100个字符")
    if not re.match(r"^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$", cleaned):
        raise ValueError("实例名称只能包含字母、数字、下划线、连字符和中文字符")
    return cleaned


def _normalize_db_type(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("数据库类型不能为空")
    normalized = DatabaseType.normalize(cleaned)
    allowed = {DatabaseType.normalize(item) for item in DatabaseType.RELATIONAL}
    if normalized not in allowed:
        raise ValueError(f"不支持的数据库类型: {normalized}.支持的类型: {', '.join(sorted(allowed))}")
    return normalized


def _validate_host(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("主机地址不能为空")
    if len(cleaned) > 255:
        raise ValueError("主机地址长度不能超过255个字符")
    if not _is_valid_host(cleaned):
        raise ValueError("主机地址格式无效,请输入有效的IP地址或域名")
    return cleaned


def _parse_port(value: Any) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("端口号必须是整数") from exc
    if not (1 <= port <= 65535):
        raise ValueError("端口号必须在1-65535之间")
    return port


def _parse_credential_id(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        cred_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("凭据ID必须是整数") from exc
    if cred_id <= 0:
        raise ValueError("凭据ID必须是正整数")
    return cred_id


def _parse_optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value).strip() or None


def _validate_database_name(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > 64:
        raise ValueError("数据库名称长度不能超过64个字符")
    if not re.match(r"^[a-zA-Z0-9_\-]+$", value):
        raise ValueError("数据库名称只能包含字母、数字、下划线和连字符")
    return value


def _parse_tag_names(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


class InstanceCreatePayload(PayloadSchema):
    """创建实例 payload."""

    name: StrictStr
    db_type: StrictStr
    host: StrictStr
    port: int
    credential_id: int | None = None
    database_name: StrictStr | None = None
    description: StrictStr = ""
    tag_names: list[StrictStr] = Field(default_factory=list)
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        return _validate_required_fields(data, required=("name", "db_type", "host", "port"))

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _validate_instance_name(value)

    @field_validator("db_type")
    @classmethod
    def _validate_db_type(cls, value: str) -> str:
        return _normalize_db_type(value)

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: str) -> str:
        return _validate_host(value)

    @field_validator("port", mode="before")
    @classmethod
    def _parse_port(cls, value: Any) -> int:
        return _parse_port(value)

    @field_validator("credential_id", mode="before")
    @classmethod
    def _parse_credential_id(cls, value: Any) -> int | None:
        return _parse_credential_id(value)

    @field_validator("database_name", mode="before")
    @classmethod
    def _parse_database_name(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("database_name")
    @classmethod
    def _validate_database_name(cls, value: str | None) -> str | None:
        return _validate_database_name(value)

    @field_validator("description", mode="before")
    @classmethod
    def _parse_description(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str) -> str:
        if len(value) > 500:
            raise ValueError("描述长度不能超过500个字符")
        return value

    @field_validator("tag_names", mode="before")
    @classmethod
    def _parse_tag_names(cls, value: Any) -> list[str]:
        return _parse_tag_names(value)

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool:
        if value is None:
            return True
        return as_bool(value, default=True)


class InstanceUpdatePayload(PayloadSchema):
    """更新实例 payload."""

    name: StrictStr
    db_type: StrictStr
    host: StrictStr
    port: int
    credential_id: int | None = None
    database_name: StrictStr | None = None
    description: StrictStr | None = None
    tag_names: list[StrictStr] = Field(default_factory=list)
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        return _validate_required_fields(data, required=("name", "db_type", "host", "port"))

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _validate_instance_name(value)

    @field_validator("db_type")
    @classmethod
    def _validate_db_type(cls, value: str) -> str:
        return _normalize_db_type(value)

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: str) -> str:
        return _validate_host(value)

    @field_validator("port", mode="before")
    @classmethod
    def _parse_port(cls, value: Any) -> int:
        return _parse_port(value)

    @field_validator("credential_id", mode="before")
    @classmethod
    def _parse_credential_id(cls, value: Any) -> int | None:
        return _parse_credential_id(value)

    @field_validator("database_name", mode="before")
    @classmethod
    def _parse_database_name(cls, value: Any) -> str | None:
        return _parse_optional_string(value)

    @field_validator("database_name")
    @classmethod
    def _validate_database_name(cls, value: str | None) -> str | None:
        return _validate_database_name(value)

    @field_validator("description", mode="before")
    @classmethod
    def _parse_description(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator("description")
    @classmethod
    def _validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value) > 500:
            raise ValueError("描述长度不能超过500个字符")
        return value

    @field_validator("tag_names", mode="before")
    @classmethod
    def _parse_tag_names(cls, value: Any) -> list[str]:
        return _parse_tag_names(value)

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool | None:
        if value is None:
            return None
        return as_bool(value, default=False)


def _is_valid_host(host: str) -> bool:
    ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if re.match(ip_pattern, host):
        parts = host.split(".")
        return all(0 <= int(part) <= 255 for part in parts)

    domain_pattern = (
        r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
    )
    return bool(re.match(domain_pattern, host))
