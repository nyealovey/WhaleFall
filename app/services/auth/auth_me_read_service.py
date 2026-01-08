"""Auth Me Read Service.

职责:
- 读取当前用户信息(供 `/api/v1/auth/me` 使用)
- 不返回 Response、不 commit
"""

from __future__ import annotations

from app.constants.system_constants import ErrorMessages
from app.errors import AuthenticationError, NotFoundError
from app.models.user import User


class AuthMeReadService:
    """读取当前用户信息服务."""

    def get_me(self, *, identity: str | int | None) -> dict[str, object]:
        """获取当前用户信息.

        Args:
            identity: `jwt_identity`,通常为字符串形式的用户 ID.

        Returns:
            dict[str, object]: 可 JSON 序列化的用户信息 payload.

        Raises:
            AuthenticationError: 当 identity 非法或无法解析为用户 ID.
            NotFoundError: 当用户不存在.

        """
        try:
            user_id = int(identity)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise AuthenticationError(
                message=ErrorMessages.INVALID_CREDENTIALS,
                message_key="INVALID_CREDENTIALS",
            ) from exc

        user = User.query.get(user_id)
        if not user:
            raise NotFoundError(message="用户不存在")

        return {
            "id": user.id,
            "username": user.username,
            "email": getattr(user, "email", None),
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

