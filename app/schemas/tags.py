"""标签写路径 schema."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import StrictStr, field_validator, model_validator

from app.schemas.base import PayloadSchema
from app.utils.payload_converters import as_bool
from app.utils.theme_color_utils import is_valid_theme_color

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


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


def _validate_name(value: str) -> str:
    cleaned = value.strip()
    if not _NAME_PATTERN.match(cleaned):
        raise ValueError("标签代码仅支持字母、数字、下划线或中划线")
    return cleaned


def _validate_display_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("display_name不能为空")
    return cleaned


def _validate_category(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("category不能为空")
    return cleaned


def _parse_color(value: Any, *, fallback: str | None) -> str | None:
    if value is None:
        return fallback
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or (fallback or "primary")
    cleaned = str(value).strip()
    return cleaned or (fallback or "primary")


class TagUpsertPayload(PayloadSchema):
    """创建标签 payload."""

    name: StrictStr
    display_name: StrictStr
    category: StrictStr
    color: StrictStr = "primary"
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        return _require_fields(data, required=("name", "display_name", "category"))

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, value: str) -> str:
        return _validate_display_name(value)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        return _validate_category(value)

    @field_validator("color", mode="before")
    @classmethod
    def _parse_color(cls, value: Any) -> str:
        parsed = _parse_color(value, fallback="primary")
        return "primary" if parsed is None else parsed

    @field_validator("color")
    @classmethod
    def _validate_color(cls, value: str) -> str:
        if not is_valid_theme_color(value):
            raise ValueError(f"无效的颜色选择: {value}")
        return value

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool:
        if value is None:
            return True
        return as_bool(value, default=True)


class TagUpdatePayload(PayloadSchema):
    """更新标签 payload."""

    name: StrictStr
    display_name: StrictStr
    category: StrictStr
    color: StrictStr | None = None
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        return _require_fields(data, required=("name", "display_name", "category"))

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _validate_name(value)

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, value: str) -> str:
        return _validate_display_name(value)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        return _validate_category(value)

    @field_validator("color", mode="before")
    @classmethod
    def _parse_color(cls, value: Any) -> str | None:
        return _parse_color(value, fallback=None)

    @field_validator("color")
    @classmethod
    def _validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not is_valid_theme_color(value):
            raise ValueError(f"无效的颜色选择: {value}")
        return value

    @field_validator("is_active", mode="before")
    @classmethod
    def _parse_is_active(cls, value: Any) -> bool | None:
        if value is None:
            return None
        return as_bool(value, default=False)
