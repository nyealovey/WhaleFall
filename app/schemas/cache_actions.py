"""Cache actions 写路径 schema."""

from __future__ import annotations

from typing import Any

from pydantic import StrictStr, field_validator

from app.schemas.base import PayloadSchema

CLASSIFICATION_DB_TYPES: tuple[str, ...] = ("mysql", "postgresql", "sqlserver", "oracle")
VALID_CLASSIFICATION_DB_TYPES: frozenset[str] = frozenset(CLASSIFICATION_DB_TYPES)


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
