"""数据库相关 query 参数 schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.core.constants.validation_limits import DATABASE_TABLE_SIZES_LIMIT_MAX
from app.core.types.common_filter_options import CommonDatabasesOptionsFilters
from app.core.types.instance_database_sizes import InstanceDatabaseSizesQuery
from app.core.types.instance_database_table_sizes import InstanceDatabaseTableSizesQuery
from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_optional_int, parse_text
from app.utils.payload_converters import as_bool
from app.utils.time_utils import time_utils

_DEFAULT_PAGE = 1


def _parse_raw_optional_str(value: Any) -> str | None:
    """Parse optional string without stripping to preserve legacy behavior."""
    return value if isinstance(value, str) else None


def _parse_tags(value: Any) -> list[str]:
    """Parse tags as appendable list and split comma segments (strip, drop blanks)."""
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = [item for item in value if isinstance(item, str)]
    else:
        return []

    output: list[str] = []
    for item in candidates:
        for segment in item.split(","):
            cleaned = segment.strip()
            if cleaned:
                output.append(cleaned)
    return output


def _parse_optional_date(value: Any, *, param_name: str) -> date | None:
    """Parse YYYY-MM-DD as China date (strict)."""
    if value is None:
        return None

    if isinstance(value, datetime):
        parsed_dt = time_utils.to_china(value)
        if not parsed_dt:
            raise ValueError(f"{param_name} 参数必须为 YYYY-MM-DD")
        return parsed_dt.date()

    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise TypeError(f"{param_name} 参数必须为 YYYY-MM-DD")

    cleaned = value.strip()
    if not cleaned:
        return None

    parsed_dt = time_utils.to_china(cleaned + "T00:00:00")
    if not parsed_dt:
        raise ValueError(f"{param_name} 参数必须为 YYYY-MM-DD")
    return parsed_dt.date()


class DatabasesOptionsQuery(PayloadSchema):
    """`/databases/options` query 参数 schema."""

    instance_id: int
    page: int = 1
    limit: int = 100
    offset: str | None = None  # legacy param - explicitly rejected

    @model_validator(mode="after")
    def _reject_offset(self) -> DatabasesOptionsQuery:
        if self.offset is not None:
            raise ValueError("分页参数已统一为 page/limit，不支持 offset")
        return self

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int:
        parsed = parse_int(value, default=0)
        if parsed <= 0:
            raise ValueError("instance_id 为必填参数")
        return parsed

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_PAGE)
        if parsed < 1:
            raise ValueError("page 参数必须为正整数")
        return parsed

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = parse_int(value, default=100)
        if parsed < 1:
            raise ValueError("limit 参数必须为正整数")
        if parsed > 1000:
            raise ValueError("limit 最大为 1000")
        return parsed

    def to_filters(self, *, resolved_instance_id: int | None = None) -> CommonDatabasesOptionsFilters:
        """转换为通用 databases options filters 对象."""
        instance_id = resolved_instance_id if resolved_instance_id is not None else self.instance_id
        offset = (self.page - 1) * self.limit
        return CommonDatabasesOptionsFilters(instance_id=instance_id, limit=self.limit, offset=offset)


class DatabaseLedgersQuery(PayloadSchema):
    """`/databases/ledgers` query 参数 schema."""

    search: str = ""
    db_type: str = "all"
    instance_id: int | None = None
    tags: list[str] = Field(default_factory=list)
    page: int = 1
    limit: int = 20

    @field_validator("search", mode="before")
    @classmethod
    def _parse_search(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str:
        cleaned = parse_text(value)
        return cleaned or "all"

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int | None:
        return parse_optional_int(value)

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, value: Any) -> list[str]:
        return _parse_tags(value)

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_PAGE)
        if parsed < 1:
            raise ValueError("page 参数必须为正整数")
        return parsed

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = parse_int(value, default=20)
        if parsed < 1:
            raise ValueError("limit 参数必须为正整数")
        if parsed > 200:
            raise ValueError("limit 最大为 200")
        return parsed


class DatabaseLedgersExportQuery(PayloadSchema):
    """`/databases/ledgers/exports` query 参数 schema."""

    search: str = ""
    db_type: str = "all"
    instance_id: int | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("search", mode="before")
    @classmethod
    def _parse_search(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str:
        cleaned = parse_text(value)
        return cleaned or "all"

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int | None:
        return parse_optional_int(value)

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, value: Any) -> list[str]:
        return _parse_tags(value)


class DatabasesSizesQuery(PayloadSchema):
    """`/databases/sizes` query 参数 schema."""

    instance_id: int
    start_date: date | None = None
    end_date: date | None = None
    database_name: str | None = None
    latest_only: bool = False
    include_inactive: bool = False
    page: int = 1
    limit: int = 100
    offset: str | None = None  # legacy param - explicitly rejected

    @model_validator(mode="after")
    def _reject_offset(self) -> DatabasesSizesQuery:
        if self.offset is not None:
            raise ValueError("分页参数已统一为 page/limit，不支持 offset")
        return self

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int:
        parsed = parse_int(value, default=0)
        if parsed <= 0:
            raise ValueError("缺少 instance_id")
        return parsed

    @field_validator("start_date", mode="before")
    @classmethod
    def _parse_start_date(cls, value: Any) -> date | None:
        return _parse_optional_date(value, param_name="start_date")

    @field_validator("end_date", mode="before")
    @classmethod
    def _parse_end_date(cls, value: Any) -> date | None:
        return _parse_optional_date(value, param_name="end_date")

    @field_validator("database_name", mode="before")
    @classmethod
    def _parse_database_name(cls, value: Any) -> str | None:
        return _parse_raw_optional_str(value)

    @field_validator("latest_only", mode="before")
    @classmethod
    def _parse_latest_only(cls, value: Any) -> bool:
        return as_bool(value, default=False)

    @field_validator("include_inactive", mode="before")
    @classmethod
    def _parse_include_inactive(cls, value: Any) -> bool:
        return as_bool(value, default=False)

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_PAGE)
        if parsed < 1:
            raise ValueError("page 参数必须为正整数")
        return parsed

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = parse_int(value, default=100)
        if parsed < 1:
            raise ValueError("limit 参数必须为正整数")
        return parsed

    def to_options(self, *, resolved_instance_id: int | None = None) -> InstanceDatabaseSizesQuery:
        """转换为实例数据库容量 options 对象."""
        instance_id = resolved_instance_id if resolved_instance_id is not None else self.instance_id
        offset = (self.page - 1) * self.limit
        return InstanceDatabaseSizesQuery(
            instance_id=instance_id,
            database_name=self.database_name,
            start_date=self.start_date,
            end_date=self.end_date,
            include_inactive=self.include_inactive,
            limit=self.limit,
            offset=offset,
        )


class DatabaseTableSizesQuery(PayloadSchema):
    """`/databases/<id>/tables/sizes` query 参数 schema."""

    schema_name: str | None = None
    table_name: str | None = None
    page: int = 1
    limit: int = 200
    offset: str | None = None  # legacy param - explicitly rejected

    @model_validator(mode="after")
    def _reject_offset(self) -> DatabaseTableSizesQuery:
        if self.offset is not None:
            raise ValueError("分页参数已统一为 page/limit，不支持 offset")
        return self

    @field_validator("schema_name", "table_name", mode="before")
    @classmethod
    def _parse_optional_strings(cls, value: Any) -> str | None:
        return _parse_raw_optional_str(value)

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_PAGE)
        if parsed < 1:
            raise ValueError("page 参数必须为正整数")
        return parsed

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = parse_int(value, default=200)
        if parsed > DATABASE_TABLE_SIZES_LIMIT_MAX:
            raise ValueError(f"limit 最大为 {DATABASE_TABLE_SIZES_LIMIT_MAX}")
        if parsed < 1:
            raise ValueError("limit 参数必须为正整数")
        return parsed

    def to_options(
        self,
        *,
        instance_id: int,
        database_name: str,
    ) -> InstanceDatabaseTableSizesQuery:
        """转换为实例表大小 options 对象."""
        offset = (self.page - 1) * self.limit
        return InstanceDatabaseTableSizesQuery(
            instance_id=instance_id,
            database_name=database_name,
            schema_name=self.schema_name,
            table_name=self.table_name,
            limit=self.limit,
            offset=offset,
        )
