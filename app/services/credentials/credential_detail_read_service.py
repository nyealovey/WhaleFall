"""凭据详情 Service.

职责:
- 组织 repository 调用
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.models.credential import Credential
from app.repositories.credentials_repository import CredentialsRepository


class CredentialDetailReadService:
    """凭据详情读取服务."""

    def __init__(self, repository: CredentialsRepository | None = None) -> None:
        """初始化服务并注入凭据仓库."""
        self._repository = repository or CredentialsRepository()

    def get_credential_by_id(self, credential_id: int) -> Credential | None:
        """按 ID 获取凭据(可为空)."""
        return self._repository.get_by_id(credential_id)

    def get_credential_or_error(self, credential_id: int) -> Credential:
        """按 ID 获取凭据(不存在则抛错)."""
        credential = self.get_credential_by_id(credential_id)
        if credential is None:
            raise NotFoundError("凭据不存在", extra={"credential_id": credential_id})
        return credential
