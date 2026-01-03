"""标签写操作 Service.

职责:
- 处理标签的创建/更新/删除编排
- 负责校验与数据规范化
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.constants.colors import ThemeColors
from app.errors import NotFoundError, ValidationError
from app.models.tag import Tag
from app.repositories.tags_repository import TagsRepository
from app.types.converters import as_bool, as_str
from app.utils.data_validator import DataValidator
from app.utils.route_safety import log_with_context
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.types import MutablePayloadDict, PayloadMapping, ResourcePayload


@dataclass(slots=True)
class TagDeleteOutcome:
    """标签删除结果."""

    tag_id: int
    display_name: str
    status: Literal["deleted", "in_use"]
    instance_count: int


@dataclass(slots=True)
class TagBatchDeleteOutcome:
    """标签批量删除结果."""

    results: list[dict[str, object]]
    has_failure: bool


class TagWriteService:
    """标签写操作服务."""

    NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

    def __init__(self, repository: TagsRepository | None = None) -> None:
        """初始化写操作服务."""
        self._repository = repository or TagsRepository()

    def create(self, payload: ResourcePayload, *, operator_id: int | None = None) -> Tag:
        """创建标签."""
        sanitized = self._sanitize(payload)
        normalized = self._validate_and_normalize(sanitized, resource=None)

        tag = Tag(
            name=cast(str, normalized["name"]),
            display_name=cast(str, normalized["display_name"]),
            category=cast(str, normalized["category"]),
            color=cast(str, normalized["color"]),
            is_active=cast(bool, normalized["is_active"]),
        )

        try:
            self._repository.add(tag)
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise ValidationError("保存失败,请稍后再试", extra={"exception": str(exc)}) from exc

        self._log_create(tag, operator_id=operator_id)
        return tag

    def update(self, tag_id: int, payload: ResourcePayload, *, operator_id: int | None = None) -> Tag:
        """更新标签."""
        tag = self._repository.get_by_id(tag_id)
        if not tag:
            raise NotFoundError("标签不存在", extra={"tag_id": tag_id})

        sanitized = self._sanitize(payload)
        normalized = self._validate_and_normalize(sanitized, resource=tag)
        self._assign(tag, normalized)

        try:
            self._repository.add(tag)
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise ValidationError("保存失败,请稍后再试", extra={"exception": str(exc)}) from exc

        self._log_update(tag, operator_id=operator_id)
        return tag

    def delete(self, tag_id: int, *, operator_id: int | None = None) -> TagDeleteOutcome:
        """删除标签."""
        tag = self._repository.get_by_id(tag_id)
        if not tag:
            raise NotFoundError("标签不存在", extra={"tag_id": tag_id})

        instance_count = len(tag.instances)
        if instance_count > 0:
            return TagDeleteOutcome(
                tag_id=tag_id,
                display_name=tag.display_name,
                status="in_use",
                instance_count=instance_count,
            )

        self._repository.delete(tag)
        self._log_delete(tag, operator_id=operator_id)
        return TagDeleteOutcome(
            tag_id=tag_id,
            display_name=tag.display_name,
            status="deleted",
            instance_count=0,
        )

    def batch_delete(self, tag_ids: Sequence[object], *, operator_id: int | None = None) -> TagBatchDeleteOutcome:
        """批量删除标签."""
        results: list[dict[str, object]] = []
        has_failure = False

        for raw_id in tag_ids:
            try:
                tag_id = int(raw_id)
            except (ValueError, TypeError):
                has_failure = True
                results.append({"tag_id": raw_id, "status": "invalid_id"})
                continue

            tag = self._repository.get_by_id(tag_id)
            if not tag:
                has_failure = True
                results.append({"tag_id": tag_id, "status": "not_found"})
                continue

            instance_count = len(tag.instances)
            if instance_count > 0:
                has_failure = True
                results.append(
                    {
                        "tag_id": tag_id,
                        "status": "in_use",
                        "instance_count": instance_count,
                    },
                )
                continue

            try:
                with db.session.begin_nested():
                    self._repository.delete(tag)
                    db.session.flush()
                    self._log_delete(tag, operator_id=operator_id)
                results.append({"tag_id": tag_id, "status": "deleted"})
            except SQLAlchemyError as exc:  # pragma: no cover - 逐条记录方便排查
                has_failure = True
                log_with_context(
                    "warning",
                    "批量删除标签失败",
                    module="tags",
                    action="batch_delete_tags",
                    context={"tag_id": tag_id},
                    extra={"error_message": str(exc)},
                    include_actor=True,
                )
                results.append({"tag_id": tag_id, "status": "error", "message": str(exc)})

        return TagBatchDeleteOutcome(results=results, has_failure=has_failure)

    @staticmethod
    def _sanitize(payload: PayloadMapping) -> MutablePayloadDict:
        return cast("MutablePayloadDict", DataValidator.sanitize_form_data(payload or {}))

    def _validate_and_normalize(self, data: MutablePayloadDict, *, resource: Tag | None) -> MutablePayloadDict:
        validation_error = DataValidator.validate_required_fields(data, ["name", "display_name", "category"])
        if validation_error:
            raise ValidationError(validation_error, message_key="VALIDATION_ERROR")

        normalized = self._normalize_payload(data, resource)

        name_value = cast(str, normalized["name"])
        color_value = cast(str, normalized["color"])

        if not self.NAME_PATTERN.match(name_value):
            raise ValidationError("标签代码仅支持字母、数字、下划线或中划线", message_key="VALIDATION_ERROR")

        if not ThemeColors.is_valid_color(color_value):
            raise ValidationError(f"无效的颜色选择: {color_value}", message_key="VALIDATION_ERROR")

        existing = self._repository.get_by_name(name_value)
        if existing and (resource is None or existing.id != resource.id):
            raise ValidationError("标签代码已存在,请使用其他名称", message_key="VALIDATION_ERROR")

        return normalized

    @staticmethod
    def _normalize_payload(data: PayloadMapping, resource: Tag | None) -> MutablePayloadDict:
        normalized: MutablePayloadDict = {}
        normalized["name"] = as_str(
            data.get("name"),
            default=resource.name if resource else "",
        ).strip()
        normalized["display_name"] = as_str(
            data.get("display_name"),
            default=resource.display_name if resource else "",
        ).strip()
        normalized["category"] = as_str(
            data.get("category"),
            default=resource.category if resource else "",
        ).strip()
        normalized["color"] = (
            as_str(data.get("color"), default=(resource.color if resource else "primary")).strip() or "primary"
        )
        normalized["is_active"] = as_bool(
            data.get("is_active"),
            default=resource.is_active if resource else True,
        )
        return normalized

    @staticmethod
    def _assign(tag: Tag, normalized: PayloadMapping) -> None:
        tag.name = as_str(normalized.get("name")).strip()
        tag.display_name = as_str(normalized.get("display_name")).strip()
        tag.category = as_str(normalized.get("category")).strip()
        tag.color = as_str(normalized.get("color"), default="primary").strip() or "primary"
        tag.is_active = as_bool(normalized.get("is_active"), default=True)

    @staticmethod
    def _log_create(tag: Tag, *, operator_id: int | None) -> None:
        log_info(
            "标签创建成功",
            module="tags",
            user_id=operator_id,
            tag_id=tag.id,
            name=tag.name,
            category=tag.category,
            color=tag.color,
            is_active=tag.is_active,
        )

    @staticmethod
    def _log_update(tag: Tag, *, operator_id: int | None) -> None:
        log_info(
            "标签更新成功",
            module="tags",
            user_id=operator_id,
            tag_id=tag.id,
            name=tag.name,
            category=tag.category,
            color=tag.color,
            is_active=tag.is_active,
        )

    @staticmethod
    def _log_delete(tag: Tag, *, operator_id: int | None) -> None:
        log_info(
            "标签删除成功",
            module="tags",
            user_id=operator_id,
            tag_id=tag.id,
            name=tag.name,
            display_name=tag.display_name,
        )
