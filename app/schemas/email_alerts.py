"""邮件告警配置 schema."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import PayloadSchema


class EmailAlertSettingsPayload(PayloadSchema):
    """邮件告警配置写入 payload."""

    global_enabled: bool
    recipients: list[str] = Field(default_factory=list)
    database_capacity_enabled: bool
    database_capacity_percent_threshold: int
    database_capacity_absolute_gb_threshold: int
    account_sync_failure_enabled: bool
    database_sync_failure_enabled: bool
    privileged_account_enabled: bool

    @field_validator("database_capacity_percent_threshold", "database_capacity_absolute_gb_threshold")
    @classmethod
    def _validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("阈值必须为正整数")
        return value

    @field_validator("recipients", mode="before")
    @classmethod
    def _normalize_recipients(cls, value: Any) -> Any:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("recipients 必须为字符串数组")
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("recipients 必须为字符串数组")
            email = item.strip()
            if email:
                normalized.append(email)
        return normalized
