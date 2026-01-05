"""实例表单处理器."""

from __future__ import annotations

from typing import cast

from app.constants import DatabaseType
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.tag import Tag
from app.services.instances.instance_write_service import InstanceWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload


class InstanceFormHandler:
    """实例表单处理器."""

    def __init__(self, service: InstanceWriteService | None = None) -> None:
        """初始化表单处理器并注入写服务."""
        self._service = service or InstanceWriteService()

    def load(self, resource_id: ResourceIdentifier) -> Instance | None:
        """加载实例资源."""
        if not isinstance(resource_id, int):
            return None
        return cast("Instance | None", Instance.query.get(resource_id))

    def upsert(self, payload: ResourcePayload, resource: Instance | None = None) -> Instance:
        """创建或更新实例."""
        if resource is None:
            return self._service.create(payload)
        return self._service.update(resource.id, payload)

    def build_context(self, *, resource: Instance | None) -> ResourceContext:
        """构造表单渲染上下文."""
        credentials = Credential.query.filter_by(is_active=True).all()
        credential_options = [
            {
                "value": cred.id,
                "label": f"#{cred.id} - {cred.name} ({cred.credential_type})",
            }
            for cred in credentials
        ]

        database_type_options = [
            {"value": db_type, "label": DatabaseType.get_display_name(db_type)} for db_type in DatabaseType.RELATIONAL
        ]

        tags = Tag.get_active_tags()
        tag_options = [{"value": tag.name, "label": tag.display_name, "color": tag.color} for tag in tags]

        selected_tags = list(cast("list[Tag]", resource.tags)) if resource else []
        selected_tag_names = [tag.name for tag in selected_tags]

        return {
            "credential_options": credential_options,
            "database_type_options": database_type_options,
            "tag_options": tag_options,
            "selected_tag_names": selected_tag_names,
        }
