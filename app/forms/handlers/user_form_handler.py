"""用户表单处理器."""

from __future__ import annotations

from typing import cast

from app.constants import UserRole
from app.models.user import User
from app.services.users.user_write_service import UserWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.utils.data_validator import DataValidator


class UserFormHandler:
    """用户表单处理器."""

    def __init__(self, service: UserWriteService | None = None) -> None:
        self._service = service or UserWriteService()

    def load(self, resource_id: ResourceIdentifier) -> User | None:
        if not isinstance(resource_id, int):
            return None
        return cast("User | None", User.query.get(resource_id))

    def upsert(self, payload: ResourcePayload, resource: User | None = None) -> User:
        sanitized = cast("dict[str, object]", DataValidator.sanitize_form_data(payload or {}))
        if resource is None:
            return self._service.create(sanitized)
        return self._service.update(resource.id, sanitized)

    def build_context(self, *, resource: User | None) -> ResourceContext:
        del resource
        return {
            "role_options": [
                {"value": UserRole.ADMIN, "label": "管理员"},
                {"value": UserRole.USER, "label": "普通用户"},
            ],
        }
