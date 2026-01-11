"""凭据表单处理器(View layer)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants import CREDENTIAL_TYPES, DATABASE_TYPES
from app.services.credentials.credential_detail_read_service import CredentialDetailReadService
from app.services.credentials.credential_write_service import CredentialWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload

if TYPE_CHECKING:
    from app.models.credential import Credential


class CredentialFormHandler:
    """凭据表单处理器.

    约束:
    - 不直接访问数据库
    - load/upsert 均通过 Service 完成
    """

    def __init__(
        self,
        *,
        detail_service: CredentialDetailReadService | None = None,
        write_service: CredentialWriteService | None = None,
    ) -> None:
        self._detail_service = detail_service or CredentialDetailReadService()
        self._write_service = write_service or CredentialWriteService()

    def load(self, resource_id: ResourceIdentifier) -> "Credential | None":
        """加载凭据资源."""
        if not isinstance(resource_id, int):
            return None
        return self._detail_service.get_credential_by_id(resource_id)

    def upsert(self, payload: ResourcePayload, resource: "Credential | None" = None) -> "Credential":
        """创建或更新凭据."""
        if resource is None:
            return self._write_service.create(payload)
        return self._write_service.update(resource.id, payload)

    def build_context(self, *, resource: "Credential | None") -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        return {
            "credential_type_options": CREDENTIAL_TYPES,
            "db_type_options": DATABASE_TYPES,
        }

