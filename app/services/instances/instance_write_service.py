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
from app.models.credential import Credential
from app.models.instance import Instance
from app.repositories.instances_repository import InstancesRepository
from app.repositories.tags_repository import TagsRepository
from app.types.converters import as_list_of_str
from app.utils.data_validator import DataValidator
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils


@dataclass(slots=True)
class InstanceSoftDeleteOutcome:
    instance: Instance
    deletion_mode: Literal["soft"]


@dataclass(slots=True)
class InstanceRestoreOutcome:
    instance: Instance
    restored: bool


class InstanceWriteService:
    """实例写操作服务."""

    def __init__(self, repository: InstancesRepository | None = None) -> None:
        self._repository = repository or InstancesRepository()

    def create(self, payload: Mapping[str, object] | None, *, operator_id: int | None = None) -> Instance:
        sanitized = self._sanitize(payload or {})
        is_valid, validation_error = DataValidator.validate_instance_data(sanitized)
        if not is_valid:
            raise ValidationError(validation_error)

        tag_names = self._normalize_tag_names(sanitized)

        name = str(sanitized.get("name") or "").strip()
        db_type_raw = sanitized.get("db_type")
        db_type_value = db_type_raw if isinstance(db_type_raw, str) else ""
        host = str(sanitized.get("host") or "").strip()
        description = str(sanitized.get("description") or "").strip()
        database_name_raw = sanitized.get("database_name")
        database_name = None
        if database_name_raw not in (None, ""):
            database_name = str(database_name_raw).strip() or None

        port = self._parse_create_port(sanitized.get("port"))
        credential_id = self._resolve_create_credential_id(sanitized.get("credential_id"))
        is_active = self._parse_is_active_value(sanitized.get("is_active", None), default=True)

        existing_instance = Instance.query.filter_by(name=name).first()
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
        instance = self._repository.get_active_instance(instance_id)
        sanitized = self._sanitize(payload or {})

        is_valid, validation_error = DataValidator.validate_instance_data(sanitized)
        if not is_valid:
            raise ValidationError(validation_error)

        tag_names = self._normalize_tag_names(sanitized)

        credential_raw = sanitized.get("credential_id")
        if credential_raw not in (None, ""):
            credential_id = self._parse_int(credential_raw, field="credential_id")
            credential = Credential.query.get(credential_id)
            if not credential:
                raise ValidationError("凭据不存在")

        existing_instance = Instance.query.filter(
            Instance.name == sanitized.get("name"),
            Instance.id != instance_id,
        ).first()
        if existing_instance:
            raise ConflictError("实例名称已存在")

        instance.name = self._safe_strip(sanitized.get("name", instance.name), instance.name or "")
        instance.db_type = cast("str", sanitized.get("db_type", instance.db_type))
        instance.host = self._safe_strip(sanitized.get("host", instance.host), instance.host or "")

        port_value = sanitized.get("port", instance.port)
        instance.port = self._parse_int(port_value, field="端口", default=instance.port or 0)

        credential_value = sanitized.get("credential_id", instance.credential_id)
        instance.credential_id = (
            self._parse_int(credential_value, field="credential_id") if credential_value not in (None, "") else None
        )

        instance.description = self._safe_strip(
            sanitized.get("description", instance.description),
            instance.description or "",
        )
        database_name_value = sanitized.get("database_name", instance.database_name)
        instance.database_name = self._safe_strip(database_name_value, instance.database_name or "") or None
        instance.is_active = self._parse_is_active_value(
            sanitized.get("is_active", None),
            default=instance.is_active,
        )

        self._repository.add(instance)
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
    def _sanitize(payload: Mapping[str, object]) -> dict[str, object]:
        # 兼容 HTML form 的 MultiDict(getlist),同时保留 JSON list 字段.
        if hasattr(payload, "getlist"):
            return cast(dict[str, object], DataValidator.sanitize_form_data(payload))

        sanitized: dict[str, object] = {}
        for key, value in (payload or {}).items():
            if isinstance(value, str):
                sanitized[key] = value.strip()
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif value is None:
                sanitized[key] = None
            elif isinstance(value, (list, tuple, set)):
                sanitized[key] = [str(item).strip() for item in value]
            else:
                sanitized[key] = str(value).strip()
        return sanitized

    @staticmethod
    def _normalize_tag_names(data: Mapping[str, object]) -> list[str]:
        # 兼容:
        # - HTML form: MultiDict.getlist -> list[str]
        # - JSON: tag_names: ["a","b"]
        # - 兼容旧字段: "a,b"
        return as_list_of_str(cast(Any, data.get("tag_names")))

    @staticmethod
    def _sync_tags(instance: Instance, tag_names: list[str]) -> None:
        TagsRepository().sync_instance_tags(instance, tag_names)

    @staticmethod
    def _parse_create_port(value: object) -> int:
        if not isinstance(value, (str, int)):
            raise ValidationError("端口号格式不正确")
        try:
            return int(cast(Any, value))
        except (TypeError, ValueError) as exc:
            raise ValidationError("端口号格式不正确") from exc

    @staticmethod
    def _resolve_create_credential_id(value: object) -> int | None:
        if value is None:
            return None
        if not isinstance(value, (str, int)):
            raise ValidationError("无效的凭据ID")
        try:
            credential_id = int(cast(Any, value))
        except (TypeError, ValueError) as exc:
            raise ValidationError("无效的凭据ID") from exc

        credential = Credential.query.get(credential_id)
        if not credential:
            raise ValidationError("凭据不存在")

        return credential_id

    @staticmethod
    def _parse_int(value: object | None, *, field: str, default: int | None = None) -> int:
        if value is None or value == "":
            if default is not None:
                return default
            raise ValidationError(f"{field} 必须为整数")
        try:
            return int(cast(Any, value))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} 必须为整数") from exc

    @staticmethod
    def _safe_strip(value: object, default: str = "") -> str:
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return default
        return str(value).strip()

    @staticmethod
    def _parse_is_active_value(value: object, *, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        raise ValidationError("is_active 仅支持布尔类型")
