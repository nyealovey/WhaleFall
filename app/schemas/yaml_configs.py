"""YAML 配置文件的 schema(一次性校验/规范化入口).

这些 schema 用于读取 `app/config/*.yaml` 之类的本地配置文件:
- 在读取入口完成一次性 canonicalization + 校验
- 下游逻辑只消费已规整的 typed config，避免运行期散落 `or` 兜底链
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.schemas.base import PayloadSchema


class SchedulerTaskConfig(PayloadSchema):
    """单条 scheduler task 配置."""

    id: str
    name: str
    function: str
    trigger_type: str
    trigger_params: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    description: str | None = None

    @field_validator("id", "name", "function", "trigger_type")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("字段不能为空")
        return value.strip()

    @field_validator("trigger_params", mode="before")
    @classmethod
    def _coerce_trigger_params(cls, value: Any) -> Any:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ValueError("trigger_params 必须为对象")  # noqa: TRY004
        return dict(value)


class SchedulerTasksConfigFile(PayloadSchema):
    """`scheduler_tasks.yaml` 文件结构."""

    default_tasks: list[SchedulerTaskConfig]

    @model_validator(mode="before")
    @classmethod
    def _validate_root(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            raise ValueError("配置文件格式错误，必须为 YAML mapping")  # noqa: TRY004
        return data


class AccountFilterRuleConfig(PayloadSchema):
    """账户同步过滤规则（仅固化实际消费字段）."""

    exclude_users: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)

    @field_validator("exclude_users", "exclude_patterns", mode="before")
    @classmethod
    def _coerce_string_list(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            items: list[str] = []
            for item in value:
                if not isinstance(item, str):
                    continue
                stripped = item.strip()
                if stripped:
                    items.append(stripped)
            return items
        raise ValueError("必须为字符串列表")


class AccountFiltersConfigFile(PayloadSchema):
    """`account_filters.yaml` 文件结构."""

    account_filters: dict[str, AccountFilterRuleConfig]

    @model_validator(mode="before")
    @classmethod
    def _validate_root(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            raise ValueError("配置文件格式错误，必须为 YAML mapping")  # noqa: TRY004
        return data

    @field_validator("account_filters", mode="before")
    @classmethod
    def _normalize_db_type_keys(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            raise ValueError("account_filters 必须为对象")  # noqa: TRY004
        normalized: dict[str, Any] = {}
        for key, rule in value.items():
            if not isinstance(key, str) or not key.strip():
                continue
            normalized[key.strip().lower()] = rule
        return normalized


class DatabaseFilterRuleConfig(PayloadSchema):
    """数据库过滤规则（仅固化实际消费字段）."""

    exclude_databases: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)

    @field_validator("exclude_databases", "exclude_patterns", mode="before")
    @classmethod
    def _coerce_string_list(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            items: list[str] = []
            for item in value:
                if not isinstance(item, str):
                    continue
                stripped = item.strip()
                if stripped:
                    items.append(stripped)
            return items
        raise ValueError("必须为字符串列表")


class DatabaseFiltersConfigFile(PayloadSchema):
    """`database_filters.yaml` 文件结构."""

    database_filters: dict[str, DatabaseFilterRuleConfig]

    @model_validator(mode="before")
    @classmethod
    def _validate_root(cls, data: Any) -> Any:
        if not isinstance(data, Mapping):
            raise ValueError("配置文件格式错误，必须为 YAML mapping")  # noqa: TRY004
        return data

    @field_validator("database_filters", mode="before")
    @classmethod
    def _normalize_db_type_keys(cls, value: Any) -> Any:
        if not isinstance(value, Mapping):
            raise ValueError("database_filters 必须为对象")  # noqa: TRY004
        normalized: dict[str, Any] = {}
        for key, rule in value.items():
            if not isinstance(key, str) or not key.strip():
                continue
            normalized[key.strip().lower()] = rule
        return normalized


__all__ = [
    "AccountFilterRuleConfig",
    "AccountFiltersConfigFile",
    "DatabaseFilterRuleConfig",
    "DatabaseFiltersConfigFile",
    "SchedulerTaskConfig",
    "SchedulerTasksConfigFile",
]
