"""修改密码表单处理器(View layer)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.services.auth.change_password_service import ChangePasswordService

if TYPE_CHECKING:
    from app.models.user import User


class ChangePasswordFormHandler:
    """修改密码表单处理器.

    说明:
    - 该表单资源(load) 由 `ChangePasswordFormView` 从 session/current_user 解析, handler 不做 DB 访问.
    """

    def __init__(self, service: ChangePasswordService | None = None) -> None:
        """初始化表单处理器."""
        self._service = service or ChangePasswordService()

    def load(self, resource_id: ResourceIdentifier) -> User | None:
        """加载用户资源(当前实现不从 DB 读取)."""
        del resource_id
        return None

    def upsert(self, payload: ResourcePayload, resource: User | None = None) -> User:
        """修改用户密码."""
        return self._service.change_password(payload, user=resource)

    def build_context(self, *, resource: User | None) -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        return {}
