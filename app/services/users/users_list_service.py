"""用户列表 Service.

职责:
- 组织 repository 调用并将 ORM 对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.users_repository import UsersRepository
from app.types.listing import PaginatedResult
from app.types.users import UserListFilters, UserListItem


class UsersListService:
    """用户列表业务编排服务."""

    def __init__(self, repository: UsersRepository | None = None) -> None:
        """初始化服务并注入用户仓库."""
        self._repository = repository or UsersRepository()

    def list_users(self, filters: UserListFilters) -> PaginatedResult[UserListItem]:
        """分页列出用户列表."""
        page_result = self._repository.list_users(filters)

        items: list[UserListItem] = []
        for user in page_result.items:
            created_at = user.created_at.strftime("%Y-%m-%d") if user.created_at else None
            items.append(
                UserListItem(
                    id=user.id,
                    username=user.username,
                    role=user.role,
                    created_at=created_at,
                    created_at_display=created_at,
                    last_login=user.last_login.isoformat() if user.last_login else None,
                    is_active=bool(user.is_active),
                ),
            )

        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )
