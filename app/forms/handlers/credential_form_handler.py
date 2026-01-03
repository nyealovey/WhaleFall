"""凭据表单处理器."""

from __future__ import annotations

from typing import cast

from app.constants import CREDENTIAL_TYPES, DATABASE_TYPES
from app.models.credential import Credential
from app.services.credentials.credential_write_service import CredentialWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.utils.data_validator import DataValidator


class CredentialFormHandler:
    """凭据表单处理器."""

    def __init__(self, service: CredentialWriteService | None = None) -> None:
        """初始化表单处理器并注入写服务."""
        self._service = service or CredentialWriteService()

    def load(self, resource_id: ResourceIdentifier) -> Credential | None:
        """加载凭据资源."""
        if not isinstance(resource_id, int):
            return None
        return cast("Credential | None", Credential.query.get(resource_id))

    def upsert(self, payload: ResourcePayload, resource: Credential | None = None) -> Credential:
        """创建或更新凭据."""
        sanitized = cast(ResourcePayload, DataValidator.sanitize_form_data(payload or {}))
        if resource is None:
            return self._service.create(sanitized)
        return self._service.update(resource.id, sanitized)

    def build_context(self, *, resource: Credential | None) -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        return {
            "credential_type_options": CREDENTIAL_TYPES,
            "db_type_options": DATABASE_TYPES,
        }
