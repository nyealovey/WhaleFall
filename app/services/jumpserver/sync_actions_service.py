"""JumpServer 资源同步动作服务."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from flask import current_app, has_app_context

from app import db
from app.core.exceptions import ValidationError
from app.models.task_run import TaskRun
from app.infra.route_safety import log_with_context
from app.repositories.jumpserver_repository import JumpServerRepository
from app.services.jumpserver.provider import HttpJumpServerProvider, JumpServerProvider
from app.services.jumpserver.source_service import JumpServerSourceService
from app.services.task_runs.task_run_summary_builders import build_sync_jumpserver_assets_summary
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.time_utils import time_utils

_SYNC_ITEM_TYPE = "step"
_SYNC_ITEM_KEY = "sync_assets"
_SYNC_ITEM_NAME = "同步 JumpServer 资产"


@dataclass(frozen=True, slots=True)
class JumpServerSyncPreparedRun:
    """后台同步准备结果."""

    run_id: str
    credential_id: int


@dataclass(frozen=True, slots=True)
class JumpServerSyncLaunchResult:
    """后台同步启动结果."""

    run_id: str
    thread_name: str


class JumpServerSyncActionsService:
    """JumpServer 资源同步动作编排."""

    def __init__(
        self,
        *,
        source_service: JumpServerSourceService | None = None,
        jumpserver_repository: JumpServerRepository | None = None,
        provider: JumpServerProvider | None = None,
    ) -> None:
        self._source_service = source_service or JumpServerSourceService(provider=provider)
        self._jumpserver_repository = jumpserver_repository or JumpServerRepository()
        self._provider = provider or HttpJumpServerProvider()

    def prepare_background_sync(self, *, created_by: int | None) -> JumpServerSyncPreparedRun:
        """创建 TaskRun 并校验同步前置条件."""
        if not self._provider.is_configured():
            raise ValidationError("JumpServer Provider 尚未接入真实 API")
        binding = self._source_service.get_binding_or_error()
        credential = getattr(binding, "credential", None)
        if credential is None:
            raise ValidationError("JumpServer 数据源未绑定有效凭据")

        task_runs_service = TaskRunsWriteService()
        run_id = task_runs_service.start_run(
            task_key="sync_jumpserver_assets",
            task_name="JumpServer 资源同步",
            task_category="other",
            trigger_source="manual",
            created_by=created_by,
            summary_json=None,
            result_url="/admin/system-settings#system-settings-jumpserver",
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
        return JumpServerSyncPreparedRun(run_id=run_id, credential_id=int(binding.credential_id))

    def launch_background_sync(
        self,
        *,
        created_by: int | None,
        prepared: JumpServerSyncPreparedRun,
    ) -> JumpServerSyncLaunchResult:
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
            name="sync_jumpserver_assets_manual",
            daemon=True,
        )
        thread.start()
        return JumpServerSyncLaunchResult(run_id=prepared.run_id, thread_name=thread.name)

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
            raise ValidationError("JumpServer 数据源凭据已变更，请重新发起同步")

        task_runs_service = TaskRunsWriteService()
        synced_at = time_utils.now()
        try:
            task_runs_service.start_item(run_id, item_type=_SYNC_ITEM_TYPE, item_key=_SYNC_ITEM_KEY)
            result = self._provider.list_database_assets(
                base_url=str(binding.base_url or ""),
                access_key_id=str(credential.username or ""),
                access_key_secret=str(credential.get_plain_password() or ""),
                org_id=self._source_service.resolve_binding_org_id(binding),
                verify_ssl=self._source_service.resolve_binding_verify_ssl(binding),
            )
            self._jumpserver_repository.replace_asset_snapshots(result.assets, sync_run_id=run_id, synced_at=synced_at)
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
                    "supported_total": result.supported_total,
                    "snapshots_written_total": len(result.assets),
                    "skipped_unsupported": result.skipped_unsupported,
                    "skipped_invalid": result.skipped_invalid,
                },
                details_json={
                    "received_total": result.received_total,
                    "supported_total": result.supported_total,
                    "snapshots_written_total": len(result.assets),
                    "skipped_unsupported": result.skipped_unsupported,
                    "skipped_invalid": result.skipped_invalid,
                },
            )
            self._write_run_summary(
                run_id=run_id,
                payload=build_sync_jumpserver_assets_summary(
                    task_key="sync_jumpserver_assets",
                    inputs={"credential_id": int(binding.credential_id)},
                    received_total=result.received_total,
                    supported_total=result.supported_total,
                    snapshots_written_total=len(result.assets),
                    skipped_unsupported=result.skipped_unsupported,
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
                payload=build_sync_jumpserver_assets_summary(
                    task_key="sync_jumpserver_assets",
                    inputs={"credential_id": int(binding.credential_id)},
                    received_total=0,
                    supported_total=0,
                    snapshots_written_total=0,
                    skipped_unsupported=0,
                    skipped_invalid=0,
                    error_message=str(exc),
                ),
                error_message=str(exc),
            )
            task_runs_service.finalize_run(run_id)
            db.session.commit()
            log_with_context(
                "error",
                "JumpServer 资源同步失败",
                module="jumpserver",
                action="sync_assets_background",
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
