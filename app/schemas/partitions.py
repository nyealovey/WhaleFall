"""分区管理写路径 schema."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from app.schemas.base import PayloadSchema

DEFAULT_RETENTION_MONTHS = 12


class PartitionCleanupPayload(PayloadSchema):
    """清理旧分区 payload."""

    retention_months: int = DEFAULT_RETENTION_MONTHS

    @field_validator("retention_months", mode="before")
    @classmethod
    def _parse_retention_months(cls, value: Any) -> int:
        if value is None:
            return DEFAULT_RETENTION_MONTHS

        if isinstance(value, bool):
            raise ValueError("retention_months 必须为数字")

        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("retention_months 必须为数字") from exc

        if parsed <= 0:
            raise ValueError("retention_months 必须为正整数(月)")

        return parsed

