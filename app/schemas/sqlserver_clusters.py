"""SQL Server 群集管理 schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import AliasChoices, Field, StrictStr, field_validator, model_validator

from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_optional_int, parse_optional_int_list, parse_text
from app.utils.payload_converters import as_bool

_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise TypeError("参数格式错误")
    return data


def _parse_optional_text(value: Any) -> str | None:
    cleaned = parse_text(value)
    return cleaned or None


def _validate_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("name不能为空")
    if len(cleaned) > 128:
        raise ValueError("name长度不能超过128个字符")
    return cleaned


class SQLServerClusterListQuery(PayloadSchema):
    """SQL Server 群集列表 query."""

    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    search: str = ""
    status: str | None = None
    sort_field: str = Field(default="id", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="desc", validation_alias=AliasChoices("order", "sort_order"))

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_PAGE)
        if parsed < 1:
            raise ValueError("page 参数必须为正整数")
        return parsed

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_LIMIT)
        if parsed < 1:
            raise ValueError("limit 参数必须为正整数")
        if parsed > _MAX_LIMIT:
            raise ValueError(f"limit 最大为 {_MAX_LIMIT}")
        return parsed

    @field_validator("search", mode="before")
    @classmethod
    def _parse_search(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def _parse_status(cls, value: Any) -> str | None:
        cleaned = parse_text(value).lower()
        if cleaned in {"active", "inactive"}:
            return cleaned
        return None

    @field_validator("sort_field", mode="before")
    @classmethod
    def _parse_sort_field(cls, value: Any) -> str:
        return parse_text(value).lower() or "id"

    @field_validator("sort_order", mode="before")
    @classmethod
    def _parse_sort_order(cls, value: Any) -> str:
        cleaned = parse_text(value).lower() or "desc"
        if cleaned not in {"asc", "desc"}:
            raise ValueError("order 参数必须为 asc 或 desc")
        return cleaned


class SQLServerClusterCreatePayload(PayloadSchema):
    """创建 SQL Server 群集 payload."""

    name: StrictStr
    description: StrictStr | None = ""
    is_enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def _require_name(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        if not parse_text(mapping.get("name")):
            raise ValueError("name不能为空")
        return data

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("description", mode="before")
    @classmethod
    def _clean_description(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("is_enabled", mode="before")
    @classmethod
    def _parse_is_enabled(cls, value: Any) -> bool:
        return as_bool(value, default=True)


class SQLServerClusterUpdatePayload(PayloadSchema):
    """更新 SQL Server 群集 payload."""

    name: StrictStr | None = None
    description: StrictStr | None = None
    is_enabled: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _parse_name(cls, value: Any) -> str | None:
        return _parse_optional_text(value)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str | None) -> str | None:
        return _validate_name(value) if value is not None else None

    @field_validator("description", mode="before")
    @classmethod
    def _clean_description(cls, value: Any) -> str | None:
        if value is None:
            return None
        return parse_text(value)

    @field_validator("is_enabled", mode="before")
    @classmethod
    def _parse_is_enabled(cls, value: Any) -> bool | None:
        if value is None:
            return None
        return as_bool(value, default=True)


class SQLServerClusterInstancesPayload(PayloadSchema):
    """整体替换群集实例绑定 payload."""

    instance_ids: list[int] = Field(default_factory=list)

    @field_validator("instance_ids", mode="before")
    @classmethod
    def _parse_instance_ids(cls, value: Any) -> list[int]:
        return parse_optional_int_list(value)


class SQLServerAvailabilityGroupCreatePayload(PayloadSchema):
    """创建 SQL Server AG 配置 payload."""

    name: StrictStr
    listener_name: StrictStr | None = None
    listener_host: StrictStr
    listener_port: int = 1433
    credential_id: int | None = None
    connection_database: StrictStr | None = None
    contained_enabled: bool = False
    is_enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def _require_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        for field in ("name", "listener_host"):
            if not parse_text(mapping.get(field)):
                raise ValueError(f"{field}不能为空")
        return data

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("listener_name", "connection_database", mode="before")
    @classmethod
    def _parse_optional_text(cls, value: Any) -> str | None:
        return _parse_optional_text(value)

    @field_validator("listener_host")
    @classmethod
    def _clean_listener_host(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("listener_host不能为空")
        return cleaned

    @field_validator("listener_port", mode="before")
    @classmethod
    def _parse_listener_port(cls, value: Any) -> int:
        parsed = parse_int(value, default=1433)
        if parsed < 1 or parsed > 65535:
            raise ValueError("listener_port 必须在 1-65535 之间")
        return parsed

    @field_validator("credential_id", mode="before")
    @classmethod
    def _parse_credential_id(cls, value: Any) -> int | None:
        return parse_optional_int(value)

    @field_validator("contained_enabled", "is_enabled", mode="before")
    @classmethod
    def _parse_bool(cls, value: Any) -> bool:
        return as_bool(value, default=False)


class SQLServerAvailabilityGroupUpdatePayload(PayloadSchema):
    """更新 SQL Server AG 配置 payload."""

    name: StrictStr | None = None
    listener_name: StrictStr | None = None
    listener_host: StrictStr | None = None
    listener_port: int | None = None
    credential_id: int | None = None
    connection_database: StrictStr | None = None
    contained_enabled: bool | None = None
    is_enabled: bool | None = None

    @field_validator("name", "listener_name", "listener_host", "connection_database", mode="before")
    @classmethod
    def _parse_text_fields(cls, value: Any) -> str | None:
        return _parse_optional_text(value)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str | None) -> str | None:
        return _validate_name(value) if value is not None else None

    @field_validator("listener_port", mode="before")
    @classmethod
    def _parse_listener_port(cls, value: Any) -> int | None:
        parsed = parse_optional_int(value)
        if parsed is not None and (parsed < 1 or parsed > 65535):
            raise ValueError("listener_port 必须在 1-65535 之间")
        return parsed

    @field_validator("credential_id", mode="before")
    @classmethod
    def _parse_credential_id(cls, value: Any) -> int | None:
        return parse_optional_int(value)

    @field_validator("contained_enabled", "is_enabled", mode="before")
    @classmethod
    def _parse_bool(cls, value: Any) -> bool | None:
        if value is None:
            return None
        return as_bool(value, default=False)
