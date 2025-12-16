"""用户表单服务."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar, cast

from sqlalchemy.sql.elements import ColumnElement

from flask_login import current_user

from app.constants import UserRole
from app.models.user import MIN_USER_PASSWORD_LENGTH, User
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.types.converters import as_bool, as_optional_str, as_str
from app.utils.data_validator import sanitize_form_data
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from sqlalchemy.orm import Query

    from app.types import ContextDict, MutablePayloadDict, PayloadMapping


class UserFormService(BaseResourceService[User]):
    """负责用户创建与编辑的服务.

    提供用户的表单校验、密码强度验证和数据保存功能.

    Attributes:
        model: 关联的 User 模型类.
        USERNAME_PATTERN: 用户名的正则表达式模式.
        ALLOWED_ROLES: 允许的角色集合.
        MESSAGE_USERNAME_EXISTS: 用户名已存在的消息键.

    """

    model = User
    USERNAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_]{3,20}$")
    ALLOWED_ROLES: ClassVar[set[str]] = {UserRole.ADMIN, UserRole.USER}
    MESSAGE_USERNAME_EXISTS: ClassVar[str] = "USERNAME_EXISTS"
    MESSAGE_LAST_ADMIN_REQUIRED: ClassVar[str] = "LAST_ADMIN_REQUIRED"

    def sanitize(self, payload: PayloadMapping) -> MutablePayloadDict:
        """清理表单数据.

        Args:
            payload: 原始表单数据.

        Returns:
            清理后的数据字典.

        """
        return cast("MutablePayloadDict", sanitize_form_data(payload or {}))

    def validate(self, data: MutablePayloadDict, *, resource: User | None) -> ServiceResult[MutablePayloadDict]:
        """校验用户数据.

        校验用户名格式、角色有效性、密码强度和唯一性.

        Args:
            data: 清理后的数据.
            resource: 已存在的用户实例(编辑场景),创建时为 None.

        Returns:
            校验结果,成功时返回规范化的数据,失败时返回错误信息.

        """
        normalized = self._normalize_payload(data, resource)

        username = cast(str, normalized["username"])
        role = cast(str, normalized["role"])
        password = cast(str | None, normalized["password"])

        validators: list[tuple[str | None, str | None]] = [
            (self._validate_username(username), None),
            (self._validate_role(role), None),
            (self._validate_password_requirement(resource, password), "PASSWORD_INVALID"),
        ]

        for message, message_key in validators:
            if message:
                return ServiceResult.fail(message, message_key=message_key)

        unique_error = self._validate_unique_username(resource, username)
        if unique_error:
            return ServiceResult.fail(unique_error, message_key=self.MESSAGE_USERNAME_EXISTS)

        admin_error = self._ensure_last_admin(resource, normalized)
        if admin_error:
            return ServiceResult.fail(admin_error, message_key=self.MESSAGE_LAST_ADMIN_REQUIRED)

        return ServiceResult.ok(normalized)

    def assign(self, instance: User, data: MutablePayloadDict) -> None:
        """将数据赋值给用户实例.

        Args:
            instance: 用户实例.
            data: 已校验的数据.

        Returns:
            None: 属性赋值完成后返回.

        """
        instance.username = as_str(data.get("username"))
        instance.role = as_str(data.get("role"))
        instance.is_active = as_bool(data.get("is_active"), default=True)

        password = as_optional_str(data.get("password"))
        if password:
            instance.set_password(password)

    def after_save(self, instance: User, data: MutablePayloadDict) -> None:
        """保存后记录日志.

        Args:
            instance: 已保存的用户实例.
            data: 已校验的数据.

        Returns:
            None: 日志记录完成后返回.

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

    def build_context(self, *, resource: User | None) -> ContextDict:
        """构建模板渲染上下文.

        Args:
            resource: 用户实例,创建时为 None.

        Returns:
            包含角色选项的上下文字典.

        """
        del resource
        return {
            "role_options": [
                {"value": UserRole.ADMIN, "label": "管理员"},
                {"value": UserRole.USER, "label": "普通用户"},
            ],
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _normalize_payload(self, data: PayloadMapping, resource: User | None) -> MutablePayloadDict:
        """规范化表单数据.

        Args:
            data: 原始数据.
            resource: 已存在的用户实例,创建时为 None.

        Returns:
            规范化后的数据字典.

        """
        normalized: MutablePayloadDict = {}

        normalized["username"] = as_str(
            data.get("username"),
            default=resource.username if resource else "",
        ).strip()

        normalized["role"] = as_str(
            data.get("role"),
            default=resource.role if resource else "",
        ).strip()

        normalized["password"] = as_optional_str(data.get("password"))

        normalized["is_active"] = as_bool(
            data.get("is_active"),
            default=resource.is_active if resource else True,
        )
        normalized["_is_create"] = resource is None
        return normalized

    @staticmethod
    def _is_target_state_admin(data: PayloadMapping) -> bool:
        """判断提交后的用户是否仍为活跃管理员."""
        return data.get("role") == UserRole.ADMIN and as_bool(data.get("is_active"), default=True)

    def _user_query(self) -> Query:
        """暴露 user query,便于单测注入."""
        return User.query

    def _validate_password_strength(self, password: str) -> str | None:
        """验证密码强度.

        密码必须满足:至少8位、包含大写字母、小写字母和数字.

        Args:
            password: 待验证的密码.

        Returns:
            验证失败时返回错误信息,成功时返回 None.

        """
        if len(password) < MIN_USER_PASSWORD_LENGTH:
            return f"密码长度至少{MIN_USER_PASSWORD_LENGTH}位"
        if not any(char.isupper() for char in password):
            return "密码必须包含大写字母"
        if not any(char.islower() for char in password):
            return "密码必须包含小写字母"
        if not any(char.isdigit() for char in password):
            return "密码必须包含数字"
        return None

    def _validate_username(self, username: str) -> str | None:
        """校验用户名格式."""
        if not username:
            return "用户名不能为空"
        if not self.USERNAME_PATTERN.match(username):
            return "用户名只能包含字母、数字和下划线,长度为3-20位"
        return None

    def _validate_role(self, role: str) -> str | None:
        """校验角色合法性."""
        if role not in self.ALLOWED_ROLES:
            return "角色只能是管理员或普通用户"
        return None

    def _validate_password_requirement(self, resource: User | None, password: str | None) -> str | None:
        """校验密码是否满足必填与强度要求."""
        if resource is None and not password:
            return "请设置初始密码"
        if password:
            return self._validate_password_strength(password)
        return None

    def _validate_unique_username(self, resource: User | None, username: str) -> str | None:
        """检查用户名唯一性."""
        username_filter = cast("ColumnElement[bool]", User.username == username)
        query = self._user_query().filter(username_filter)
        if resource:
            exclude_self = cast("ColumnElement[bool]", User.id != resource.id)
            query = query.filter(exclude_self)
        if query.first():
            return "用户名已存在"
        return None

    def _ensure_last_admin(self, resource: User | None, normalized: PayloadMapping) -> str | None:
        """确保至少保留一名活跃管理员."""
        if resource and resource.is_admin() and not self._is_target_state_admin(normalized):
            has_backup_admin = User.active_admin_count(exclude_user_id=resource.id)
            if has_backup_admin <= 0:
                return "系统至少需要一位活跃管理员"
        return None
