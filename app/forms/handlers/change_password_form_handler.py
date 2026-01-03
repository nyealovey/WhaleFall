"""修改密码表单处理器."""

from __future__ import annotations

from typing import cast

from app.models.user import User
from app.services.auth.change_password_service import ChangePasswordService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload


class ChangePasswordFormHandler:
    """修改密码表单处理器."""

    def __init__(self, service: ChangePasswordService | None = None) -> None:
        """初始化表单处理器并注入服务."""
        self._service = service or ChangePasswordService()

    def load(self, resource_id: ResourceIdentifier) -> User | None:
        """加载用户资源."""
        if not isinstance(resource_id, int):
            return None
        return cast("User | None", User.query.get(resource_id))

    def upsert(self, payload: ResourcePayload, resource: User | None = None) -> User:
        """修改用户密码."""
        return self._service.change_password(payload, user=resource)

    def build_context(self, *, resource: User | None) -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        return {}
