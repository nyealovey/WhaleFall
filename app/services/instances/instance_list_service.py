"""实例列表 Service.

职责:
- 组织 repository 调用并将领域对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import Any

from app.core.types.instances import InstanceListFilters, InstanceListItem
from app.core.types.listing import PaginatedResult
from app.repositories.instances_repository import InstancesRepository
from app.services.veeam.instance_backup_read_service import resolve_backup_status


def _resolve_audit_status(audit_facts: dict[str, object] | None) -> str:
    """根据审计快照 facts 推导列表页展示状态."""
    if not isinstance(audit_facts, dict):
        return "not_configured"

    has_audit = bool(audit_facts.get("has_audit"))
    enabled_count_raw = audit_facts.get("enabled_audit_count")
    if isinstance(enabled_count_raw, (int, float, str)):
        try:
            enabled_count = int(enabled_count_raw or 0)
        except ValueError:
            enabled_count = 0
    else:
        enabled_count = 0

    if has_audit and enabled_count > 0:
        return "enabled"
    if has_audit:
        return "configured_disabled"
    return "not_configured"


class InstanceListService:
    """实例列表业务编排服务."""

    def __init__(self, repository: InstancesRepository | Any | None = None) -> None:
        """初始化服务并注入实例仓库."""
        self._repository = repository or InstancesRepository()

    def list_instances(self, filters: InstanceListFilters) -> PaginatedResult[InstanceListItem]:
        """分页列出实例列表."""
        page_result, metrics = self._repository.list_instances(filters)
        items: list[InstanceListItem] = []
        for instance in page_result.items:
            last_sync = metrics.last_sync_times.get(instance.id)
            status_value = "deleted" if instance.deleted_at else ("active" if instance.is_active else "inactive")
            audit_status = _resolve_audit_status(metrics.audit_facts_map.get(instance.id))
            backup_summary = metrics.backup_summary_map.get(instance.id, {})
            backup_last_time = backup_summary.get("latest_backup_at") if isinstance(backup_summary, dict) else None
            items.append(
                InstanceListItem(
                    id=instance.id,
                    name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                    port=instance.port,
                    description="" if instance.description is None else instance.description,
                    is_active=instance.is_active,
                    deleted_at=instance.deleted_at.isoformat() if instance.deleted_at else None,
                    status=status_value,
                    audit_status=audit_status,
                    main_version=instance.main_version,
                    active_db_count=metrics.database_counts.get(instance.id, 0),
                    active_account_count=metrics.account_counts.get(instance.id, 0),
                    last_sync_time=last_sync.isoformat() if last_sync else None,
                    tags=metrics.tags_map.get(instance.id, []),
                    is_jumpserver_managed=instance.id in metrics.jumpserver_managed_ids,
                    backup_status=resolve_backup_status(
                        latest_backup_at=backup_last_time if isinstance(backup_last_time, str) else None
                    ),
                    backup_last_time=backup_last_time if isinstance(backup_last_time, str) else None,
                ),
            )

        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )
