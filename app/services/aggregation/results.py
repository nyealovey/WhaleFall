"""
Aggregation result data structures shared across aggregation components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class AggregationStatus(str, Enum):
    """聚合任务执行状态"""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(slots=True)
class PeriodSummary:
    """按周期聚合的汇总结果"""

    period_type: str
    start_date: date
    end_date: date
    processed_instances: int = 0
    total_records: int = 0
    failed_instances: int = 0
    skipped_instances: int = 0
    errors: list[str] = field(default_factory=list)
    message: str | None = None

    @property
    def status(self) -> AggregationStatus:
        if self.failed_instances > 0:
            return AggregationStatus.FAILED
        if self.processed_instances == 0:
            return AggregationStatus.SKIPPED
        return AggregationStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "period_type": self.period_type,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "processed_instances": self.processed_instances,
            "total_records": self.total_records,
            "failed_instances": self.failed_instances,
            "skipped_instances": self.skipped_instances,
            "errors": self.errors,
            "message": self.message,
        }


@dataclass(slots=True)
class InstanceSummary:
    """单个实例的聚合情况"""

    instance_id: int
    instance_name: str | None
    period_type: str
    processed_records: int = 0
    errors: list[str] = field(default_factory=list)
    message: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> AggregationStatus:
        if self.errors:
            return AggregationStatus.FAILED
        if self.processed_records == 0:
            return AggregationStatus.SKIPPED
        return AggregationStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status.value,
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "period_type": self.period_type,
            "processed_records": self.processed_records,
        }
        if self.errors:
            payload["errors"] = list(self.errors)
        if self.message:
            payload["message"] = self.message
        if self.extra:
            payload.update(self.extra)
        return payload


__all__ = ["AggregationStatus", "PeriodSummary", "InstanceSummary"]
