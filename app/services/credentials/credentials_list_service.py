"""凭据列表 Service.

职责:
- 组织 repository 调用并将 ORM 对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.credentials_repository import CredentialsRepository
from app.core.types.credentials import CredentialListFilters, CredentialListItem
from app.core.types.listing import PaginatedResult
from app.utils.time_utils import time_utils


class CredentialsListService:
    """凭据列表业务编排服务."""

    def __init__(self, repository: CredentialsRepository | None = None) -> None:
        """初始化服务并注入凭据仓库."""
        self._repository = repository or CredentialsRepository()

    def list_credentials(self, filters: CredentialListFilters) -> PaginatedResult[CredentialListItem]:
        """分页列出凭据列表."""
        page_result = self._repository.list_credentials(filters)

        items: list[CredentialListItem] = []
        for row in page_result.items:
            credential = row.credential
            items.append(
                CredentialListItem(
                    id=credential.id,
                    name=credential.name,
                    credential_type=credential.credential_type,
                    db_type=credential.db_type,
                    username=credential.username,
                    category_id=credential.category_id,
                    created_at=credential.created_at.isoformat() if credential.created_at else None,
                    updated_at=credential.updated_at.isoformat() if credential.updated_at else None,
                    password=credential.get_password_masked(),
                    description=credential.description,
                    is_active=bool(credential.is_active),
                    instance_count=row.instance_count,
                    created_at_display=(
                        time_utils.format_china_time(credential.created_at, "%Y-%m-%d %H:%M:%S")
                        if credential.created_at
                        else ""
                    ),
                ),
            )

        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )
