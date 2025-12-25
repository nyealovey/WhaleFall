"""容量统计(聚合触发)相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CurrentAggregationRequest:
    """手动触发当前周期聚合的请求参数."""

    requested_period_type: str
    scope: str

