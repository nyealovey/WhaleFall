"""
用户表单服务
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from flask_login import current_user

from app.constants import UserRole
from app.models.user import User
from app.services.resource_form_service import BaseResourceService, ServiceResult
from app.utils.data_validator import sanitize_form_data
from app.utils.structlog_config import log_info


class UserFormService(BaseResourceService[User]):
    """负责用户创建与编辑的服务。"""

    model = User
    USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
    ALLOWED_ROLES = {UserRole.ADMIN, UserRole.USER}
    MESSAGE_USERNAME_EXISTS = "USERNAME_EXISTS"

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return sanitize_form_data(payload or {})

    def validate(self, data: dict[str, Any], *, resource: User | None) -> ServiceResult[dict[str, Any]]:
        normalized = self._normalize_payload(data, resource)

        if not normalized["username"]:
            return ServiceResult.fail("用户名不能为空")

        if not self.USERNAME_PATTERN.match(normalized["username"]):
            return ServiceResult.fail("用户名只能包含字母、数字和下划线，长度为3-20位")

        if normalized["role"] not in self.ALLOWED_ROLES:
            return ServiceResult.fail("角色只能是管理员或普通用户")

        if resource is None and not normalized["password"]:
            return ServiceResult.fail("请设置初始密码")

        if normalized["password"]:
            password_error = self._validate_password_strength(normalized["password"])
            if password_error:
                return ServiceResult.fail(password_error, message_key="PASSWORD_INVALID")

        # 唯一性校验
        query = User.query.filter(User.username == normalized["username"])
        if resource:
            query = query.filter(User.id != resource.id)
        if query.first():
            return ServiceResult.fail("用户名已存在", message_key=self.MESSAGE_USERNAME_EXISTS)

        return ServiceResult.ok(normalized)

    def assign(self, instance: User, data: dict[str, Any]) -> None:
        instance.username = data["username"]
        instance.role = data["role"]
        instance.is_active = data["is_active"]

        password = data.get("password")
        if password:
            instance.set_password(password)

    def after_save(self, instance: User, data: dict[str, Any]) -> None:
        action = "创建用户成功" if data.get("_is_create") else "更新用户成功"
        log_info(
            action,
            module="users",
            user_id=getattr(current_user, "id", None),
            target_user_id=instance.id,
            username=instance.username,
            role=instance.role,
            is_active=instance.is_active,
        )

    def build_context(self, *, resource: User | None) -> dict[str, Any]:
        return {
            "role_options": [
                {"value": UserRole.ADMIN, "label": "管理员"},
                {"value": UserRole.USER, "label": "普通用户"},
            ],
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _normalize_payload(self, data: Mapping[str, Any], resource: User | None) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        username_value = data.get("username")
        if username_value is None and resource is not None:
            username_value = resource.username
        normalized["username"] = (username_value or "").strip()

        role_value = data.get("role")
        role_source = role_value if role_value is not None else (resource.role if resource else "")
        normalized["role"] = (role_source or "").strip()

        raw_password = data.get("password")
        password_str = (raw_password or "").strip() if raw_password is not None else None
        normalized["password"] = password_str if password_str else None

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

    def _validate_password_strength(self, password: str) -> str | None:
        if len(password) < 8:
            return "密码长度至少8位"
        if not any(char.isupper() for char in password):
            return "密码必须包含大写字母"
        if not any(char.islower() for char in password):
            return "密码必须包含小写字母"
        if not any(char.isdigit() for char in password):
            return "密码必须包含数字"
        return None
