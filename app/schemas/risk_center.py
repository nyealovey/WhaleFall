"""风险中心写入 schema."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.base import PayloadSchema


class RiskCenterRulePayload(PayloadSchema):
    """风险中心单条规则写入 payload."""

    rule_key: str
    enabled: bool = True
    severity: Literal["high", "medium", "low"]


class RiskCenterRulesUpdatePayload(PayloadSchema):
    """风险中心规则批量写入 payload."""

    rules: list[RiskCenterRulePayload] = Field(min_length=1)
