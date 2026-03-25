"""Veeam 备份同步定时任务."""

from __future__ import annotations

from app import create_app
from app.services.veeam.source_service import VeeamSourceService
from app.services.veeam.sync_actions_service import VeeamSyncActionsService


def sync_veeam_backups(
    *,
    manual_run: bool = False,
    created_by: int | None = None,
    run_id: str | None = None,
    **_: object,
) -> None:
    """同步 Veeam 备份快照."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        service = VeeamSyncActionsService()
        binding = VeeamSourceService().get_binding_or_error()
        resolved_run_id = run_id
        if not resolved_run_id:
            prepared = service.prepare_background_sync(
                created_by=created_by if manual_run else None,
                trigger_source="manual" if manual_run else "scheduled",
            )
            resolved_run_id = prepared.run_id
        service._sync_once(
            created_by=created_by if manual_run else None,
            run_id=resolved_run_id,
            credential_id=int(binding.credential_id),
        )
