"""用户表单处理器(View layer)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.constants import UserRole
from app.services.users.user_detail_read_service import UserDetailReadService
from app.services.users.user_write_service import UserWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload

if TYPE_CHECKING:
    from app.models.user import User


class UserFormHandler:
    """用户表单处理器.

    约束:
    - 不直接访问数据库
    - load/upsert 均通过 Service 完成
    """

    def __init__(
        self,
        *,
        detail_service: UserDetailReadService | None = None,
        write_service: UserWriteService | None = None,
    ) -> None:
        self._detail_service = detail_service or UserDetailReadService()
        self._write_service = write_service or UserWriteService()

    def load(self, resource_id: ResourceIdentifier) -> "User | None":
        """加载用户资源."""
        if not isinstance(resource_id, int):
            return None
        return self._detail_service.get_user_by_id(resource_id)

    def upsert(self, payload: ResourcePayload, resource: "User | None" = None) -> "User":
        """创建或更新用户."""
        if resource is None:
            return self._write_service.create(payload)
        return self._write_service.update(resource.id, payload)

    def build_context(self, *, resource: "User | None") -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        return {
            "role_options": [
                {"value": UserRole.ADMIN, "label": "管理员"},
                {"value": UserRole.USER, "label": "普通用户"},
            ],
        }

