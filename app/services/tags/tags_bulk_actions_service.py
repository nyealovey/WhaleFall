"""Tags bulk actions service.

将 tags bulk endpoints 的批量查询与循环逻辑下沉到 service 层：
- 批量分配标签
- 批量移除标签
- 批量移除所有标签
- 批量获取实例的标签集合
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from app.core.constants.system_constants import ErrorMessages
from app.core.exceptions import NotFoundError, ValidationError
from app.models.instance import Instance
from app.models.tag import Tag
from app.repositories.instances_repository import InstancesRepository
from app.repositories.tags_repository import TagsRepository
from app.schemas.tags_bulk import TagsBulkAssignPayload, TagsBulkInstanceTagsPayload, TagsBulkRemoveAllPayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info


@dataclass(frozen=True, slots=True)
class TagsBulkAssignResult:
    """批量分配标签结果."""

    assigned_count: int


@dataclass(frozen=True, slots=True)
class TagsBulkRemoveResult:
    """批量移除标签结果."""

    removed_count: int


@dataclass(frozen=True, slots=True)
class TagsBulkRemoveAllResult:
    """批量移除所有标签结果."""

    removed_count: int


@dataclass(frozen=True, slots=True)
class TagsBulkInstanceTagsResult:
    """批量查询实例标签集合结果."""

    tags: list[dict[str, object]]
    category_names: dict[str, str]


@dataclass(frozen=True, slots=True)
class TagsBulkAssignOutcome:
    """批量分配标签 endpoint 输出."""

    assigned_count: int
    instance_ids: list[int]
    tag_ids: list[int]


@dataclass(frozen=True, slots=True)
class TagsBulkRemoveOutcome:
    """批量移除标签 endpoint 输出."""

    removed_count: int
    instance_ids: list[int]
    tag_ids: list[int]


@dataclass(frozen=True, slots=True)
class TagsBulkRemoveAllOutcome:
    """批量移除所有标签 endpoint 输出."""

    removed_count: int
    instance_ids: list[int]


@dataclass(frozen=True, slots=True)
class TagsBulkInstanceTagsOutcome:
    """批量查询实例标签集合 endpoint 输出."""

    tags: list[dict[str, object]]
    category_names: dict[str, str]
    instance_ids: list[int]


class TagsBulkActionsService:
    """tags bulk actions 编排服务."""

    def assign_from_payload(self, payload: object | None, *, actor_id: int | None) -> TagsBulkAssignOutcome:
        """从 payload 解析并批量分配标签."""
        sanitized = parse_payload(payload, list_fields=["instance_ids", "tag_ids"])
        if not sanitized:
            raise ValidationError(ErrorMessages.REQUEST_DATA_EMPTY, message_key="REQUEST_DATA_EMPTY")
        parsed = validate_or_raise(TagsBulkAssignPayload, sanitized)
        result = self.assign(instance_ids=parsed.instance_ids, tag_ids=parsed.tag_ids, actor_id=actor_id)
        return TagsBulkAssignOutcome(
            assigned_count=result.assigned_count,
            instance_ids=parsed.instance_ids,
            tag_ids=parsed.tag_ids,
        )

    def remove_from_payload(self, payload: object | None, *, actor_id: int | None) -> TagsBulkRemoveOutcome:
        """从 payload 解析并批量移除指定标签."""
        sanitized = parse_payload(payload, list_fields=["instance_ids", "tag_ids"])
        if not sanitized:
            raise ValidationError(ErrorMessages.REQUEST_DATA_EMPTY, message_key="REQUEST_DATA_EMPTY")
        parsed = validate_or_raise(TagsBulkAssignPayload, sanitized)
        result = self.remove(instance_ids=parsed.instance_ids, tag_ids=parsed.tag_ids, actor_id=actor_id)
        return TagsBulkRemoveOutcome(
            removed_count=result.removed_count,
            instance_ids=parsed.instance_ids,
            tag_ids=parsed.tag_ids,
        )

    def remove_all_from_payload(self, payload: object | None, *, actor_id: int | None) -> TagsBulkRemoveAllOutcome:
        """从 payload 解析并批量移除所有标签."""
        sanitized = parse_payload(payload, list_fields=["instance_ids"])
        if not sanitized:
            raise ValidationError(ErrorMessages.REQUEST_DATA_EMPTY, message_key="REQUEST_DATA_EMPTY")
        parsed = validate_or_raise(TagsBulkRemoveAllPayload, sanitized)
        result = self.remove_all(instance_ids=parsed.instance_ids, actor_id=actor_id)
        return TagsBulkRemoveAllOutcome(
            removed_count=result.removed_count,
            instance_ids=parsed.instance_ids,
        )

    def list_instance_tags_from_payload(self, payload: object | None) -> TagsBulkInstanceTagsOutcome:
        """从 payload 解析并批量查询实例标签集合."""
        sanitized = parse_payload(payload, list_fields=["instance_ids"])
        if not sanitized:
            raise ValidationError(ErrorMessages.REQUEST_DATA_EMPTY, message_key="REQUEST_DATA_EMPTY")
        parsed = validate_or_raise(TagsBulkInstanceTagsPayload, sanitized)
        result = self.list_instance_tags(instance_ids=parsed.instance_ids)
        return TagsBulkInstanceTagsOutcome(
            tags=result.tags,
            category_names=result.category_names,
            instance_ids=parsed.instance_ids,
        )

    @staticmethod
    def _get_instances(instance_ids: list[int]) -> list[Instance]:
        instances = InstancesRepository.list_instances_by_ids(instance_ids)
        if not instances:
            raise NotFoundError("未找到任何实例", extra={"instance_ids": instance_ids})
        return instances

    @staticmethod
    def _get_tags(tag_ids: list[int]) -> list[Tag]:
        tags = TagsRepository.list_tags_by_ids(tag_ids)
        if not tags:
            raise NotFoundError("未找到任何标签", extra={"tag_ids": tag_ids})
        return tags

    def assign(self, *, instance_ids: list[int], tag_ids: list[int], actor_id: int | None) -> TagsBulkAssignResult:
        """为多实例批量分配多标签."""
        instances = self._get_instances(instance_ids)
        tags = self._get_tags(tag_ids)

        log_info(
            "开始批量分配标签",
            module="tags_bulk",
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            found_instances=len(instances),
            found_tags=len(tags),
            user_id=actor_id,
        )

        assigned_count = 0
        for instance in instances:
            tags_relation = cast(Any, instance.tags)
            existing_tag_ids = {cast(int, existing.id) for existing in tags_relation.all()}
            for tag in tags:
                if tag.id not in existing_tag_ids:
                    tags_relation.append(tag)
                    existing_tag_ids.add(tag.id)
                    assigned_count += 1

        log_info(
            "批量分配标签成功",
            module="tags_bulk",
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            assigned_count=assigned_count,
            user_id=actor_id,
        )
        return TagsBulkAssignResult(assigned_count=assigned_count)

    def remove(self, *, instance_ids: list[int], tag_ids: list[int], actor_id: int | None) -> TagsBulkRemoveResult:
        """为多实例批量移除指定标签."""
        instances = self._get_instances(instance_ids)
        tags = self._get_tags(tag_ids)

        removed_count = 0
        for instance in instances:
            tags_relation = cast(Any, instance.tags)
            existing_tag_ids = {cast(int, existing.id) for existing in tags_relation.all()}
            for tag in tags:
                if tag.id in existing_tag_ids:
                    tags_relation.remove(tag)
                    existing_tag_ids.remove(tag.id)
                    removed_count += 1

        log_info(
            "批量移除标签成功",
            module="tags_bulk",
            instance_ids=instance_ids,
            tag_ids=tag_ids,
            removed_count=removed_count,
            user_id=actor_id,
        )
        return TagsBulkRemoveResult(removed_count=removed_count)

    def remove_all(self, *, instance_ids: list[int], actor_id: int | None) -> TagsBulkRemoveAllResult:
        """为多实例批量移除全部标签."""
        instances = self._get_instances(instance_ids)

        total_removed = 0
        for instance in instances:
            tags_relation = cast(Any, instance.tags)
            current_tags = list(tags_relation.all())
            for tag in current_tags:
                tags_relation.remove(tag)
            total_removed += len(current_tags)

        log_info(
            "批量移除所有标签成功",
            module="tags_bulk",
            instance_ids=instance_ids,
            removed_count=total_removed,
            user_id=actor_id,
        )
        return TagsBulkRemoveAllResult(removed_count=total_removed)

    def list_instance_tags(self, *, instance_ids: list[int]) -> TagsBulkInstanceTagsResult:
        """批量获取指定实例集合的标签并集."""
        instances = self._get_instances(instance_ids)

        all_tags: set[Tag] = set()
        for instance in instances:
            tags_relation = cast(Any, instance.tags)
            all_tags.update(tags_relation.all())

        tags_data = [tag.to_dict() for tag in all_tags]
        category_names = {tag.category: tag.category for tag in all_tags if tag.category}
        return TagsBulkInstanceTagsResult(tags=tags_data, category_names=category_names)
