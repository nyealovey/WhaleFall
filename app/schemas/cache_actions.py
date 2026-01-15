"""Cache actions 写路径 schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import StrictStr, field_validator, model_validator

from app.schemas.base import PayloadSchema

CLASSIFICATION_DB_TYPES: tuple[str, ...] = ("mysql", "postgresql", "sqlserver", "oracle")
VALID_CLASSIFICATION_DB_TYPES: frozenset[str] = frozenset(CLASSIFICATION_DB_TYPES)


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise TypeError("参数格式错误")
    return data


class ClearUserCachePayload(PayloadSchema):
    """清除用户缓存 payload."""

    instance_id: int
    username: StrictStr

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        instance_id = mapping.get("instance_id")
        username = mapping.get("username")
        if instance_id is None or username is None:
            raise ValueError("缺少必要参数: instance_id 和 username")
        if isinstance(username, str) and not username.strip():
            raise ValueError("缺少必要参数: instance_id 和 username")
        return data

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("instance_id 必须为整数") from exc
        if parsed <= 0:
            raise ValueError("instance_id 必须为正整数")
        return parsed

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("username 不能为空")
        return normalized


class ClearInstanceCachePayload(PayloadSchema):
    """清除实例缓存 payload."""

    instance_id: int

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        instance_id = mapping.get("instance_id")
        if instance_id is None:
            raise ValueError("缺少必要参数: instance_id")
        return data

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("instance_id 必须为整数") from exc
        if parsed <= 0:
            raise ValueError("instance_id 必须为正整数")
        return parsed


class ClearClassificationCachePayload(PayloadSchema):
    """清除分类缓存 payload."""

    db_type: StrictStr | None = None

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("db_type 必须为字符串")  # noqa: TRY004
        cleaned = value.strip()
        if not cleaned:
            return None
        normalized = cleaned.lower()
        if normalized not in VALID_CLASSIFICATION_DB_TYPES:
            raise ValueError(f"不支持的数据库类型: {cleaned}")
        return normalized
