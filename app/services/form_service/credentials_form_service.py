"""
凭据资源表单服务
"""

from __future__ import annotations

from typing import Any, Mapping

from flask_login import current_user

from app.constants.filter_options import CREDENTIAL_TYPES, DATABASE_TYPES
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
    """负责凭据创建与编辑的服务。"""

    model = Credential

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return sanitize_form_data(payload or {})

    def validate(self, data: dict[str, Any], *, resource: Credential | None) -> ServiceResult[dict[str, Any]]:
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
        instance.name = data["name"]
        instance.credential_type = data["credential_type"]
        instance.username = data["username"]
        instance.db_type = data["db_type"]
        instance.description = data["description"]
        instance.is_active = data["is_active"]

        if data.get("password"):
            instance.set_password(data["password"])

    def after_save(self, instance: Credential, data: dict[str, Any]) -> None:
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
        return {
            "credential_type_options": CREDENTIAL_TYPES,
            "db_type_options": DATABASE_TYPES,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _normalize_payload(self, data: Mapping[str, Any], resource: Credential | None) -> dict[str, Any]:
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
        result = super().upsert(payload, resource)
        if not result.success and result.extra.get("exception"):
            # 将数据库异常转换为用户可读的信息
            message = self._normalize_db_error(str(result.extra["exception"]))
            return ServiceResult.fail(message)
        return result

    def _normalize_db_error(self, message: str) -> str:
        lowered = message.lower()
        if "unique constraint failed" in lowered or "duplicate key value" in lowered:
            return "凭据名称已存在，请使用其他名称"
        if "not null constraint failed" in lowered:
            return "必填字段不能为空"
        return "保存凭据失败，请稍后再试"
