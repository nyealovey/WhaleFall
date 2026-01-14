"""分区管理写路径 schema."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from pydantic import field_validator, model_validator

from app.schemas.base import PayloadSchema
from app.schemas.validation import SchemaMessageKeyError
from app.utils.time_utils import time_utils

DEFAULT_RETENTION_MONTHS = 12


class PartitionCreatePayload(PayloadSchema):
    """创建分区 payload."""

    date: date

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            raise SchemaMessageKeyError("请求体必须是 JSON 对象", message_key="VALIDATION_ERROR")
        raw = data.get("date")
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            raise SchemaMessageKeyError("缺少日期参数", message_key="VALIDATION_ERROR")
        return data

    @field_validator("date", mode="before")
    @classmethod
    def _parse_partition_date(cls, value: Any) -> date:
        if value is None or value == "":
            raise ValueError("缺少日期参数")
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()

        try:
            parsed_dt = time_utils.to_china(str(value) + "T00:00:00")
        except Exception as exc:
            raise ValueError("日期格式错误,请使用 YYYY-MM-DD 格式") from exc
        if parsed_dt is None:
            raise ValueError("无法解析日期")
        return parsed_dt.date()


class PartitionCleanupPayload(PayloadSchema):
    """清理旧分区 payload."""

    retention_months: int = DEFAULT_RETENTION_MONTHS

    @field_validator("retention_months", mode="before")
    @classmethod
    def _parse_retention_months(cls, value: Any) -> int:
        if value is None:
            return DEFAULT_RETENTION_MONTHS

        if isinstance(value, bool):
            raise ValueError("retention_months 必须为数字")  # noqa: TRY004

        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("retention_months 必须为数字") from exc

        if parsed <= 0:
            raise ValueError("retention_months 必须为正整数(月)")

        return parsed
