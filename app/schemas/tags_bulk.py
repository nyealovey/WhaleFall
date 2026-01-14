"""Tags bulk actions 写路径 schema."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from app.core.constants.system_constants import ErrorMessages
from app.schemas.base import PayloadSchema


def _parse_id_list(value: Any) -> list[int]:
    if value is None:
        return []
    raw_items = list(value) if isinstance(value, (list, tuple, set)) else [value]

    parsed: list[int] = []
    for item in raw_items:
        if isinstance(item, bool):
            raise ValueError("ID格式错误: bool")  # noqa: TRY004
        try:
            parsed.append(int(item))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"ID格式错误: {exc}") from exc
    return parsed


class TagsBulkAssignPayload(PayloadSchema):
    """批量分配/移除标签 payload."""

    instance_ids: list[int] = Field(default_factory=list)
    tag_ids: list[int] = Field(default_factory=list)

    @field_validator("instance_ids", mode="before")
    @classmethod
    def _parse_instance_ids(cls, value: Any) -> list[int]:
        return _parse_id_list(value)

    @field_validator("tag_ids", mode="before")
    @classmethod
    def _parse_tag_ids(cls, value: Any) -> list[int]:
        return _parse_id_list(value)

    @model_validator(mode="after")
    def _validate_required_fields(self) -> TagsBulkAssignPayload:
        if not self.instance_ids or not self.tag_ids:
            raise ValueError(ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids, tag_ids"))
        return self


class TagsBulkInstanceTagsPayload(PayloadSchema):
    """批量获取实例标签集合 payload."""

    instance_ids: list[int] = Field(default_factory=list)

    @field_validator("instance_ids", mode="before")
    @classmethod
    def _parse_instance_ids(cls, value: Any) -> list[int]:
        return _parse_id_list(value)

    @model_validator(mode="after")
    def _validate_required_fields(self) -> TagsBulkInstanceTagsPayload:
        if not self.instance_ids:
            raise ValueError(ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids"))
        return self


class TagsBulkRemoveAllPayload(PayloadSchema):
    """批量移除所有标签 payload."""

    instance_ids: list[int] = Field(default_factory=list)

    @field_validator("instance_ids", mode="before")
    @classmethod
    def _parse_instance_ids(cls, value: Any) -> list[int]:
        return _parse_id_list(value)

    @model_validator(mode="after")
    def _validate_required_fields(self) -> TagsBulkRemoveAllPayload:
        if not self.instance_ids:
            raise ValueError(ErrorMessages.MISSING_REQUIRED_FIELDS.format(fields="instance_ids"))
        return self
