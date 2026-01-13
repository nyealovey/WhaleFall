"""登录 Service.

职责:
- 负责用户名/密码认证（避免路由层直接 query + check_password）
- 负责生成登录响应数据（session + JWT）
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass

from flask_jwt_extended import create_access_token, create_refresh_token
from flask_login import login_user

from app.core.constants.system_constants import ErrorMessages
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.user import User
from app.repositories.users_repository import UsersRepository
from app.schemas.auth import LoginPayload
from app.schemas.validation import validate_or_raise
from app.utils.request_payload import parse_payload


@dataclass(frozen=True, slots=True)
class LoginResult:
    """登录结果(供 API 层封套返回)."""

    access_token: str
    refresh_token: str
    user: dict[str, object]

    def to_payload(self) -> dict[str, object]:
        """转换为可 JSON 序列化的 payload."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "user": self.user,
        }


class LoginService:
    """登录编排服务."""

    def login_from_payload(self, payload: object | None) -> LoginResult:
        """从原始 payload 解析并执行登录."""
        sanitized = parse_payload(payload or {}, preserve_raw_fields=["password"])
        parsed = validate_or_raise(LoginPayload, sanitized)
        return self.login(username=parsed.username, password=parsed.password)

    @staticmethod
    def authenticate(*, username: str, password: str) -> User | None:
        """认证用户名与密码.

        Args:
            username: 用户名.
            password: 明文密码.

        Returns:
            User | None: 认证成功返回 User,否则返回 None.

        """
        user = UsersRepository().get_by_username(username)
        if user and user.check_password(password):
            return user
        return None

    @staticmethod
    def build_login_result(user: User) -> LoginResult:
        """生成登录结果(写 session + 生成 JWT).

        Args:
            user: 已认证的用户对象.

        Returns:
            LoginResult: 登录结果.

        Raises:
            AuthorizationError: 当用户被禁用.

        """
        if not user.is_active:
            raise AuthorizationError(
                message=ErrorMessages.ACCOUNT_DISABLED,
                message_key="ACCOUNT_DISABLED",
            )

        login_user(user, remember=True)
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        return LoginResult(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
            },
        )

    def login(self, *, username: str, password: str) -> LoginResult:
        """登录入口: 认证并构造登录结果.

        Args:
            username: 用户名.
            password: 明文密码.

        Returns:
            LoginResult: 登录结果.

        Raises:
            AuthenticationError: 当用户名或密码错误.
            AuthorizationError: 当用户被禁用.

        """
        user = self.authenticate(username=username, password=password)
        if not user:
            raise AuthenticationError(
                message=ErrorMessages.INVALID_CREDENTIALS,
                message_key="INVALID_CREDENTIALS",
            )
        return self.build_login_result(user)
