"""凭据详情页面 Service.

职责:
- 聚合凭据详情页渲染所需的只读数据
- 组织 repositories，不在 routes 中直接拼 Query
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import NotFoundError
from app.models.credential import Credential
from app.repositories.credentials_repository import CredentialsRepository


@dataclass(slots=True)
class CredentialDetailPageContext:
    """凭据详情页面上下文."""

    credential: Credential


class CredentialDetailPageService:
    """凭据详情页面读取服务."""

    def __init__(self, *, credentials_repository: CredentialsRepository | None = None) -> None:
        """初始化服务并注入依赖."""
        self._credentials_repository = credentials_repository or CredentialsRepository()

    def build_context(self, credential_id: int) -> CredentialDetailPageContext:
        """构造凭据详情页渲染上下文."""
        credential = self._credentials_repository.get_by_id(credential_id)
        if credential is None:
            raise NotFoundError("凭据不存在", extra={"credential_id": credential_id})
        return CredentialDetailPageContext(credential=credential)
