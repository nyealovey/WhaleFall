"""
用户表单服务
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from flask_login import current_user

from app.constants import UserRole
from app.models.user import User
from app.services.form_service.resource_form_service import BaseResourceService, ServiceResult
from app.utils.data_validator import sanitize_form_data
from app.utils.structlog_config import log_info


class UserFormService(BaseResourceService[User]):
    """负责用户创建与编辑的服务。

    提供用户的表单校验、密码强度验证和数据保存功能。

    Attributes:
        model: 关联的 User 模型类。
        USERNAME_PATTERN: 用户名的正则表达式模式。
        ALLOWED_ROLES: 允许的角色集合。
        MESSAGE_USERNAME_EXISTS: 用户名已存在的消息键。
    """

    model = User
    USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
    ALLOWED_ROLES = {UserRole.ADMIN, UserRole.USER}
    MESSAGE_USERNAME_EXISTS = "USERNAME_EXISTS"

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """清理表单数据。

        Args:
            payload: 原始表单数据。

        Returns:
            清理后的数据字典。
        """
        return sanitize_form_data(payload or {})

    def validate(self, data: dict[str, Any], *, resource: User | None) -> ServiceResult[dict[str, Any]]:
        """校验用户数据。

        校验用户名格式、角色有效性、密码强度和唯一性。

        Args:
            data: 清理后的数据。
            resource: 已存在的用户实例（编辑场景），创建时为 None。

        Returns:
            校验结果，成功时返回规范化的数据，失败时返回错误信息。
        """
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
        """将数据赋值给用户实例。

        Args:
            instance: 用户实例。
            data: 已校验的数据。
        """
        instance.username = data["username"]
        instance.role = data["role"]
        instance.is_active = data["is_active"]

        password = data.get("password")
        if password:
            instance.set_password(password)

    def after_save(self, instance: User, data: dict[str, Any]) -> None:
        """保存后记录日志。

        Args:
            instance: 已保存的用户实例。
            data: 已校验的数据。
        """
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
        """构建模板渲染上下文。

        Args:
            resource: 用户实例，创建时为 None。

        Returns:
            包含角色选项的上下文字典。
        """
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
        """规范化表单数据。

        Args:
            data: 原始数据。
            resource: 已存在的用户实例，创建时为 None。

        Returns:
            规范化后的数据字典。
        """
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

    def _validate_password_strength(self, password: str) -> str | None:
        """验证密码强度。

        密码必须满足：至少8位、包含大写字母、小写字母和数字。

        Args:
            password: 待验证的密码。

        Returns:
            验证失败时返回错误信息，成功时返回 None。
        """
        if len(password) < 8:
            return "密码长度至少8位"
        if not any(char.isupper() for char in password):
            return "密码必须包含大写字母"
        if not any(char.islower() for char in password):
            return "密码必须包含小写字母"
        if not any(char.isdigit() for char in password):
            return "密码必须包含数字"
        return None
