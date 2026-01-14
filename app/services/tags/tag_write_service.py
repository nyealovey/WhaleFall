"""标签写操作 Service.

职责:
- 处理标签的创建/更新/删除编排
- 负责校验与数据规范化
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.core.exceptions import NotFoundError, ValidationError
from app.infra.route_safety import log_with_context
from app.models.tag import Tag
from app.repositories.tags_repository import TagsRepository
from app.schemas.tags import TagBatchDeletePayload, TagUpdatePayload, TagUpsertPayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from collections.abc import Sequence


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

    def __init__(self, repository: TagsRepository | None = None) -> None:
        """初始化写操作服务."""
        self._repository = repository or TagsRepository()

    def create(self, payload: object | None, *, operator_id: int | None = None) -> Tag:
        """创建标签."""
        sanitized = parse_payload(payload, boolean_fields_default_false=["is_active"])
        parsed = validate_or_raise(TagUpsertPayload, sanitized)

        existing = self._repository.get_by_name(parsed.name)
        if existing:
            raise ValidationError("标签代码已存在,请使用其他名称", message_key="VALIDATION_ERROR")

        tag = Tag(
            name=parsed.name,
            display_name=parsed.display_name,
            category=parsed.category,
            color=parsed.color,
            is_active=parsed.is_active,
        )

        try:
            self._repository.add(tag)
        except SQLAlchemyError as exc:
            raise ValidationError("保存失败,请稍后再试", extra={"exception": str(exc)}) from exc

        self._log_create(tag, operator_id=operator_id)
        return tag

    def update(self, tag_id: int, payload: object | None, *, operator_id: int | None = None) -> Tag:
        """更新标签."""
        tag = self._repository.get_by_id(tag_id)
        if not tag:
            raise NotFoundError("标签不存在", extra={"tag_id": tag_id})

        sanitized = parse_payload(payload, boolean_fields_default_false=["is_active"])
        parsed = validate_or_raise(TagUpdatePayload, sanitized)

        existing = self._repository.get_by_name(parsed.name)
        if existing and existing.id != tag.id:
            raise ValidationError("标签代码已存在,请使用其他名称", message_key="VALIDATION_ERROR")

        tag.name = parsed.name
        tag.display_name = parsed.display_name
        tag.category = parsed.category
        if "color" in parsed.model_fields_set and parsed.color is not None:
            tag.color = parsed.color
        if parsed.is_active is not None:
            tag.is_active = parsed.is_active

        try:
            self._repository.add(tag)
        except SQLAlchemyError as exc:
            raise ValidationError("保存失败,请稍后再试", extra={"exception": str(exc)}) from exc

        self._log_update(tag, operator_id=operator_id)
        return tag

    def delete(self, tag_id: int, *, operator_id: int | None = None) -> TagDeleteOutcome:
        """删除标签."""
        tag = self._repository.get_by_id(tag_id)
        if not tag:
            raise NotFoundError("标签不存在", extra={"tag_id": tag_id})

        instance_count = len(cast(Any, tag.instances))
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

    def batch_delete(self, tag_ids: Sequence[int], *, operator_id: int | None = None) -> TagBatchDeleteOutcome:
        """批量删除标签."""
        results: list[dict[str, object]] = []
        has_failure = False

        for raw_id in tag_ids:
            tag_id = raw_id

            tag = self._repository.get_by_id(tag_id)
            if not tag:
                has_failure = True
                results.append({"tag_id": tag_id, "status": "not_found"})
                continue

            instance_count = len(cast(Any, tag.instances))
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

    def batch_delete_from_payload(self, payload: object | None, *, operator_id: int | None = None) -> TagBatchDeleteOutcome:
        """从原始 payload 解析并批量删除标签."""
        sanitized = parse_payload(payload, list_fields=["tag_ids"])
        parsed = validate_or_raise(TagBatchDeletePayload, sanitized)
        return self.batch_delete(parsed.tag_ids, operator_id=operator_id)

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
