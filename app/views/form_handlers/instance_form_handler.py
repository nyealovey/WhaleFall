"""实例表单处理器(View layer)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.core.constants import DatabaseType
from app.core.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.services.common.filter_options_service import FilterOptionsService
from app.services.credentials.credential_options_service import CredentialOptionsService
from app.services.instances.instance_detail_read_service import InstanceDetailReadService
from app.services.instances.instance_write_service import InstanceWriteService
from app.utils.database_type_utils import get_database_type_display_name

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.models.tag import Tag


class InstanceFormHandler:
    """实例表单处理器.

    约束:
    - 不直接访问数据库
    - load/upsert/options 均通过 Service 完成
    """

    def __init__(
        self,
        *,
        detail_service: InstanceDetailReadService | None = None,
        write_service: InstanceWriteService | None = None,
        credential_options_service: CredentialOptionsService | None = None,
        filter_options_service: FilterOptionsService | None = None,
    ) -> None:
        """初始化表单处理器."""
        self._detail_service = detail_service or InstanceDetailReadService()
        self._write_service = write_service or InstanceWriteService()
        self._credential_options_service = credential_options_service or CredentialOptionsService()
        self._filter_options_service = filter_options_service or FilterOptionsService()

    def load(self, resource_id: ResourceIdentifier) -> Instance | None:
        """加载实例资源."""
        if not isinstance(resource_id, int):
            return None
        return self._detail_service.get_instance_by_id(resource_id)

    def upsert(self, payload: ResourcePayload, resource: Instance | None = None) -> Instance:
        """创建或更新实例."""
        if resource is None:
            return self._write_service.create(payload)
        return self._write_service.update(resource.id, payload)

    def build_context(self, *, resource: Instance | None) -> ResourceContext:
        """构造表单渲染上下文."""
        credential_options = self._credential_options_service.list_active_credential_options()
        database_type_options = [
            {"value": db_type, "label": get_database_type_display_name(db_type)} for db_type in DatabaseType.RELATIONAL
        ]
        tag_options = self._filter_options_service.list_active_tag_options()

        selected_tags = list(cast("list[Tag]", resource.tags)) if resource else []
        selected_tag_names = [tag.name for tag in selected_tags]
        return {
            "credential_options": credential_options,
            "database_type_options": database_type_options,
            "tag_options": tag_options,
            "selected_tag_names": selected_tag_names,
        }
