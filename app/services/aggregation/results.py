"""
Aggregation result data structures shared across aggregation components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class AggregationStatus(str, Enum):
    """聚合任务执行状态。

    定义聚合任务的三种执行状态。

    Attributes:
        COMPLETED: 聚合完成。
        SKIPPED: 聚合跳过（无数据或不需要执行）。
        FAILED: 聚合失败。

    """

    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(slots=True)
class PeriodSummary:
    """按周期聚合的汇总结果。

    记录某个周期内所有实例的聚合执行情况。

    Attributes:
        period_type: 周期类型，如 'daily'、'weekly'、'monthly'、'quarterly'。
        start_date: 周期开始日期。
        end_date: 周期结束日期。
        processed_instances: 已处理的实例数量。
        total_records: 生成的聚合记录总数。
        failed_instances: 失败的实例数量。
        skipped_instances: 跳过的实例数量。
        errors: 错误信息列表。
        message: 可选的汇总消息。

    """

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
        """计算聚合状态。

        Returns:
            根据执行情况返回对应的状态枚举值。

        """
        if self.failed_instances > 0:
            return AggregationStatus.FAILED
        if self.processed_instances == 0:
            return AggregationStatus.SKIPPED
        return AggregationStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含所有字段的字典，日期字段转换为 ISO 8601 格式字符串。

        """
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
    """单个实例的聚合情况。

    记录单个实例在某个周期内的聚合执行结果。

    Attributes:
        instance_id: 实例 ID。
        instance_name: 实例名称，可选。
        period_type: 周期类型，如 'daily'、'weekly'、'monthly'、'quarterly'。
        processed_records: 已处理的记录数量。
        errors: 错误信息列表。
        message: 可选的消息。
        extra: 额外信息字典。

    """

    instance_id: int
    instance_name: str | None
    period_type: str
    processed_records: int = 0
    errors: list[str] = field(default_factory=list)
    message: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> AggregationStatus:
        """计算聚合状态。

        Returns:
            根据执行情况返回对应的状态枚举值。

        """
        if self.errors:
            return AggregationStatus.FAILED
        if self.processed_records == 0:
            return AggregationStatus.SKIPPED
        return AggregationStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            包含所有字段的字典，可选字段仅在有值时包含。

        """
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
