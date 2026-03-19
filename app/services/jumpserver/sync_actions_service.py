"""JumpServer 资源同步动作服务."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from flask import current_app, has_app_context

from app import db
from app.core.exceptions import ValidationError
from app.infra.route_safety import log_with_context
from app.repositories.jumpserver_repository import JumpServerRepository
from app.services.jumpserver.provider import DeferredJumpServerProvider, JumpServerProvider
from app.services.jumpserver.source_service import JumpServerSourceService
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService
from app.utils.time_utils import time_utils


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
        self._provider = provider or DeferredJumpServerProvider()

    def prepare_background_sync(self, *, created_by: int | None) -> JumpServerSyncPreparedRun:
        """创建 TaskRun 并校验同步前置条件."""
        if not self._provider.is_configured():
            raise ValidationError("JumpServer Provider 尚未接入真实 API")
        binding = self._source_service.get_binding_or_error()
        credential = getattr(binding, "credential", None)
        if credential is None:
            raise ValidationError("JumpServer 数据源未绑定有效凭据")

        run_id = TaskRunsWriteService().start_run(
            task_key="sync_jumpserver_assets",
            task_name="JumpServer 资源同步",
            task_category="other",
            trigger_source="manual",
            created_by=created_by,
            summary_json=None,
            result_url="/integrations/jumpserver/source",
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

        synced_at = time_utils.now()
        try:
            assets = self._provider.list_database_assets(
                base_url=str(binding.base_url or ""),
                access_key_id=str(credential.username or ""),
                access_key_secret=str(credential.get_plain_password() or ""),
            )
            self._jumpserver_repository.replace_asset_snapshots(assets, sync_run_id=run_id, synced_at=synced_at)
            binding.last_sync_at = synced_at
            binding.last_sync_status = "completed"
            binding.last_sync_run_id = run_id
            binding.last_error = None
            db.session.add(binding)
            db.session.commit()
        except Exception as exc:  # noqa: BLE001 - 统一记录 provider/网络/解析异常
            db.session.rollback()
            binding = self._source_service.get_binding_or_error()
            binding.last_sync_at = synced_at
            binding.last_sync_status = "failed"
            binding.last_sync_run_id = run_id
            binding.last_error = str(exc)
            db.session.add(binding)
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
