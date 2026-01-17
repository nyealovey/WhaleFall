"""容量统计相关 query 参数 schema.

目标:
- 将 API 层的 query 参数默认值/类型转换/范围裁剪/日期解析下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.core.types.capacity_databases import DatabaseAggregationsFilters, DatabaseAggregationsSummaryFilters
from app.core.types.capacity_instances import InstanceAggregationsFilters, InstanceAggregationsSummaryFilters
from app.schemas.base import PayloadSchema
from app.utils.payload_converters import as_bool
from app.utils.time_utils import time_utils

_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200


def _parse_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_optional_str(value: Any) -> str | None:
    cleaned = _parse_text(value)
    return cleaned or None


def _parse_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise TypeError("参数必须为整数")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(stripped, 10)
        except ValueError as exc:
            raise ValueError("参数必须为整数") from exc
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("参数必须为整数") from exc


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("参数必须为整数")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped, 10)
        except ValueError as exc:
            raise ValueError("参数必须为整数") from exc
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("参数必须为整数") from exc


def _parse_optional_date(value: Any, *, field: str) -> date | None:
    cleaned = _parse_optional_str(value)
    if cleaned is None:
        return None
    try:
        parsed_dt = time_utils.to_china(cleaned + "T00:00:00")
    except Exception as exc:
        raise ValueError(f"{field} 格式错误,应为 YYYY-MM-DD") from exc
    if parsed_dt is None:
        raise ValueError("无法解析日期")
    return parsed_dt.date()


def _parse_time_range_days(value: Any) -> int | None:
    cleaned = _parse_optional_str(value)
    if cleaned is None:
        return None
    try:
        return int(cleaned, 10)
    except (TypeError, ValueError) as exc:
        raise ValueError("time_range 必须为整数(天)") from exc


class CapacityDatabasesAggregationsQuery(PayloadSchema):
    """数据库容量聚合列表 query 参数 schema."""

    start_date: date | None = None
    end_date: date | None = None
    instance_id: int | None = None
    db_type: str | None = None
    database_name: str | None = None
    database_id: int | None = None
    period_type: str | None = None
    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    get_all: bool = False

    @field_validator("start_date", mode="before")
    @classmethod
    def _parse_start_date(cls, value: Any) -> date | None:
        return _parse_optional_date(value, field="start_date")

    @field_validator("end_date", mode="before")
    @classmethod
    def _parse_end_date(cls, value: Any) -> date | None:
        return _parse_optional_date(value, field="end_date")

    @field_validator("instance_id", "database_id", mode="before")
    @classmethod
    def _parse_ids(cls, value: Any) -> int | None:
        return _parse_optional_int(value)

    @field_validator("db_type", "database_name", "period_type", mode="before")
    @classmethod
    def _parse_optional_strings(cls, value: Any) -> str | None:
        return _parse_optional_str(value)

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = _parse_int(value, default=_DEFAULT_PAGE)
        return max(parsed, 1)

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = _parse_int(value, default=_DEFAULT_LIMIT)
        if parsed < 1:
            return 1
        if parsed > _MAX_LIMIT:
            return _MAX_LIMIT
        return parsed

    @field_validator("get_all", mode="before")
    @classmethod
    def _parse_get_all(cls, value: Any) -> bool:
        return as_bool(value, default=False)

    def to_filters(self) -> DatabaseAggregationsFilters:
        """转换为数据库容量聚合 filters 对象."""
        return DatabaseAggregationsFilters(
            instance_id=self.instance_id,
            db_type=self.db_type,
            database_name=self.database_name,
            database_id=self.database_id,
            period_type=self.period_type,
            start_date=self.start_date,
            end_date=self.end_date,
            page=self.page,
            limit=self.limit,
            get_all=self.get_all,
        )


class CapacityDatabasesSummaryQuery(PayloadSchema):
    """数据库容量聚合汇总 query 参数 schema."""

    start_date: date | None = None
    end_date: date | None = None
    instance_id: int | None = None
    db_type: str | None = None
    database_name: str | None = None
    database_id: int | None = None
    period_type: str | None = None

    @field_validator("start_date", mode="before")
    @classmethod
    def _parse_start_date(cls, value: Any) -> date | None:
        return _parse_optional_date(value, field="start_date")

    @field_validator("end_date", mode="before")
    @classmethod
    def _parse_end_date(cls, value: Any) -> date | None:
        return _parse_optional_date(value, field="end_date")

    @field_validator("instance_id", "database_id", mode="before")
    @classmethod
    def _parse_ids(cls, value: Any) -> int | None:
        return _parse_optional_int(value)

    @field_validator("db_type", "database_name", "period_type", mode="before")
    @classmethod
    def _parse_optional_strings(cls, value: Any) -> str | None:
        return _parse_optional_str(value)

    def to_filters(self) -> DatabaseAggregationsSummaryFilters:
        """转换为数据库容量聚合汇总 filters 对象."""
        return DatabaseAggregationsSummaryFilters(
            instance_id=self.instance_id,
            db_type=self.db_type,
            database_name=self.database_name,
            database_id=self.database_id,
            period_type=self.period_type,
            start_date=self.start_date,
            end_date=self.end_date,
        )


class _CapacityInstancesDateRangeMixin(PayloadSchema):
    start_date: date | None = None
    end_date: date | None = None
    time_range: int | None = Field(default=None, description="时间范围(天),仅当 start/end 均缺失时生效")

    @field_validator("start_date", mode="before")
    @classmethod
    def _parse_start_date(cls, value: Any) -> date | None:
        return _parse_optional_date(value, field="start_date")

    @field_validator("end_date", mode="before")
    @classmethod
    def _parse_end_date(cls, value: Any) -> date | None:
        return _parse_optional_date(value, field="end_date")

    @field_validator("time_range", mode="before")
    @classmethod
    def _parse_time_range(cls, value: Any) -> int | None:
        return _parse_time_range_days(value)

    @model_validator(mode="after")
    def _apply_time_range(self) -> _CapacityInstancesDateRangeMixin:
        if self.time_range is None:
            return self
        if self.start_date is not None or self.end_date is not None:
            return self
        end_date_obj = time_utils.now_china().date()
        start_date_obj = end_date_obj - timedelta(days=self.time_range)
        self.start_date = start_date_obj
        self.end_date = end_date_obj
        return self


class CapacityInstancesAggregationsQuery(_CapacityInstancesDateRangeMixin):
    """实例容量聚合列表 query 参数 schema."""

    instance_id: int | None = None
    db_type: str | None = None
    period_type: str | None = None
    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    get_all: bool = False

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int | None:
        return _parse_optional_int(value)

    @field_validator("db_type", "period_type", mode="before")
    @classmethod
    def _parse_optional_strings(cls, value: Any) -> str | None:
        return _parse_optional_str(value)

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = _parse_int(value, default=_DEFAULT_PAGE)
        return max(parsed, 1)

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = _parse_int(value, default=_DEFAULT_LIMIT)
        if parsed < 1:
            return 1
        if parsed > _MAX_LIMIT:
            return _MAX_LIMIT
        return parsed

    @field_validator("get_all", mode="before")
    @classmethod
    def _parse_get_all(cls, value: Any) -> bool:
        return as_bool(value, default=False)

    def to_filters(self) -> InstanceAggregationsFilters:
        """转换为实例容量聚合 filters 对象."""
        return InstanceAggregationsFilters(
            instance_id=self.instance_id,
            db_type=self.db_type,
            period_type=self.period_type,
            start_date=self.start_date,
            end_date=self.end_date,
            page=self.page,
            limit=self.limit,
            get_all=self.get_all,
        )


class CapacityInstancesSummaryQuery(_CapacityInstancesDateRangeMixin):
    """实例容量聚合汇总 query 参数 schema."""

    instance_id: int | None = None
    db_type: str | None = None
    period_type: str | None = None

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int | None:
        return _parse_optional_int(value)

    @field_validator("db_type", "period_type", mode="before")
    @classmethod
    def _parse_optional_strings(cls, value: Any) -> str | None:
        return _parse_optional_str(value)

    def to_filters(self) -> InstanceAggregationsSummaryFilters:
        """转换为实例容量聚合汇总 filters 对象."""
        return InstanceAggregationsSummaryFilters(
            instance_id=self.instance_id,
            db_type=self.db_type,
            period_type=self.period_type,
            start_date=self.start_date,
            end_date=self.end_date,
        )
