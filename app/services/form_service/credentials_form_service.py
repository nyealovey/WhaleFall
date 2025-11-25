"""
凭据资源表单服务
"""

from __future__ import annotations

from typing import Any, Mapping

from flask_login import current_user

from app.constants import CREDENTIAL_TYPES, DATABASE_TYPES
from app.models.credential import Credential
from app.services.form_service.resource_form_service import BaseResourceService, ServiceResult
from app.utils.data_validator import (
    sanitize_form_data,
    validate_credential_type,
    validate_db_type,
    validate_password,
    validate_required_fields,
    validate_username,
)
from app.utils.structlog_config import log_info


class CredentialFormService(BaseResourceService[Credential]):
    """负责凭据创建与编辑的服务。

    提供凭据的表单校验、数据规范化和保存功能。

    Attributes:
        model: 关联的 Credential 模型类。
    """

    model = Credential

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """清理表单数据。

        Args:
            payload: 原始表单数据。

        Returns:
            清理后的数据字典。
        """
        return sanitize_form_data(payload or {})

    def validate(self, data: dict[str, Any], *, resource: Credential | None) -> ServiceResult[dict[str, Any]]:
        """校验凭据数据。

        校验必填字段、用户名格式、密码强度、数据库类型和凭据类型。

        Args:
            data: 清理后的数据。
            resource: 已存在的凭据实例（编辑场景），创建时为 None。

        Returns:
            校验结果，成功时返回规范化的数据，失败时返回错误信息。
        """
        require_password = resource is None

        required_fields = ["name", "credential_type", "username"]
        if require_password:
            required_fields.append("password")

        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return ServiceResult.fail(validation_error)

        username_error = validate_username(data.get("username"))
        if username_error:
            return ServiceResult.fail(username_error)

        password_value = data.get("password")
        if require_password or password_value:
            password_error = validate_password(password_value)
            if password_error:
                return ServiceResult.fail(password_error)

        if data.get("db_type"):
            db_type_error = validate_db_type(data.get("db_type"))
            if db_type_error:
                return ServiceResult.fail(db_type_error)

        credential_type_error = validate_credential_type(data.get("credential_type"))
        if credential_type_error:
            return ServiceResult.fail(credential_type_error)

        normalized = self._normalize_payload(data, resource)

        # 唯一性校验
        query = Credential.query.filter(Credential.name == normalized["name"])
        if resource:
            query = query.filter(Credential.id != resource.id)
        if query.first():
            return ServiceResult.fail("凭据名称已存在，请使用其他名称")

        return ServiceResult.ok(normalized)

    def assign(self, instance: Credential, data: dict[str, Any]) -> None:
        """将数据赋值给凭据实例。

        Args:
            instance: 凭据实例。
            data: 已校验的数据。
        """
        instance.name = data["name"]
        instance.credential_type = data["credential_type"]
        instance.username = data["username"]
        instance.db_type = data["db_type"]
        instance.description = data["description"]
        instance.is_active = data["is_active"]

        if data.get("password"):
            instance.set_password(data["password"])

    def after_save(self, instance: Credential, data: dict[str, Any]) -> None:
        """保存后记录日志。

        Args:
            instance: 已保存的凭据实例。
            data: 已校验的数据。
        """
        action = "创建数据库凭据" if data.get("_is_create") else "更新数据库凭据"
        log_info(
            action,
            module="credentials",
            user_id=getattr(current_user, "id", None),
            credential_id=instance.id,
            credential_name=instance.name,
            credential_type=instance.credential_type,
            db_type=instance.db_type,
            is_active=instance.is_active,
        )

    def build_context(self, *, resource: Credential | None) -> dict[str, Any]:
        """构建模板渲染上下文。

        Args:
            resource: 凭据实例，创建时为 None。

        Returns:
            包含凭据类型和数据库类型选项的上下文字典。
        """
        return {
            "credential_type_options": CREDENTIAL_TYPES,
            "db_type_options": DATABASE_TYPES,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _normalize_payload(self, data: Mapping[str, Any], resource: Credential | None) -> dict[str, Any]:
        """规范化表单数据。

        Args:
            data: 原始数据。
            resource: 已存在的凭据实例，创建时为 None。

        Returns:
            规范化后的数据字典。
        """
        normalized: dict[str, Any] = {}
        normalized["name"] = (data.get("name") or (resource.name if resource else "")).strip()
        normalized["credential_type"] = (data.get("credential_type") or (resource.credential_type if resource else "")).strip()
        normalized["username"] = (data.get("username") or (resource.username if resource else "")).strip()

        db_type_raw = data.get("db_type") if data.get("db_type") is not None else (resource.db_type if resource else "")
        normalized["db_type"] = (db_type_raw or "").strip() or None

        description_raw = data.get("description")
        if description_raw is None and resource:
            description_raw = resource.description
        normalized["description"] = (description_raw or "").strip() or None

        normalized["password"] = (data.get("password") or "").strip()
        normalized["is_active"] = self._coerce_bool(
            data.get("is_active"),
            default=(resource.is_active if resource else True),
        )

        normalized["_is_create"] = resource is None
        return normalized

    def _coerce_bool(self, value: Any, *, default: bool) -> bool:
        """将值转换为布尔类型。

        Args:
            value: 待转换的值。
            default: 默认值。

        Returns:
            转换后的布尔值。
        """
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
            return default
        return default

    def upsert(self, payload: Mapping[str, Any], resource: Credential | None = None) -> ServiceResult[Credential]:
        """执行凭据创建或更新操作。

        Args:
            payload: 原始表单数据。
            resource: 已存在的凭据实例（编辑场景），创建时为 None。

        Returns:
            操作结果，成功时返回凭据实例，失败时返回错误信息。
        """
        result = super().upsert(payload, resource)
        if not result.success and result.extra.get("exception"):
            # 将数据库异常转换为用户可读的信息
            message = self._normalize_db_error(str(result.extra["exception"]))
            return ServiceResult.fail(message)
        return result

    def _normalize_db_error(self, message: str) -> str:
        """将数据库异常转换为用户可读的错误信息。

        Args:
            message: 数据库异常信息。

        Returns:
            用户可读的错误信息。
        """
        lowered = message.lower()
        if "unique constraint failed" in lowered or "duplicate key value" in lowered:
            return "凭据名称已存在，请使用其他名称"
        if "not null constraint failed" in lowered:
            return "必填字段不能为空"
        return "保存凭据失败，请稍后再试"
