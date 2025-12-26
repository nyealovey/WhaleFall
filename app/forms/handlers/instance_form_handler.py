"""实例表单处理器."""

from __future__ import annotations

from typing import cast

from app.models.credential import Credential
from app.models.instance import Instance
from app.models.tag import Tag
from app.services.database_type_service import DatabaseTypeService
from app.services.instances.instance_write_service import InstanceWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.utils.data_validator import DataValidator


class InstanceFormHandler:
    """实例表单处理器."""

    def __init__(self, service: InstanceWriteService | None = None) -> None:
        self._service = service or InstanceWriteService()

    def load(self, resource_id: ResourceIdentifier) -> Instance | None:
        if not isinstance(resource_id, int):
            return None
        return cast("Instance | None", Instance.query.get(resource_id))

    def upsert(self, payload: ResourcePayload, resource: Instance | None = None) -> Instance:
        sanitized = cast("dict[str, object]", DataValidator.sanitize_form_data(payload or {}))
        if resource is None:
            return self._service.create(sanitized)
        return self._service.update(resource.id, sanitized)

    def build_context(self, *, resource: Instance | None) -> ResourceContext:
        credentials = Credential.query.filter_by(is_active=True).all()
        credential_options = [
            {
                "value": cred.id,
                "label": f"#{cred.id} - {cred.name} ({cred.credential_type})",
            }
            for cred in credentials
        ]

        database_type_configs = DatabaseTypeService.get_active_types()
        database_type_options = [
            {
                "value": config.name,
                "label": config.display_name or config.name,
            }
            for config in database_type_configs
        ]

        tags = Tag.get_active_tags()
        tag_options = [
            {"value": tag.name, "label": tag.display_name, "color": tag.color}
            for tag in tags
        ]

        selected_tags = list(cast("list[Tag]", resource.tags)) if resource else []
        selected_tag_names = [tag.name for tag in selected_tags]

        return {
            "credential_options": credential_options,
            "database_type_options": database_type_options,
            "tag_options": tag_options,
            "selected_tag_names": selected_tag_names,
        }
