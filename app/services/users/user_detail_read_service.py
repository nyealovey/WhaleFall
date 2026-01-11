"""用户详情 Service.

职责:
- 组织 repository 调用
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.errors import NotFoundError
from app.models.user import User
from app.repositories.users_repository import UsersRepository


class UserDetailReadService:
    """用户详情读取服务."""

    def __init__(self, repository: UsersRepository | None = None) -> None:
        """初始化服务并注入用户仓库."""
        self._repository = repository or UsersRepository()

    def get_user_by_id(self, user_id: int) -> User | None:
        """按 ID 获取用户(可为空)."""
        return self._repository.get_by_id(user_id)

    def get_user_or_error(self, user_id: int) -> User:
        """按 ID 获取用户(不存在则抛错)."""
        user = self.get_user_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在", extra={"user_id": user_id})
        return user

