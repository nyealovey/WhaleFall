"""Veeam 备份同步动作服务."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from flask import current_app, has_app_context

from app import db
from app.core.exceptions import ValidationError
from app.infra.route_safety import log_with_context
from app.models.task_run import TaskRun
from app.repositories.veeam_repository import VeeamRepository
from app.services.task_runs.task_run_summary_builders import build_sync_veeam_backups_summary
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.services.veeam.provider import HttpVeeamProvider, VeeamProvider
from app.services.veeam.source_service import VeeamSourceService
from app.utils.time_utils import time_utils

_SYNC_ITEM_TYPE = "step"
_SYNC_ITEM_KEY = "sync_backups"
_SYNC_ITEM_NAME = "同步 Veeam 备份"


@dataclass(frozen=True, slots=True)
class VeeamSyncPreparedRun:
    """后台同步准备结果."""

    run_id: str
    credential_id: int


@dataclass(frozen=True, slots=True)
class VeeamSyncLaunchResult:
    """后台同步启动结果."""

    run_id: str
    thread_name: str


class VeeamSyncActionsService:
    """Veeam 备份同步动作编排."""

    def __init__(
        self,
        *,
        source_service: VeeamSourceService | None = None,
        veeam_repository: VeeamRepository | None = None,
        provider: VeeamProvider | None = None,
    ) -> None:
        self._source_service = source_service or VeeamSourceService(provider=provider)
        self._veeam_repository = veeam_repository or VeeamRepository()
        self._provider = provider or HttpVeeamProvider()

    def prepare_background_sync(self, *, created_by: int | None) -> VeeamSyncPreparedRun:
        """创建 TaskRun 并校验同步前置条件."""
        if not self._provider.is_configured():
            raise ValidationError("Veeam Provider 尚未接入真实 API")
        binding = self._source_service.get_binding_or_error()
        credential = getattr(binding, "credential", None)
        if credential is None:
            raise ValidationError("Veeam 数据源未绑定有效凭据")

        task_runs_service = TaskRunsWriteService()
        run_id = task_runs_service.start_run(
            task_key="sync_veeam_backups",
            task_name="Veeam 备份同步",
            task_category="other",
            trigger_source="manual",
            created_by=created_by,
            summary_json=None,
            result_url="/admin/system-settings#system-settings-veeam",
        )
        task_runs_service.init_items(
            run_id,
            items=[
                TaskRunItemInit(
                    item_type=_SYNC_ITEM_TYPE,
                    item_key=_SYNC_ITEM_KEY,
                    item_name=_SYNC_ITEM_NAME,
                )
            ],
        )
        return VeeamSyncPreparedRun(run_id=run_id, credential_id=int(binding.credential_id))

    def launch_background_sync(
        self,
        *,
        created_by: int | None,
        prepared: VeeamSyncPreparedRun,
    ) -> VeeamSyncLaunchResult:
        """后台启动同步线程."""
        base_app = current_app._get_current_object() if has_app_context() else None
        db.session.commit()

        def _run_sync(captured_created_by: int | None, captured_run_id: str, credential_id: int) -> None:
            app = base_app
            if app is None:
                return
            with app.app_context():
                try:
                    self._sync_once(
                        created_by=captured_created_by,
                        run_id=captured_run_id,
                        credential_id=credential_id,
                    )
                except Exception:
                    return

        thread = threading.Thread(
            target=_run_sync,
            args=(created_by, prepared.run_id, prepared.credential_id),
            name="sync_veeam_backups_manual",
            daemon=True,
        )
        thread.start()
        return VeeamSyncLaunchResult(run_id=prepared.run_id, thread_name=thread.name)

    def _sync_once(
        self,
        *,
        created_by: int | None,
        run_id: str,
        credential_id: int,
    ) -> None:
        binding = self._source_service.get_binding_or_error()
        credential = getattr(binding, "credential", None)
        if credential is None or int(binding.credential_id) != int(credential_id):
            raise ValidationError("Veeam 数据源凭据已变更，请重新发起同步")

        task_runs_service = TaskRunsWriteService()
        synced_at = time_utils.now()
        try:
            task_runs_service.start_item(run_id, item_type=_SYNC_ITEM_TYPE, item_key=_SYNC_ITEM_KEY)
            result = self._provider.list_machine_backups(
                server_host=str(binding.server_host or ""),
                server_port=int(binding.server_port),
                username=str(credential.username or ""),
                password=str(credential.get_plain_password() or ""),
                api_version=str(binding.api_version or ""),
                verify_ssl=bool(binding.verify_ssl),
            )
            snapshots_written_total = self._veeam_repository.replace_machine_backup_snapshots(
                result.records,
                sync_run_id=run_id,
                synced_at=synced_at,
            )
            binding.last_sync_at = synced_at
            binding.last_sync_status = "completed"
            binding.last_sync_run_id = run_id
            binding.last_error = None
            db.session.add(binding)
            task_runs_service.complete_item(
                run_id,
                item_type=_SYNC_ITEM_TYPE,
                item_key=_SYNC_ITEM_KEY,
                metrics_json={
                    "received_total": result.received_total,
                    "snapshots_written_total": snapshots_written_total,
                    "skipped_invalid": result.skipped_invalid,
                },
                details_json={
                    "received_total": result.received_total,
                    "snapshots_written_total": snapshots_written_total,
                    "skipped_invalid": result.skipped_invalid,
                },
            )
            self._write_run_summary(
                run_id=run_id,
                payload=build_sync_veeam_backups_summary(
                    task_key="sync_veeam_backups",
                    inputs={"credential_id": int(binding.credential_id)},
                    received_total=result.received_total,
                    snapshots_written_total=snapshots_written_total,
                    skipped_invalid=result.skipped_invalid,
                    error_message=None,
                ),
                error_message=None,
            )
            task_runs_service.finalize_run(run_id)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            binding = self._source_service.get_binding_or_error()
            binding.last_sync_at = synced_at
            binding.last_sync_status = "failed"
            binding.last_sync_run_id = run_id
            binding.last_error = str(exc)
            db.session.add(binding)
            task_runs_service.fail_item(
                run_id,
                item_type=_SYNC_ITEM_TYPE,
                item_key=_SYNC_ITEM_KEY,
                error_message=str(exc),
                details_json={"error_message": str(exc)},
            )
            self._write_run_summary(
                run_id=run_id,
                payload=build_sync_veeam_backups_summary(
                    task_key="sync_veeam_backups",
                    inputs={"credential_id": int(binding.credential_id)},
                    received_total=0,
                    snapshots_written_total=0,
                    skipped_invalid=0,
                    error_message=str(exc),
                ),
                error_message=str(exc),
            )
            task_runs_service.finalize_run(run_id)
            db.session.commit()
            log_with_context(
                "error",
                "Veeam 备份同步失败",
                module="veeam",
                action="sync_backups_background",
                context={"created_by": created_by, "run_id": run_id},
                extra={"error_type": exc.__class__.__name__, "error_message": str(exc)},
                include_actor=False,
            )
            raise

    @staticmethod
    def _write_run_summary(*, run_id: str, payload: dict[str, object], error_message: str | None) -> None:
        current_run = TaskRun.query.filter_by(run_id=run_id).first()
        if current_run is None or current_run.status == "cancelled":
            return
        current_run.summary_json = payload
        current_run.error_message = error_message
