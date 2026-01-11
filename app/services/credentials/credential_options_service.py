"""凭据下拉选项 Service.

职责:
- 组织 repository 调用并输出通用 options 结构
- 不做 Response、不 commit
"""

from __future__ import annotations

from app.repositories.credentials_repository import CredentialsRepository


class CredentialOptionsService:
    """凭据下拉选项读取服务."""

    def __init__(self, repository: CredentialsRepository | None = None) -> None:
        self._repository = repository or CredentialsRepository()

    def list_active_credential_options(self) -> list[dict[str, object]]:
        """获取启用的凭据 options."""
        credentials = self._repository.list_active_credentials()
        return [
            {
                "value": cred.id,
                "label": f"#{cred.id} - {cred.name} ({cred.credential_type})",
            }
            for cred in credentials
        ]

