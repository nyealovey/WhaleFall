"""用户写操作 Service.

职责:
- 处理用户的创建/更新/删除编排
- 负责校验与数据规范化
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, cast

from sqlalchemy.exc import SQLAlchemyError

from app.core.constants import UserRole
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.user import User
from app.repositories.users_repository import UsersRepository
from app.schemas.users import UserCreatePayload, UserUpdatePayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from app.core.types import PayloadMapping, ResourcePayload


@dataclass(slots=True)
class UserDeleteOutcome:
    """用户删除结果."""

    user_id: int
    username: str
    role: str


class UserWriteService:
    """用户写操作服务."""

    MESSAGE_USERNAME_EXISTS: ClassVar[str] = "USERNAME_EXISTS"

    def __init__(self, repository: UsersRepository | None = None) -> None:
        """初始化服务并注入用户仓库."""
        self._repository = repository or UsersRepository()

    def create(self, payload: ResourcePayload, *, operator_id: int | None = None) -> User:
        """创建用户."""
        sanitized = parse_payload(
            payload,
            preserve_raw_fields=["password"],
            boolean_fields_default_false=["is_active"],
        )
        parsed = validate_or_raise(UserCreatePayload, sanitized)
        self._ensure_username_unique(parsed.username, resource=None)

        username = parsed.username
        role = parsed.role
        password = parsed.password

        user = User(username=username, role=role)
        cast(Any, user).is_active = parsed.is_active
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
        sanitized = parse_payload(
            payload,
            preserve_raw_fields=["password"],
            boolean_fields_default_false=["is_active"],
        )
        parsed = validate_or_raise(UserUpdatePayload, sanitized)

        self._ensure_username_unique(parsed.username, resource=user)
        self._ensure_last_admin(user, {"role": parsed.role, "is_active": parsed.is_active})

        user.username = parsed.username
        user.role = parsed.role
        cast(Any, user).is_active = parsed.is_active
        if parsed.password is not None:
            user.set_password(parsed.password)
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
            admin_count = self._repository.count_by_role(UserRole.ADMIN)
            if admin_count <= 1:
                raise ValidationError("不能删除最后一个管理员账户")

        outcome = UserDeleteOutcome(user_id=user.id, username=user.username, role=user.role)
        self._repository.delete(user)
        self._log_delete(outcome, operator_id=operator_id)
        return outcome

    def _ensure_username_unique(self, username: str, *, resource: User | None) -> None:
        existing = self._repository.get_by_username(username)
        if existing and (resource is None or existing.id != resource.id):
            raise ConflictError("用户名已存在", message_key=self.MESSAGE_USERNAME_EXISTS)

    @staticmethod
    def _is_target_state_admin(data: PayloadMapping) -> bool:
        return data.get("role") == UserRole.ADMIN and data.get("is_active") is True

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
