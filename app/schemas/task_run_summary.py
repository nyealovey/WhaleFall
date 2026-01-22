"""TaskRun.summary_json 统一结构定义.

目标:
- 顶层结构固定为 version/common/ext
- common: 通用字段(输入/范围/指标/高亮/flags)
- ext: 任务扩展字段(随 task_key 变化)
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SummaryMetricItemV1(BaseModel):
    """通用指标展示条目."""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    value: int | float | str | bool | None
    unit: str | None = None
    tone: Literal["info", "success", "warning", "danger"] | None = None


class SummaryScopeTimeV1(BaseModel):
    """通用范围: 时间维度."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["date"]
    timezone: str
    date: date


class SummaryScopeV1(BaseModel):
    """通用范围."""

    model_config = ConfigDict(extra="forbid")

    time: SummaryScopeTimeV1 | None = None
    target: dict[str, Any] = Field(default_factory=dict)


class SummaryFlagsV1(BaseModel):
    """通用 flags."""

    model_config = ConfigDict(extra="forbid")

    skipped: bool = False
    skip_reason: str | None = None


class SummaryCommonV1(BaseModel):
    """summary_json 的通用部分."""

    model_config = ConfigDict(extra="forbid")

    inputs: dict[str, Any] = Field(default_factory=dict)
    scope: SummaryScopeV1 = Field(default_factory=SummaryScopeV1)
    metrics: list[SummaryMetricItemV1] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    flags: SummaryFlagsV1 = Field(default_factory=SummaryFlagsV1)


class SummaryExtV1(BaseModel):
    """summary_json 的任务扩展部分."""

    model_config = ConfigDict(extra="forbid")

    type: str
    version: int = 1
    data: dict[str, Any] = Field(default_factory=dict)


class TaskRunSummaryV1(BaseModel):
    """TaskRun.summary_json v1 envelope."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    common: SummaryCommonV1
    ext: SummaryExtV1

    def validate_task_key(self, task_key: str) -> TaskRunSummaryV1:
        """校验 ext.type 是否与 TaskRun.task_key 匹配."""
        if self.ext.type != task_key:
            raise ValueError(f"summary_json.ext.type 必须等于 task_key({task_key})")
        return self


class TaskRunSummaryFactory:
    """用于生成合法的 summary envelope."""

    @staticmethod
    def base(
        *,
        task_key: str,
        inputs: dict[str, Any] | None = None,
        scope: SummaryScopeV1 | dict[str, Any] | None = None,
        metrics: list[SummaryMetricItemV1 | dict[str, Any]] | None = None,
        highlights: list[str] | None = None,
        flags: SummaryFlagsV1 | dict[str, Any] | None = None,
        ext_data: dict[str, Any] | None = None,
        ext_version: int = 1,
    ) -> dict[str, Any]:
        """生成基础 envelope(可选注入 inputs/scope/metrics/highlights/flags/ext.data)."""
        model = TaskRunSummaryV1(
            common={
                "inputs": inputs or {},
                "scope": scope or {},
                "metrics": metrics or [],
                "highlights": highlights or [],
                "flags": flags or {},
            },
            ext={"type": task_key, "version": ext_version, "data": ext_data or {}},
        )
        # 使用 mode="json" 以确保 date 等类型序列化为 JSON 兼容值
        return model.model_dump(mode="json")

