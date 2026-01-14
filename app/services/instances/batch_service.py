"""实例批量操作服务,集中处理创建/删除等写操作(不 commit)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import SystemError, ValidationError
from app.models.instance import Instance
from app.repositories.instances_batch_repository import InstancesBatchRepository
from app.schemas.instances import InstanceCreatePayload, InstancesBatchDeletePayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils


def _init_deletion_stats() -> dict[str, int]:
    """初始化删除统计字典.

    Returns:
        包含所有删除计数器的字典,初始值均为 0.

    """
    return {
        "deleted_assignments": 0,
        "deleted_account_permissions": 0,
        "deleted_sync_records": 0,
        "deleted_change_logs": 0,
        "deleted_instance_accounts": 0,
        "deleted_instance_databases": 0,
        "deleted_instance_size_stats": 0,
        "deleted_instance_size_aggregations": 0,
        "deleted_database_size_stats": 0,
        "deleted_database_size_aggregations": 0,
        "deleted_tag_links": 0,
    }


class InstanceBatchCreationService:
    """负责批量创建实例的服务.

    提供批量创建实例的功能,包括数据校验、重复检查和批量插入.
    """

    def __init__(self, repository: InstancesBatchRepository | None = None) -> None:
        self._repository = repository or InstancesBatchRepository()

    def create_instances(
        self,
        instances_data: Sequence[Mapping[str, object]],
        *,
        operator_id: int | None = None,
    ) -> dict[str, Any]:
        """批量创建实例.

        校验实例数据,检查重复名称,批量插入数据库.

        Args:
            instances_data: 实例数据列表,每个元素包含实例的字段信息.
            operator_id: 操作者用户 ID,可选.

        Returns:
            包含创建结果的字典,格式如下:
            {
                'created_count': 3,
                'errors': [],
                'duplicate_names': [],
                'skipped_existing_names': [],
                'message': '成功创建 3 个实例'
            }

        Raises:
            ValidationError: 当实例数据为空时抛出.
            SystemError: 当数据库操作失败时抛出.

        """
        self._ensure_payload_exists(instances_data)
        valid_data, validation_errors = self._validate_batch_payloads(instances_data)
        errors: list[str] = list(validation_errors)

        duplicate_names = self._find_duplicate_names(valid_data)
        if duplicate_names:
            errors.append(f"存在重复实例名称: {', '.join(duplicate_names)}")

        existing_names = self._find_existing_names(valid_data, duplicate_names)
        if existing_names:
            errors.append(f"以下实例名称已存在: {', '.join(sorted(existing_names))}")

        created_count = 0

        try:
            created_count, additional_errors = self._create_valid_instances(
                valid_data,
                duplicate_names,
                existing_names,
                operator_id,
            )
            errors.extend(additional_errors)

            message = f"成功创建 {created_count} 个实例"

            return {
                "created_count": created_count,
                "errors": errors,
                "duplicate_names": duplicate_names,
                "skipped_existing_names": sorted(existing_names),
                "message": message,
            }
        except SQLAlchemyError as exc:
            log_error("batch_create_instance_failed", module="instances", error=str(exc))
            msg = "批量创建实例失败"
            raise SystemError(msg) from exc

    @staticmethod
    def _validate_batch_payloads(
        instances_data: Sequence[Mapping[str, object]],
    ) -> tuple[list[InstanceCreatePayload], list[str]]:
        valid_data: list[InstanceCreatePayload] = []
        errors: list[str] = []
        for index, payload in enumerate(instances_data, start=1):
            try:
                params = validate_or_raise(InstanceCreatePayload, payload)
            except ValidationError as exc:
                errors.append(f"第{index}条数据: {exc}")
                continue
            valid_data.append(params)
        return valid_data, errors

    @staticmethod
    def _ensure_payload_exists(instances_data: Sequence[Mapping[str, object]]) -> None:
        """确保入参非空."""
        if not instances_data:
            msg = "请提供实例数据"
            raise ValidationError(msg)

    @staticmethod
    def _find_duplicate_names(valid_data: Sequence[InstanceCreatePayload]) -> list[str]:
        """定位 payload 内部的重复名称."""
        name_counter = Counter(
            item.name.strip()
            for item in valid_data
            if item.name is not None and str(item.name).strip()
        )
        return sorted({name for name, count in name_counter.items() if name and count > 1})

    def _find_existing_names(
        self,
        valid_data: Sequence[InstanceCreatePayload],
        duplicate_names: list[str],
    ) -> set[str]:
        """查找数据库中已存在的实例名."""
        payload_names = [
            item.name for item in valid_data if item.name and item.name not in duplicate_names
        ]
        if not payload_names:
            return set()
        return self._repository.fetch_existing_instance_names(payload_names)

    def _create_valid_instances(
        self,
        valid_data: Sequence[InstanceCreatePayload],
        duplicate_names: list[str],
        existing_names: set[str],
        operator_id: int | None,
    ) -> tuple[int, list[str]]:
        """创建通过校验的实例并收集错误."""
        created_count = 0
        errors: list[str] = []

        for index, payload in enumerate(valid_data, start=1):
            name = payload.name
            if not name or name in duplicate_names or name in existing_names:
                continue

            try:
                instance = Instance(
                    name=payload.name,
                    db_type=payload.db_type,
                    host=payload.host,
                    port=payload.port,
                    database_name=payload.database_name,
                    description=payload.description or None,
                    credential_id=payload.credential_id,
                )
            except ValidationError as exc:
                errors.append(f"第 {index} 个实例数据无效: {exc}")
                continue

            self._repository.add_instance(instance)
            created_count += 1
            log_info(
                "batch_create_instance",
                module="instances",
                operator_id=operator_id,
                instance_name=instance.name,
                db_type=instance.db_type,
                host=instance.host,
            )

        return created_count, errors


class InstanceBatchDeletionService:
    """负责批量删除实例及其关联数据的服务.

    提供批量删除实例的功能,包括级联删除所有关联数据.
    """

    def __init__(self, repository: InstancesBatchRepository | None = None) -> None:
        self._repository = repository or InstancesBatchRepository()

    def delete_instances_from_payload(
        self,
        payload: object | None,
        *,
        operator_id: int | None = None,
    ) -> dict[str, Any]:
        """从原始 payload 解析并批量删除实例."""
        sanitized = parse_payload(payload or {}, list_fields=["instance_ids"])
        parsed = validate_or_raise(InstancesBatchDeletePayload, sanitized)
        return self.delete_instances(
            parsed.instance_ids,
            operator_id=operator_id,
            deletion_mode=parsed.deletion_mode,
        )

    def delete_instances(
        self,
        instance_ids: Sequence[int],
        *,
        operator_id: int | None = None,
        deletion_mode: Literal["soft", "hard"] = "hard",
    ) -> dict[str, Any]:
        """批量删除实例.

        支持软删除（移入回收站）与硬删除（物理删除）两种模式：

        - soft：仅设置 instances.deleted_at，保留关联数据，支持恢复。
        - hard：物理删除实例及其关联数据（不可恢复）。

        Args:
            instance_ids: 实例 ID 列表.
            operator_id: 操作者用户 ID,可选.
            deletion_mode: 删除模式，soft/hard.

        Returns:
            包含删除统计的字典,格式如下:
            {
                'deleted_count': 2,
                'deleted_assignments': 10,
                'deleted_account_permissions': 50,
                'deleted_sync_records': 5,
                'deleted_change_logs': 20,
                'deleted_instance_accounts': 30,
                'deleted_instance_databases': 15,
                'deleted_instance_size_stats': 100,
                'deleted_instance_size_aggregations': 50,
                'deleted_database_size_stats': 200,
                'deleted_database_size_aggregations': 100,
                'deleted_tag_links': 5,
                'missing_instance_ids': [],
                'deleted_sync_data': 50
            }

        Raises:
            ValidationError: 当实例 ID 列表为空或无效时抛出.
            SystemError: 当数据库操作失败时抛出.

        """
        if not instance_ids:
            msg = "请选择要删除的实例"
            raise ValidationError(msg)

        if deletion_mode not in {"soft", "hard"}:
            msg = "删除模式无效"
            raise ValidationError(msg)

        try:
            unique_ids = sorted({int(i) for i in instance_ids})
        except (TypeError, ValueError) as exc:
            msg = "实例ID列表无效"
            raise ValidationError(msg) from exc
        instances = self._repository.list_instances_by_ids(unique_ids)
        found_ids = {instance.id for instance in instances}
        missing_ids = [instance_id for instance_id in unique_ids if instance_id not in found_ids]

        stats = _init_deletion_stats()
        deleted_count = 0

        try:
            now_ts = time_utils.now()
            for instance in instances:
                if deletion_mode == "soft":
                    if not instance.deleted_at:
                        instance.deleted_at = now_ts
                    self._repository.save_instance(instance)
                    deleted_count += 1
                    log_info(
                        "batch_soft_delete_instance",
                        module="instances",
                        operator_id=operator_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        db_type=instance.db_type,
                        host=instance.host,
                    )
                else:
                    per_stats = self._delete_single_instance(instance)
                    for key, value in per_stats.items():
                        stats[key] += value

                    self._repository.delete_instance(instance)
                    deleted_count += 1

                    log_info(
                        "batch_delete_instance",
                        module="instances",
                        operator_id=operator_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        db_type=instance.db_type,
                        host=instance.host,
                    )

            result: dict[str, Any] = dict(stats)
            result["deleted_count"] = deleted_count
            result["missing_instance_ids"] = missing_ids
            result["deleted_sync_data"] = stats["deleted_account_permissions"]
            result["deletion_mode"] = deletion_mode

        except SQLAlchemyError as exc:
            log_error("batch_delete_instance_failed", module="instances", error=str(exc))
            msg = "批量删除实例失败"
            raise SystemError(msg) from exc
        else:
            return result

    def _delete_single_instance(self, instance: Instance) -> dict[str, int]:
        """删除单个实例的所有关联数据.

        Args:
            instance: 要删除的实例对象.

        Returns:
            包含各类关联数据删除数量的字典.

        """
        return self._repository.delete_related_data_for_instance(instance_id=instance.id)
