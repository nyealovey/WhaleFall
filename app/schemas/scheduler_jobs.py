"""调度任务写路径 schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import StrictStr, field_validator, model_validator

from app.schemas.base import PayloadSchema

_CRON_PARTS_ALLOWED = {5, 6, 7}


def _ensure_mapping(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise TypeError("参数格式错误")
    return data


class SchedulerJobUpsertPayload(PayloadSchema):
    """更新调度任务触发器 payload."""

    trigger_type: StrictStr
    cron_expression: StrictStr

    @model_validator(mode="before")
    @classmethod
    def _validate_required_fields(cls, data: Any) -> Any:
        mapping = _ensure_mapping(data)
        trigger_type = mapping.get("trigger_type")
        if trigger_type is None or (isinstance(trigger_type, str) and not trigger_type.strip()):
            raise ValueError("缺少触发器类型配置")

        cron_expression = mapping.get("cron_expression")
        if cron_expression is None or (isinstance(cron_expression, str) and not cron_expression.strip()):
            raise ValueError("缺少 cron_expression")
        return data

    @field_validator("trigger_type", mode="before")
    @classmethod
    def _parse_trigger_type(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("缺少触发器类型配置")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("缺少触发器类型配置")
        return cleaned

    @field_validator("trigger_type")
    @classmethod
    def _validate_trigger_type(cls, value: str) -> str:
        if value != "cron":
            raise ValueError("仅支持 cron 触发器")
        return value

    @field_validator("cron_expression", mode="before")
    @classmethod
    def _parse_cron_expression(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("缺少 cron_expression")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("缺少 cron_expression")
        return cleaned

    @field_validator("cron_expression")
    @classmethod
    def _validate_cron_expression(cls, value: str) -> str:
        parts = value.split()
        if len(parts) not in _CRON_PARTS_ALLOWED:
            raise ValueError("cron_expression 格式非法")
        return value

