"""
实例资源表单服务
"""

from __future__ import annotations

from typing import Any
from collections.abc import Mapping

from app import db
from app.models.instance import Instance
from app.models.credential import Credential
from app.models.tag import Tag
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.utils.data_validator import DataValidator
from app.services.database_type_service import DatabaseTypeService
from app.utils.structlog_config import log_error, log_info


class InstanceFormService(BaseResourceService[Instance]):
    """负责实例创建/编辑的表单服务。

    提供实例的表单校验、数据规范化、标签同步和保存功能。

    Attributes:
        model: 关联的 Instance 模型类。

    """

    model = Instance

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """清理表单数据。

        Args:
            payload: 原始表单数据。

        Returns:
            清理后的数据字典。

        """
        return DataValidator.sanitize_form_data(payload)

    def validate(self, data: dict[str, Any], *, resource: Instance | None) -> ServiceResult[dict[str, Any]]:
        """校验实例数据。

        校验必填字段、端口号、凭据有效性、标签和唯一性。

        Args:
            data: 清理后的数据。
            resource: 已存在的实例（编辑场景），创建时为 None。

        Returns:
            校验结果，成功时返回规范化的数据，失败时返回错误信息。

        """
        is_valid, error = DataValidator.validate_instance_data(data)
        if not is_valid:
            return ServiceResult.fail(error or "表单验证失败")

        normalized = dict(data)
        normalized["name"] = normalized.get("name", "").strip()
        normalized["port"] = int(normalized["port"])
        normalized["database_name"] = (normalized.get("database_name") or "").strip() or None
        normalized["description"] = (normalized.get("description") or "").strip()
        try:
            normalized["credential_id"] = self._resolve_credential_id(normalized.get("credential_id"))
        except ValueError as exc:
            return ServiceResult.fail(str(exc))
        normalized["is_active"] = self._parse_is_active(data, default=(resource.is_active if resource else True))
        normalized["tag_names"] = self._normalize_tag_names(data.get("tag_names"))

        duplicate_query = Instance.query.filter(Instance.name == normalized["name"])
        if resource:
            duplicate_query = duplicate_query.filter(Instance.id != resource.id)
        if duplicate_query.first():
            return ServiceResult.fail("实例名称已存在")

        return ServiceResult.ok(normalized)

    def assign(self, instance: Instance, data: dict[str, Any]) -> None:
        """将数据赋值给实例。

        Args:
            instance: 实例对象。
            data: 已校验的数据。

        Returns:
            None: 属性赋值完成后返回。

        """
        instance.name = data["name"]
        instance.db_type = data["db_type"]
        instance.host = data["host"]
        instance.port = data["port"]
        instance.database_name = data.get("database_name")
        instance.credential_id = data.get("credential_id")
        instance.description = data.get("description")
        instance.is_active = data.get("is_active", True)
        instance.type_specific = instance.type_specific or {}

    def after_save(self, instance: Instance, data: dict[str, Any]) -> None:
        """保存后同步标签并记录日志。

        Args:
            instance: 已保存的实例。
            data: 已校验的数据。

        Returns:
            None: 标签同步与日志记录结束后返回。

        """
        tag_names = data.get("tag_names", [])
        self._sync_tags(instance, tag_names)
        log_info(
            "保存数据库实例",
            module="instances",
            instance_id=instance.id,
            instance_name=instance.name,
            db_type=instance.db_type,
            host=instance.host,
        )

    def build_context(self, *, resource: Instance | None) -> dict[str, Any]:
        """构建模板渲染上下文。

        Args:
            resource: 实例对象，创建时为 None。

        Returns:
            包含凭据、数据库类型和标签选项的上下文字典。

        """
        credentials = Credential.query.filter_by(is_active=True).all()
        database_types = DatabaseTypeService.get_active_types()
        all_tags = Tag.get_active_tags()
        selected_tags = resource.tags if resource else []

        return {
            "credentials": credentials,
            "database_types": database_types,
            "all_tags": all_tags,
            "selected_tags": selected_tags,
            "selected_tag_names": [tag.name for tag in selected_tags],
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _resolve_credential_id(self, credential_raw: Any) -> int | None:
        """解析凭据 ID。

        Args:
            credential_raw: 原始凭据 ID（可能是整数、字符串或列表）。

        Returns:
            解析后的凭据 ID，如果为空则返回 None。

        Raises:
            ValueError: 当凭据 ID 无效或凭据不存在时抛出。

        """
        if credential_raw in (None, "", []):
            return None
        try:
            credential_id = int(credential_raw if not isinstance(credential_raw, list) else credential_raw[-1])
        except (TypeError, ValueError):
            raise ValueError("无效的凭据ID")

        credential = Credential.query.get(credential_id)
        if not credential:
            raise ValueError("凭据不存在")
        return credential_id

    def _normalize_tag_names(self, tag_field: Any) -> list[str]:
        """规范化标签名称列表。

        Args:
            tag_field: 原始标签字段（可能是列表或逗号分隔的字符串）。

        Returns:
            规范化后的标签名称列表。

        """
        if not tag_field:
            return []
        values = tag_field if isinstance(tag_field, list) else str(tag_field).split(",")
        return [value.strip() for value in values if value and value.strip()]

    def _parse_is_active(self, data: Mapping[str, Any], *, default: bool) -> bool:
        """解析 is_active 字段。

        Args:
            data: 表单数据。
            default: 默认值。

        Returns:
            解析后的布尔值。

        """
        value = data.get("is_active", default)
        if isinstance(value, list):
            value = value[-1]
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "on", "yes"}:
                return True
            if normalized in {"0", "false", "off", "no"}:
                return False
            return default
        return bool(value)

    def _create_instance(self) -> Instance:
        """提供实例模型的占位对象，便于沿用基类保存流程。"""

        return Instance(
            name="__pending__",
            db_type="mysql",
            host="placeholder.local",
            port=3306,
            database_name=None,
            credential_id=None,
            description=None,
        )

    def _sync_tags(self, instance: Instance, tag_names: list[str]) -> None:
        """同步实例的标签。

        清除现有标签并添加新标签。

        Args:
            instance: 实例对象。
            tag_names: 标签名称列表。

        Returns:
            None: 标签同步操作完成后返回。

        """
        try:
            instance.tags.clear()
            if not tag_names:
                db.session.commit()
                return

            added = []
            for name in tag_names:
                tag = Tag.get_tag_by_name(name)
                if tag:
                    instance.tags.append(tag)
                    added.append(name)

            db.session.commit()
            if added:
                log_info(
                    "实例标签已更新",
                    module="instances",
                    instance_id=instance.id,
                    tags=added,
                )
        except Exception as exc:
            db.session.rollback()
            log_error(
                "同步实例标签失败",
                module="instances",
                instance_id=getattr(instance, "id", None),
                exception=exc,
            )
