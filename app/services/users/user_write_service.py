"""用户写操作 Service.

职责:
- 处理用户的创建/更新/删除编排
- 负责校验与数据规范化
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, cast

from sqlalchemy.exc import SQLAlchemyError

from app.constants import UserRole
from app.errors import ConflictError, NotFoundError, ValidationError
from app.models.user import MIN_USER_PASSWORD_LENGTH, User
from app.repositories.users_repository import UsersRepository
from app.types.converters import as_bool, as_str
from app.utils.data_validator import DataValidator
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from app.types import MutablePayloadDict, PayloadMapping, ResourcePayload


@dataclass(slots=True)
class UserDeleteOutcome:
    """用户删除结果."""

    user_id: int
    username: str
    role: str


class UserWriteService:
    """用户写操作服务."""

    MESSAGE_USERNAME_EXISTS: ClassVar[str] = "USERNAME_EXISTS"

    USERNAME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_]{3,20}$")
    ALLOWED_ROLES: ClassVar[set[str]] = {UserRole.ADMIN, UserRole.USER}

    def __init__(self, repository: UsersRepository | None = None) -> None:
        """初始化服务并注入用户仓库."""
        self._repository = repository or UsersRepository()

    def create(self, payload: ResourcePayload, *, operator_id: int | None = None) -> User:
        """创建用户."""
        sanitized = self._sanitize(payload)
        normalized = self._normalize_payload(sanitized, resource=None)
        self._validate(normalized, resource=None)

        username = cast(str, normalized["username"])
        role = cast(str, normalized["role"])
        password = cast(str, normalized["password"])

        user = User(username=username, role=role)
        cast(Any, user).is_active = cast(bool, normalized["is_active"])
        user.set_password(password)

        try:
            self._repository.add(user)
        except SQLAlchemyError as exc:
            raise ValidationError("保存失败,请稍后再试", extra={"exception": str(exc)}) from exc

        self._log_create(user, operator_id=operator_id)
        return user

    def update(self, user_id: int, payload: ResourcePayload, *, operator_id: int | None = None) -> User:
        """更新用户."""
        user = self._get_or_error(user_id)
        sanitized = self._sanitize(payload)
        normalized = self._normalize_payload(sanitized, resource=user)
        self._validate(normalized, resource=user)

        self._assign(user, normalized)
        try:
            self._repository.add(user)
        except SQLAlchemyError as exc:
            raise ValidationError("保存失败,请稍后再试", extra={"exception": str(exc)}) from exc

        self._log_update(user, operator_id=operator_id)
        return user

    def delete(self, user_id: int, *, operator_id: int | None = None) -> UserDeleteOutcome:
        """删除用户."""
        user = self._get_or_error(user_id)

        if operator_id is not None and user.id == operator_id:
            raise ValidationError("不能删除自己的账户")

        if user.role == UserRole.ADMIN:
            admin_count = User.query.filter_by(role=UserRole.ADMIN).count()
            if admin_count <= 1:
                raise ValidationError("不能删除最后一个管理员账户")

        outcome = UserDeleteOutcome(user_id=user.id, username=user.username, role=user.role)
        self._repository.delete(user)
        self._log_delete(outcome, operator_id=operator_id)
        return outcome

    @staticmethod
    def _sanitize(payload: PayloadMapping) -> MutablePayloadDict:
        return cast("MutablePayloadDict", DataValidator.sanitize_form_data(payload or {}))

    @classmethod
    def _normalize_payload(cls, data: PayloadMapping, *, resource: User | None) -> MutablePayloadDict:
        normalized: MutablePayloadDict = {}
        normalized["username"] = as_str(
            data.get("username"),
            default=resource.username if resource else "",
        ).strip()
        normalized["role"] = as_str(
            data.get("role"),
            default=resource.role if resource else "",
        ).strip()
        normalized["password"] = as_str(data.get("password"), default="")
        normalized["is_active"] = as_bool(
            data.get("is_active"),
            default=resource.is_active if resource else True,
        )
        return normalized

    def _validate(self, normalized: PayloadMapping, *, resource: User | None) -> None:
        username = cast(str, normalized.get("username") or "")
        role = cast(str, normalized.get("role") or "")
        password = cast("str | None", normalized.get("password"))

        username_error = self._validate_username(username)
        if username_error:
            raise ValidationError(username_error)

        role_error = self._validate_role(role)
        if role_error:
            raise ValidationError(role_error)

        password_error = self._validate_password_requirement(resource, password)
        if password_error:
            raise ValidationError(password_error, message_key="PASSWORD_INVALID")

        self._ensure_username_unique(username, resource=resource)
        self._ensure_last_admin(resource, normalized)

    def _ensure_username_unique(self, username: str, *, resource: User | None) -> None:
        existing = self._repository.get_by_username(username)
        if existing and (resource is None or existing.id != resource.id):
            raise ConflictError("用户名已存在", message_key=self.MESSAGE_USERNAME_EXISTS)

    @staticmethod
    def _is_target_state_admin(data: PayloadMapping) -> bool:
        return data.get("role") == UserRole.ADMIN and as_bool(data.get("is_active"), default=True)

    def _ensure_last_admin(self, resource: User | None, normalized: PayloadMapping) -> None:
        if resource and resource.is_admin() and not self._is_target_state_admin(normalized):
            has_backup_admin = User.active_admin_count(exclude_user_id=resource.id)
            if has_backup_admin <= 0:
                raise ValidationError("系统至少需要一位活跃管理员", message_key="LAST_ADMIN_REQUIRED")

    def _get_or_error(self, user_id: int) -> User:
        user = self._repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在", extra={"user_id": user_id})
        return user

    def _validate_username(self, username: str) -> str | None:
        if not username:
            return "用户名不能为空"
        if not self.USERNAME_PATTERN.match(username):
            return "用户名只能包含字母、数字和下划线,长度为3-20位"
        return None

    def _validate_role(self, role: str) -> str | None:
        if role not in self.ALLOWED_ROLES:
            return "角色只能是管理员或普通用户"
        return None

    @staticmethod
    def _validate_password_strength(password: str) -> str | None:
        if len(password) < MIN_USER_PASSWORD_LENGTH:
            return f"密码长度至少{MIN_USER_PASSWORD_LENGTH}位"
        if not any(char.isupper() for char in password):
            return "密码必须包含大写字母"
        if not any(char.islower() for char in password):
            return "密码必须包含小写字母"
        if not any(char.isdigit() for char in password):
            return "密码必须包含数字"
        return None

    def _validate_password_requirement(self, resource: User | None, password: str | None) -> str | None:
        if resource is None and not password:
            return "请设置初始密码"
        if password:
            return self._validate_password_strength(password)
        return None

    @staticmethod
    def _assign(user: User, normalized: PayloadMapping) -> None:
        user.username = as_str(normalized.get("username"))
        user.role = as_str(normalized.get("role"))
        cast(Any, user).is_active = as_bool(normalized.get("is_active"), default=True)

        password_value = as_str(normalized.get("password"), default="")
        if password_value:
            user.set_password(password_value)

    @staticmethod
    def _log_create(user: User, *, operator_id: int | None) -> None:
        log_info(
            "创建用户成功",
            module="users",
            user_id=operator_id,
            target_user_id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
        )

    @staticmethod
    def _log_update(user: User, *, operator_id: int | None) -> None:
        log_info(
            "更新用户成功",
            module="users",
            user_id=operator_id,
            target_user_id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
        )

    @staticmethod
    def _log_delete(outcome: UserDeleteOutcome, *, operator_id: int | None) -> None:
        log_info(
            "删除用户",
            module="users",
            user_id=operator_id,
            deleted_user_id=outcome.user_id,
            deleted_username=outcome.username,
            deleted_role=outcome.role,
        )
