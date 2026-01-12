"""实例写操作 Service.

职责:
- 处理实例的创建/更新/删除/恢复编排
- 负责校验与数据规范化
- 调用 repository 执行 add/delete/flush
- 不返回 Response, 不 commit
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from app.errors import ConflictError, ValidationError
from app.models.instance import Instance
from app.repositories.credentials_repository import CredentialsRepository
from app.repositories.instances_repository import InstancesRepository
from app.repositories.tags_repository import TagsRepository
from app.schemas.instances import InstanceCreatePayload, InstanceUpdatePayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils


@dataclass(slots=True)
class InstanceSoftDeleteOutcome:
    """实例软删除结果."""

    instance: Instance
    deletion_mode: Literal["soft"]


@dataclass(slots=True)
class InstanceRestoreOutcome:
    """实例恢复结果."""

    instance: Instance
    restored: bool


class InstanceWriteService:
    """实例写操作服务."""

    def __init__(
        self,
        repository: InstancesRepository | None = None,
        credentials_repository: CredentialsRepository | None = None,
    ) -> None:
        """初始化写操作服务."""
        self._repository = repository or InstancesRepository()
        self._credentials_repository = credentials_repository or CredentialsRepository()

    def create(self, payload: Mapping[str, object] | None, *, operator_id: int | None = None) -> Instance:
        """创建实例."""
        sanitized = parse_payload(
            payload or {},
            list_fields=["tag_names"],
            boolean_fields_default_false=["is_active"],
        )
        params = validate_or_raise(InstanceCreatePayload, sanitized)

        name = params.name
        db_type_value = params.db_type
        host = params.host
        port = params.port
        database_name = params.database_name
        description = params.description
        credential_id = self._resolve_create_credential_id(params.credential_id)
        is_active = params.is_active
        tag_names = [str(item) for item in params.tag_names]

        existing_instance = self._repository.get_by_name(name)
        if existing_instance:
            raise ConflictError("实例名称已存在")

        instance = Instance(
            name=name,
            db_type=db_type_value,
            host=host,
            port=port,
            database_name=database_name,
            credential_id=credential_id,
            description=description,
            is_active=is_active,
        )

        self._repository.add(instance)
        self._sync_tags(instance, tag_names)
        log_info(
            "创建数据库实例",
            module="instances",
            user_id=operator_id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
            port=instance.port,
        )
        return instance

    def update(
        self,
        instance_id: int,
        payload: Mapping[str, object] | None,
        *,
        operator_id: int | None = None,
    ) -> Instance:
        """更新实例."""
        instance = self._repository.get_active_instance(instance_id)
        sanitized = parse_payload(
            payload or {},
            list_fields=["tag_names"],
            boolean_fields_default_false=["is_active"],
        )
        params = validate_or_raise(InstanceUpdatePayload, sanitized)

        if "credential_id" in params.model_fields_set and params.credential_id is not None:
            credential = self._credentials_repository.get_by_id(int(params.credential_id))
            if not credential:
                raise ValidationError("凭据不存在")

        existing_instance = self._repository.get_by_name_excluding_id(params.name, exclude_instance_id=instance_id)
        if existing_instance:
            raise ConflictError("实例名称已存在")

        instance.name = params.name
        instance.db_type = params.db_type
        instance.host = params.host
        instance.port = params.port

        if "credential_id" in params.model_fields_set:
            instance.credential_id = params.credential_id

        if "description" in params.model_fields_set:
            instance.description = params.description or ""

        if "database_name" in params.model_fields_set:
            instance.database_name = params.database_name

        if params.is_active is not None:
            instance.is_active = params.is_active

        self._repository.add(instance)
        tag_names = [str(item) for item in params.tag_names]
        self._sync_tags(instance, tag_names)
        log_info(
            "更新数据库实例",
            module="instances",
            user_id=operator_id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=str(instance.db_type) if instance.db_type else None,
            host=instance.host,
            port=instance.port,
            is_active=instance.is_active,
        )
        return instance

    def soft_delete(self, instance_id: int, *, operator_id: int | None = None) -> InstanceSoftDeleteOutcome:
        """软删除实例."""
        instance = self._repository.get_instance_or_404(instance_id)
        if not instance.deleted_at:
            instance.deleted_at = time_utils.now()

        self._repository.add(instance)
        log_info(
            "移入回收站",
            module="instances",
            user_id=operator_id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
        )
        return InstanceSoftDeleteOutcome(instance=instance, deletion_mode="soft")

    def restore(self, instance_id: int, *, operator_id: int | None = None) -> InstanceRestoreOutcome:
        """恢复实例."""
        instance = self._repository.get_instance_or_404(instance_id)
        if not instance.deleted_at:
            return InstanceRestoreOutcome(instance=instance, restored=False)

        instance.deleted_at = None
        self._repository.add(instance)
        log_info(
            "恢复数据库实例",
            module="instances",
            user_id=operator_id,
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
        )
        return InstanceRestoreOutcome(instance=instance, restored=True)

    @staticmethod
    def _sync_tags(instance: Instance, tag_names: list[str]) -> None:
        TagsRepository().sync_instance_tags(instance, tag_names)

    def _resolve_create_credential_id(self, value: object) -> int | None:
        if value is None:
            return None
        try:
            credential_id = int(cast(Any, value))
        except (TypeError, ValueError) as exc:
            raise ValidationError("无效的凭据ID") from exc

        credential = self._credentials_repository.get_by_id(credential_id)
        if not credential:
            raise ValidationError("凭据不存在")

        return credential_id
