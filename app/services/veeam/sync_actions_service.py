"""Veeam 备份同步动作服务."""

from __future__ import annotations

import importlib
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.core.exceptions import ValidationError
from app.infra.route_safety import log_with_context
from app.models.task_run import TaskRun
from app.repositories.instances_repository import InstancesRepository
from app.repositories.veeam_repository import VeeamRepository
from app.services.task_runs.task_run_summary_builders import build_sync_veeam_backups_summary
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.services.veeam.matching import (
    build_instance_ip_candidates,
    build_instance_match_candidates,
    normalize_machine_name,
)
from app.services.veeam.provider import (
    HttpVeeamProvider,
    VeeamBackupFileCollection,
    VeeamBackupFileRecord,
    VeeamBackupObjectMatchResult,
    VeeamMachineBackupCollection,
    VeeamMachineBackupRecord,
    VeeamProvider,
    VeeamProviderSession,
    VeeamRestorePointsFetchError,
)
from app.services.veeam.source_service import VeeamSourceService
from app.utils.time_utils import time_utils

_SYNC_ITEM_TYPE = "step"
_FETCH_BACKUP_OBJECTS_ITEM_KEY = "fetch_backup_objects"
_FETCH_BACKUP_OBJECTS_ITEM_NAME = "获取 backupObjects"
_MATCH_BACKUP_OBJECTS_ITEM_KEY = "match_backup_objects"
_MATCH_BACKUP_OBJECTS_ITEM_NAME = "匹配目标备份对象"
_FETCH_RESTORE_POINTS_ITEM_KEY = "fetch_restore_points"
_FETCH_RESTORE_POINTS_ITEM_NAME = "拉取 restorePoints"
_FETCH_BACKUP_FILES_ITEM_KEY = "fetch_backup_files"
_FETCH_BACKUP_FILES_ITEM_NAME = "拉取 backupFiles"
_WRITE_SNAPSHOTS_ITEM_KEY = "write_snapshots"
_WRITE_SNAPSHOTS_ITEM_NAME = "写入快照"
_SYNC_STAGE_ITEMS: tuple[tuple[str, str], ...] = (
    (_FETCH_BACKUP_OBJECTS_ITEM_KEY, _FETCH_BACKUP_OBJECTS_ITEM_NAME),
    (_MATCH_BACKUP_OBJECTS_ITEM_KEY, _MATCH_BACKUP_OBJECTS_ITEM_NAME),
    (_FETCH_RESTORE_POINTS_ITEM_KEY, _FETCH_RESTORE_POINTS_ITEM_NAME),
    (_FETCH_BACKUP_FILES_ITEM_KEY, _FETCH_BACKUP_FILES_ITEM_NAME),
    (_WRITE_SNAPSHOTS_ITEM_KEY, _WRITE_SNAPSHOTS_ITEM_NAME),
)

BACKGROUND_SYNC_EXCEPTIONS: tuple[type[Exception], ...] = (
    ValidationError,
    SQLAlchemyError,
    RuntimeError,
    ValueError,
    LookupError,
)


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


def _resolve_default_task() -> Callable[..., Any]:
    """惰性加载默认任务函数,避免导入期循环依赖."""
    module = importlib.import_module("app.tasks.veeam_backup_sync_tasks")
    return cast("Callable[..., Any]", module.sync_veeam_backups)


def _launch_background_sync(
    *,
    created_by: int | None,
    run_id: str,
    task: Callable[..., Any],
) -> threading.Thread:
    def _run_task(captured_created_by: int | None, captured_run_id: str) -> None:
        try:
            task(manual_run=True, created_by=captured_created_by, run_id=captured_run_id)
        except BACKGROUND_SYNC_EXCEPTIONS as exc:
            log_with_context(
                "error",
                "后台 Veeam 备份同步失败",
                module="veeam",
                action="sync_backups_background",
                context={
                    "created_by": captured_created_by,
                    "run_id": captured_run_id,
                },
                extra={
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
                include_actor=False,
            )

    thread = threading.Thread(
        target=_run_task,
        args=(created_by, run_id),
        name="sync_veeam_backups_manual",
        daemon=True,
    )
    thread.start()
    return thread


class VeeamSyncActionsService:
    """Veeam 备份同步动作编排."""

    def __init__(
        self,
        *,
        source_service: VeeamSourceService | None = None,
        veeam_repository: VeeamRepository | None = None,
        instances_repository: InstancesRepository | None = None,
        provider: VeeamProvider | None = None,
        task: Callable[..., Any] | None = None,
    ) -> None:
        self._source_service = source_service or VeeamSourceService(provider=provider)
        self._veeam_repository = veeam_repository or VeeamRepository()
        self._instances_repository = instances_repository or InstancesRepository()
        self._provider = provider or HttpVeeamProvider()
        self._task = task or _resolve_default_task()

    def prepare_background_sync(
        self,
        *,
        created_by: int | None,
        trigger_source: str = "manual",
        result_url: str = "/admin/system-settings#system-settings-veeam",
    ) -> VeeamSyncPreparedRun:
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
            trigger_source=trigger_source,
            created_by=created_by,
            summary_json=None,
            result_url=result_url,
        )
        task_runs_service.init_items(
            run_id,
            items=[
                TaskRunItemInit(
                    item_type=_SYNC_ITEM_TYPE,
                    item_key=item_key,
                    item_name=item_name,
                )
                for item_key, item_name in _SYNC_STAGE_ITEMS
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
        thread = _launch_background_sync(
            created_by=created_by,
            run_id=prepared.run_id,
            task=self._task,
        )
        return VeeamSyncLaunchResult(run_id=prepared.run_id, thread_name=thread.name)

    def _sync_once(  # noqa: PLR0915
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
        sync_context = {"created_by": created_by, "run_id": run_id}
        current_stage_key: str | None = None
        session: VeeamProviderSession | object | None = None
        backup_items: list[dict[str, object]] = []
        match_result: VeeamBackupObjectMatchResult | object | None = None
        restore_points_result: VeeamMachineBackupCollection | object | None = None
        backup_files_result: VeeamBackupFileCollection | object | None = None
        latest_records: list[VeeamMachineBackupRecord] = []
        try:
            log_with_context(
                "info",
                "Veeam 备份同步开始",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "server_host": str(binding.server_host or ""),
                    "server_port": int(binding.server_port),
                    "api_version": str(binding.api_version or ""),
                    "verify_ssl": bool(binding.verify_ssl),
                },
                include_actor=False,
            )
            match_machine_names, match_machine_ips = self._build_all_match_candidates(
                match_domains=binding.match_domains
            )
            log_with_context(
                "info",
                "Veeam 候选机器池已构建",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "candidate_machine_count": len(match_machine_names),
                    "candidate_machine_sample": sorted(match_machine_names)[:20],
                    "candidate_ip_count": len(match_machine_ips),
                    "candidate_ip_sample": sorted(match_machine_ips)[:20],
                },
                include_actor=False,
            )
            current_stage_key = _FETCH_BACKUP_OBJECTS_ITEM_KEY
            self._start_stage(task_runs_service=task_runs_service, run_id=run_id, item_key=current_stage_key)
            session = self._provider.create_session(
                server_host=str(binding.server_host or ""),
                server_port=int(binding.server_port),
                username=str(credential.username or ""),
                password=str(credential.get_plain_password() or ""),
                api_version=str(binding.api_version or ""),
                verify_ssl=bool(binding.verify_ssl),
            )
            backup_items = self._provider.fetch_backup_objects(session=cast("VeeamProviderSession", session))
            self._complete_stage(
                task_runs_service=task_runs_service,
                run_id=run_id,
                item_key=current_stage_key,
                metrics_json={"backup_objects_received_total": len(backup_items)},
                details_json=self._build_fetch_backup_objects_details(backup_objects_received_total=len(backup_items)),
            )

            current_stage_key = _MATCH_BACKUP_OBJECTS_ITEM_KEY
            self._start_stage(task_runs_service=task_runs_service, run_id=run_id, item_key=current_stage_key)
            match_result = self._provider.match_backup_objects(
                backup_items=cast("list[dict[str, object]]", backup_items),
                match_machine_names=match_machine_names,
                match_machine_ips=match_machine_ips,
            )
            log_with_context(
                "info",
                "Veeam 备份链匹配完成",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "backups_received_total": getattr(match_result, "backups_received_total", 0),
                    "backups_matched_total": getattr(match_result, "backups_matched_total", 0),
                    "backups_unmatched_total": getattr(match_result, "backups_unmatched_total", 0),
                    "backups_missing_machine_name": getattr(match_result, "backups_missing_machine_name", 0),
                    "backup_objects_received_total": getattr(match_result, "backups_received_total", 0),
                    "backup_objects_matched_total": getattr(match_result, "backups_matched_total", 0),
                    "backup_objects_unmatched_total": getattr(match_result, "backups_unmatched_total", 0),
                    "backup_objects_missing_machine_name": getattr(match_result, "backups_missing_machine_name", 0),
                    "matched_backup_ids_sample": getattr(match_result, "matched_backup_ids_sample", []),
                    "unmatched_backup_ids_sample": getattr(match_result, "unmatched_backup_ids_sample", []),
                    "unmatched_machine_names_sample": getattr(match_result, "unmatched_machine_names_sample", []),
                    "missing_machine_name_backup_ids_sample": getattr(
                        match_result, "missing_machine_name_backup_ids_sample", []
                    ),
                    "missing_machine_name_backup_names_sample": getattr(
                        match_result, "missing_machine_name_backup_names_sample", []
                    ),
                },
                include_actor=False,
            )
            self._complete_stage(
                task_runs_service=task_runs_service,
                run_id=run_id,
                item_key=current_stage_key,
                metrics_json={
                    "candidate_machine_count": len(match_machine_names),
                    "backups_received_total": getattr(match_result, "backups_received_total", 0),
                    "matched_backup_objects_total": getattr(match_result, "backups_matched_total", 0),
                    "unmatched_backup_objects_total": getattr(match_result, "backups_unmatched_total", 0),
                    "missing_machine_name_backup_objects_total": getattr(
                        match_result, "backups_missing_machine_name", 0
                    ),
                },
                details_json=self._build_match_backup_objects_details(
                    candidate_machine_count=len(match_machine_names),
                    match_result=cast("VeeamBackupObjectMatchResult", match_result),
                ),
            )

            if getattr(match_result, "backups_matched_total", 0) <= 0:
                log_with_context(
                    "warning",
                    "Veeam 未命中任何备份链",
                    module="veeam",
                    action="sync_backups_background",
                    context=sync_context,
                    extra={
                        "candidate_machine_count": len(match_machine_names),
                        "candidate_machine_sample": sorted(match_machine_names)[:20],
                        "backups_received_total": getattr(match_result, "backups_received_total", 0),
                        "backups_missing_machine_name": getattr(match_result, "backups_missing_machine_name", 0),
                        "backup_objects_received_total": getattr(match_result, "backups_received_total", 0),
                        "backup_objects_missing_machine_name": getattr(match_result, "backups_missing_machine_name", 0),
                        "unmatched_backup_ids_sample": getattr(match_result, "unmatched_backup_ids_sample", []),
                        "unmatched_machine_names_sample": getattr(match_result, "unmatched_machine_names_sample", []),
                        "missing_machine_name_backup_ids_sample": getattr(
                            match_result, "missing_machine_name_backup_ids_sample", []
                        ),
                        "missing_machine_name_backup_names_sample": getattr(
                            match_result, "missing_machine_name_backup_names_sample", []
                        ),
                    },
                    include_actor=False,
                )

            current_stage_key = _FETCH_RESTORE_POINTS_ITEM_KEY
            self._start_stage(task_runs_service=task_runs_service, run_id=run_id, item_key=current_stage_key)
            restore_points_result = self._provider.fetch_restore_point_records(
                session=cast("VeeamProviderSession", session),
                match_result=cast("VeeamBackupObjectMatchResult", match_result),
            )
            timed_out_backup_objects_total = int(
                getattr(restore_points_result, "timed_out_backup_objects_total", 0) or 0
            )
            failed_backup_objects_total = int(getattr(restore_points_result, "failed_backup_objects_total", 0) or 0)
            completed_backup_objects_total = int(
                getattr(restore_points_result, "restore_points_backup_objects_completed", 0) or 0
            )
            skipped_backup_objects_total = timed_out_backup_objects_total + failed_backup_objects_total
            if skipped_backup_objects_total > 0 and completed_backup_objects_total > 0:
                log_with_context(
                    "warning",
                    "Veeam restorePoints 拉取部分超时/失败，已跳过异常对象",
                    module="veeam",
                    action="sync_backups_background",
                    context=sync_context,
                    extra={
                        "matched_backup_objects_total": getattr(
                            restore_points_result, "restore_points_backup_objects_total", 0
                        ),
                        "restore_points_backup_objects_completed": completed_backup_objects_total,
                        "timed_out_backup_objects_total": timed_out_backup_objects_total,
                        "timed_out_backup_ids_sample": getattr(
                            restore_points_result, "timed_out_backup_ids_sample", []
                        ),
                        "timed_out_machine_names_sample": getattr(
                            restore_points_result,
                            "timed_out_machine_names_sample",
                            [],
                        ),
                        "failed_backup_objects_total": failed_backup_objects_total,
                        "failed_backup_ids_sample": getattr(restore_points_result, "failed_backup_ids_sample", []),
                        "failed_machine_names_sample": getattr(
                            restore_points_result, "failed_machine_names_sample", []
                        ),
                    },
                    include_actor=False,
                )
            if skipped_backup_objects_total > 0 and completed_backup_objects_total <= 0:
                self._raise_restore_points_all_timeout(
                    restore_points_result=cast("VeeamMachineBackupCollection", restore_points_result),
                    match_result=cast("VeeamBackupObjectMatchResult", match_result),
                )
            self._complete_stage(
                task_runs_service=task_runs_service,
                run_id=run_id,
                item_key=current_stage_key,
                metrics_json={
                    "matched_backup_objects_total": getattr(
                        restore_points_result, "restore_points_backup_objects_total", 0
                    ),
                    "restore_points_backup_objects_completed": getattr(
                        restore_points_result,
                        "restore_points_backup_objects_completed",
                        0,
                    ),
                    "restore_points_received_total": getattr(restore_points_result, "received_total", 0),
                    "skipped_invalid": getattr(restore_points_result, "skipped_invalid", 0),
                    "timed_out_backup_objects_total": timed_out_backup_objects_total,
                    "failed_backup_objects_total": failed_backup_objects_total,
                },
                details_json=self._build_fetch_restore_points_details(
                    match_result=cast("VeeamBackupObjectMatchResult", match_result),
                    result=cast("VeeamMachineBackupCollection", restore_points_result),
                ),
            )

            current_stage_key = _FETCH_BACKUP_FILES_ITEM_KEY
            self._start_stage(task_runs_service=task_runs_service, run_id=run_id, item_key=current_stage_key)
            restore_point_records = list(cast("VeeamMachineBackupCollection", restore_points_result).records)
            backup_ids = self._collect_unique_strings([record.backup_id for record in restore_point_records])
            backup_files_result = self._provider.fetch_backup_file_records(
                session=cast("VeeamProviderSession", session),
                backup_ids=backup_ids,
            )
            backup_file_coverage = self._summarize_backup_file_coverage(
                records=restore_point_records,
                backup_files_result=cast("VeeamBackupFileCollection", backup_files_result),
            )
            backup_files_partial_success = self._is_backup_files_partial_success(
                backup_ids_total=int(getattr(backup_files_result, "backup_ids_total", 0) or 0),
                backup_ids_completed=int(getattr(backup_files_result, "backup_ids_completed", 0) or 0),
                timed_out_backup_ids_total=int(getattr(backup_files_result, "timed_out_backup_ids_total", 0) or 0),
                failed_backup_ids_total=int(getattr(backup_files_result, "failed_backup_ids_total", 0) or 0),
            ) or bool(backup_file_coverage["restore_points_missing_metrics_total"])
            if backup_files_partial_success:
                log_with_context(
                    "warning",
                    "Veeam backupFiles 拉取存在缺口，已按部分成功继续",
                    module="veeam",
                    action="sync_backups_background",
                    context=sync_context,
                    extra={
                        "backup_ids_total": getattr(backup_files_result, "backup_ids_total", 0),
                        "backup_ids_completed": getattr(backup_files_result, "backup_ids_completed", 0),
                        "backup_files_scanned_total": getattr(backup_files_result, "received_total", 0),
                        "timed_out_backup_ids_total": getattr(backup_files_result, "timed_out_backup_ids_total", 0),
                        "timed_out_backup_ids_sample": getattr(backup_files_result, "timed_out_backup_ids_sample", []),
                        "failed_backup_ids_total": getattr(backup_files_result, "failed_backup_ids_total", 0),
                        "failed_backup_ids_sample": getattr(backup_files_result, "failed_backup_ids_sample", []),
                        "failed_urls_sample": getattr(backup_files_result, "failed_urls_sample", []),
                        "restore_points_expected_total": backup_file_coverage["restore_points_expected_total"],
                        "restore_points_enriched_total": backup_file_coverage["restore_points_enriched_total"],
                        "restore_points_missing_metrics_total": backup_file_coverage[
                            "restore_points_missing_metrics_total"
                        ],
                        "backup_ids_fully_covered_total": backup_file_coverage["backup_ids_fully_covered_total"],
                        "backup_ids_partially_covered_total": backup_file_coverage[
                            "backup_ids_partially_covered_total"
                        ],
                    },
                    include_actor=False,
                )
            self._complete_stage(
                task_runs_service=task_runs_service,
                run_id=run_id,
                item_key=current_stage_key,
                metrics_json={
                    "backup_ids_total": getattr(backup_files_result, "backup_ids_total", 0),
                    "backup_ids_completed": getattr(backup_files_result, "backup_ids_completed", 0),
                    "backup_files_scanned_total": getattr(backup_files_result, "received_total", 0),
                    "timed_out_backup_ids_total": getattr(backup_files_result, "timed_out_backup_ids_total", 0),
                    "failed_backup_ids_total": getattr(backup_files_result, "failed_backup_ids_total", 0),
                    "restore_points_expected_total": backup_file_coverage["restore_points_expected_total"],
                    "restore_points_enriched_total": backup_file_coverage["restore_points_enriched_total"],
                    "restore_points_missing_metrics_total": backup_file_coverage[
                        "restore_points_missing_metrics_total"
                    ],
                    "backup_ids_fully_covered_total": backup_file_coverage["backup_ids_fully_covered_total"],
                    "backup_ids_partially_covered_total": backup_file_coverage["backup_ids_partially_covered_total"],
                },
                details_json=self._build_fetch_backup_files_details(
                    backup_ids_total=len(backup_ids),
                    result=cast("VeeamBackupFileCollection", backup_files_result),
                    coverage=backup_file_coverage,
                ),
            )

            enriched_restore_point_records = self._merge_backup_file_metrics_into_records(
                records=restore_point_records,
                backup_files_result=cast("VeeamBackupFileCollection", backup_files_result),
            )
            latest_records = self._select_latest_records(enriched_restore_point_records)
            log_with_context(
                "info",
                "Veeam 最新机器快照已筛选",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "latest_machine_count": len(latest_records),
                    "latest_machine_names_sample": [record.machine_name for record in latest_records[:20]],
                },
                include_actor=False,
            )
            current_stage_key = _WRITE_SNAPSHOTS_ITEM_KEY
            self._start_stage(task_runs_service=task_runs_service, run_id=run_id, item_key=current_stage_key)
            self._validate_records_to_write(latest_records)
            snapshots_written_total = self._veeam_repository.replace_machine_backup_snapshots(
                latest_records,
                sync_run_id=run_id,
                synced_at=synced_at,
            )
            binding.last_sync_at = synced_at
            binding.last_sync_status = "completed"
            binding.last_sync_run_id = run_id
            binding.last_error = None
            db.session.add(binding)
            log_with_context(
                "info",
                "Veeam 快照写入完成",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={"snapshots_written_total": snapshots_written_total},
                include_actor=False,
            )
            task_runs_service.complete_item(
                run_id,
                item_type=_SYNC_ITEM_TYPE,
                item_key=current_stage_key,
                metrics_json={
                    "latest_machine_count": len(latest_records),
                    "snapshots_written_total": snapshots_written_total,
                },
                details_json=self._build_write_snapshots_details(
                    latest_machine_count=len(latest_records),
                    snapshots_written_total=snapshots_written_total,
                ),
            )
            self._write_run_summary(
                run_id=run_id,
                payload=build_sync_veeam_backups_summary(
                    task_key="sync_veeam_backups",
                    inputs={"credential_id": int(binding.credential_id)},
                    received_total=cast("VeeamMachineBackupCollection", restore_points_result).received_total,
                    snapshots_written_total=snapshots_written_total,
                    skipped_invalid=cast("VeeamMachineBackupCollection", restore_points_result).skipped_invalid,
                    timed_out_backup_objects_total=timed_out_backup_objects_total,
                    backup_files_scanned_total=int(getattr(backup_files_result, "received_total", 0) or 0),
                    backup_ids_total=int(getattr(backup_files_result, "backup_ids_total", 0) or 0),
                    backup_ids_completed=int(getattr(backup_files_result, "backup_ids_completed", 0) or 0),
                    timed_out_backup_ids_total=int(getattr(backup_files_result, "timed_out_backup_ids_total", 0) or 0),
                    failed_backup_ids_total=int(getattr(backup_files_result, "failed_backup_ids_total", 0) or 0),
                    restore_points_expected_total=int(backup_file_coverage["restore_points_expected_total"]),
                    restore_points_enriched_total=int(backup_file_coverage["restore_points_enriched_total"]),
                    restore_points_missing_metrics_total=int(
                        backup_file_coverage["restore_points_missing_metrics_total"]
                    ),
                    backup_ids_fully_covered_total=int(backup_file_coverage["backup_ids_fully_covered_total"]),
                    backup_ids_partially_covered_total=int(backup_file_coverage["backup_ids_partially_covered_total"]),
                    partial_success=(skipped_backup_objects_total > 0 or backup_files_partial_success),
                    error_message=None,
                ),
                error_message=None,
            )
            task_runs_service.finalize_run(run_id)
            db.session.commit()
            log_with_context(
                "info",
                "Veeam 备份同步完成",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "candidate_machine_count": len(match_machine_names),
                    "backups_received_total": getattr(match_result, "backups_received_total", 0),
                    "backups_matched_total": getattr(match_result, "backups_matched_total", 0),
                    "backups_unmatched_total": getattr(match_result, "backups_unmatched_total", 0),
                    "backups_missing_machine_name": getattr(match_result, "backups_missing_machine_name", 0),
                    "backup_objects_received_total": getattr(match_result, "backups_received_total", 0),
                    "backup_objects_matched_total": getattr(match_result, "backups_matched_total", 0),
                    "backup_objects_unmatched_total": getattr(match_result, "backups_unmatched_total", 0),
                    "backup_objects_missing_machine_name": getattr(match_result, "backups_missing_machine_name", 0),
                    "missing_machine_name_backup_ids_sample": getattr(
                        match_result, "missing_machine_name_backup_ids_sample", []
                    ),
                    "restore_points_received_total": getattr(restore_points_result, "received_total", 0),
                    "timed_out_backup_objects_total": timed_out_backup_objects_total,
                    "failed_backup_objects_total": failed_backup_objects_total,
                    "backup_ids_total": getattr(backup_files_result, "backup_ids_total", 0),
                    "backup_ids_completed": getattr(backup_files_result, "backup_ids_completed", 0),
                    "backup_files_scanned_total": getattr(backup_files_result, "received_total", 0),
                    "timed_out_backup_ids_total": getattr(backup_files_result, "timed_out_backup_ids_total", 0),
                    "failed_backup_ids_total": getattr(backup_files_result, "failed_backup_ids_total", 0),
                    "restore_points_expected_total": backup_file_coverage["restore_points_expected_total"],
                    "restore_points_enriched_total": backup_file_coverage["restore_points_enriched_total"],
                    "restore_points_missing_metrics_total": backup_file_coverage[
                        "restore_points_missing_metrics_total"
                    ],
                    "backup_ids_fully_covered_total": backup_file_coverage["backup_ids_fully_covered_total"],
                    "backup_ids_partially_covered_total": backup_file_coverage["backup_ids_partially_covered_total"],
                    "latest_machine_count": len(latest_records),
                    "snapshots_written_total": snapshots_written_total,
                    "skipped_invalid": getattr(restore_points_result, "skipped_invalid", 0),
                },
                include_actor=False,
            )
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
                item_key=current_stage_key or _FETCH_BACKUP_OBJECTS_ITEM_KEY,
                error_message=str(exc),
                details_json=self._build_failed_stage_details(
                    stage_key=current_stage_key,
                    error_message=str(exc),
                    match_result=cast("VeeamBackupObjectMatchResult | None", match_result),
                    exception=exc,
                ),
            )
            self._cancel_following_stages(
                task_runs_service=task_runs_service,
                run_id=run_id,
                current_stage_key=current_stage_key,
            )
            self._write_run_summary(
                run_id=run_id,
                payload=build_sync_veeam_backups_summary(
                    task_key="sync_veeam_backups",
                    inputs={"credential_id": int(binding.credential_id)},
                    received_total=0,
                    snapshots_written_total=0,
                    skipped_invalid=0,
                    timed_out_backup_objects_total=0,
                    partial_success=False,
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
                context=sync_context,
                extra={"error_type": exc.__class__.__name__, "error_message": str(exc), "stage": "sync_backups"},
                include_actor=False,
            )
            raise

    @staticmethod
    def _start_stage(*, task_runs_service: TaskRunsWriteService, run_id: str, item_key: str) -> None:
        task_runs_service.start_item(run_id, item_type=_SYNC_ITEM_TYPE, item_key=item_key)
        db.session.commit()

    @staticmethod
    def _complete_stage(
        *,
        task_runs_service: TaskRunsWriteService,
        run_id: str,
        item_key: str,
        metrics_json: dict[str, object],
        details_json: dict[str, object],
    ) -> None:
        task_runs_service.complete_item(
            run_id,
            item_type=_SYNC_ITEM_TYPE,
            item_key=item_key,
            metrics_json=metrics_json,
            details_json=details_json,
        )
        db.session.commit()

    @staticmethod
    def _build_fetch_backup_objects_details(*, backup_objects_received_total: int) -> dict[str, object]:
        return {
            "summary": f"共拉取 {backup_objects_received_total} 个 backupObjects",
            "backup_objects_received_total": backup_objects_received_total,
        }

    @staticmethod
    def _build_match_backup_objects_details(
        *,
        candidate_machine_count: int,
        match_result: VeeamBackupObjectMatchResult,
    ) -> dict[str, object]:
        return {
            "summary": f"候选机器 {candidate_machine_count} 个 · 匹配 {match_result.backups_matched_total} 个对象",
            "candidate_machine_count": candidate_machine_count,
            "backup_objects_received_total": match_result.backups_received_total,
            "matched_backup_objects_total": match_result.backups_matched_total,
            "unmatched_backup_objects_total": match_result.backups_unmatched_total,
            "missing_machine_name_backup_objects_total": match_result.backups_missing_machine_name,
            "matched_backup_ids_sample": list(match_result.matched_backup_ids_sample),
            "unmatched_backup_ids_sample": list(match_result.unmatched_backup_ids_sample),
            "unmatched_machine_names_sample": list(match_result.unmatched_machine_names_sample),
            "missing_machine_name_backup_ids_sample": list(match_result.missing_machine_name_backup_ids_sample),
            "missing_machine_name_backup_names_sample": list(match_result.missing_machine_name_backup_names_sample),
        }

    @staticmethod
    def _build_fetch_restore_points_details(
        *,
        match_result: VeeamBackupObjectMatchResult,
        result: VeeamMachineBackupCollection,
    ) -> dict[str, object]:
        total = int(
            getattr(result, "restore_points_backup_objects_total", 0) or match_result.backups_matched_total or 0
        )
        completed = int(getattr(result, "restore_points_backup_objects_completed", 0) or 0)
        timed_out = int(getattr(result, "timed_out_backup_objects_total", 0) or 0)
        failed = int(getattr(result, "failed_backup_objects_total", 0) or 0)
        summary = (
            f"已完成 {completed}/{total} 个对象 · 超时跳过 {timed_out} 个 · 失败跳过 {failed} 个 · 拉取 {result.received_total} 条恢复点"
            if total > 0
            else "无匹配对象，跳过 restorePoints 拉取"
        )
        return {
            "summary": summary,
            "matched_backup_objects_total": total,
            "restore_points_backup_objects_completed": completed,
            "restore_points_received_total": result.received_total,
            "skipped_invalid": result.skipped_invalid,
            "matched_backup_ids_sample": list(match_result.matched_backup_ids_sample),
            "timed_out_backup_objects_total": timed_out,
            "timed_out_backup_ids_sample": list(getattr(result, "timed_out_backup_ids_sample", [])),
            "timed_out_machine_names_sample": list(getattr(result, "timed_out_machine_names_sample", [])),
            "failed_backup_objects_total": failed,
            "failed_backup_ids_sample": list(getattr(result, "failed_backup_ids_sample", [])),
            "failed_machine_names_sample": list(getattr(result, "failed_machine_names_sample", [])),
        }

    @staticmethod
    def _build_fetch_backup_files_details(
        *,
        backup_ids_total: int,
        result: VeeamBackupFileCollection,
        coverage: dict[str, int],
    ) -> dict[str, object]:
        completed = int(getattr(result, "backup_ids_completed", 0) or 0)
        timed_out = int(getattr(result, "timed_out_backup_ids_total", 0) or 0)
        failed = int(getattr(result, "failed_backup_ids_total", 0) or 0)
        summary = (
            f"已完成 {completed}/{backup_ids_total} 个备份 · 全覆盖 {coverage['backup_ids_fully_covered_total']} 个 · 部分覆盖 {coverage['backup_ids_partially_covered_total']} 个 · 超时跳过 {timed_out} 个备份 · 失败跳过 {failed} 个备份 · 有效补齐 {coverage['restore_points_enriched_total']}/{coverage['restore_points_expected_total']} 个恢复点"
            if backup_ids_total > 0
            else "无有效 backupId，跳过 backupFiles 拉取"
        )
        return {
            "summary": summary,
            "backup_ids_total": backup_ids_total,
            "backup_ids_completed": completed,
            "backup_files_scanned_total": result.received_total,
            "timed_out_backup_ids_total": timed_out,
            "timed_out_backup_ids_sample": list(getattr(result, "timed_out_backup_ids_sample", [])),
            "failed_backup_ids_total": failed,
            "failed_backup_ids_sample": list(getattr(result, "failed_backup_ids_sample", [])),
            "failed_urls_sample": list(getattr(result, "failed_urls_sample", [])),
            "restore_points_expected_total": coverage["restore_points_expected_total"],
            "restore_points_enriched_total": coverage["restore_points_enriched_total"],
            "restore_points_missing_metrics_total": coverage["restore_points_missing_metrics_total"],
            "backup_ids_fully_covered_total": coverage["backup_ids_fully_covered_total"],
            "backup_ids_partially_covered_total": coverage["backup_ids_partially_covered_total"],
        }

    @staticmethod
    def _build_write_snapshots_details(*, latest_machine_count: int, snapshots_written_total: int) -> dict[str, object]:
        return {
            "summary": f"已筛选 {latest_machine_count} 台机器 · 写入 {snapshots_written_total} 条快照",
            "latest_machine_count": latest_machine_count,
            "snapshots_written_total": snapshots_written_total,
        }

    @staticmethod
    def _build_failed_stage_details(
        *,
        stage_key: str | None,
        error_message: str,
        match_result: VeeamBackupObjectMatchResult | None,
        exception: Exception,
    ) -> dict[str, object]:
        if stage_key == _FETCH_RESTORE_POINTS_ITEM_KEY:
            matched_total = int(
                getattr(exception, "matched_backup_objects_total", 0)
                or getattr(match_result, "backups_matched_total", 0)
            )
            completed_total = int(getattr(exception, "completed_backup_objects_total", 0))
            return {
                "summary": (
                    f"已完成 {completed_total}/{matched_total} 个对象，当前对象 restorePoints 拉取失败"
                    if matched_total > 0
                    else "restorePoints 拉取失败"
                ),
                "matched_backup_objects_total": matched_total,
                "restore_points_backup_objects_completed": completed_total,
                "failed_backup_object_id": getattr(exception, "failed_backup_object_id", None),
                "failed_machine_name": getattr(exception, "failed_machine_name", None),
                "failed_url": getattr(exception, "failed_url", None),
                "error_message": error_message,
            }
        if stage_key == _FETCH_BACKUP_OBJECTS_ITEM_KEY:
            return {"summary": "拉取 backupObjects 失败", "error_message": error_message}
        if stage_key == _MATCH_BACKUP_OBJECTS_ITEM_KEY:
            return {"summary": "匹配目标备份对象失败", "error_message": error_message}
        if stage_key == _FETCH_BACKUP_FILES_ITEM_KEY:
            return {"summary": "拉取 backupFiles 失败", "error_message": error_message}
        if stage_key == _WRITE_SNAPSHOTS_ITEM_KEY:
            return {"summary": "写入快照失败", "error_message": error_message}
        return {"error_message": error_message}

    @staticmethod
    def _cancel_following_stages(
        *,
        task_runs_service: TaskRunsWriteService,
        run_id: str,
        current_stage_key: str | None,
    ) -> None:
        stage_keys = [item_key for item_key, _ in _SYNC_STAGE_ITEMS]
        if current_stage_key not in stage_keys:
            return
        current_index = stage_keys.index(current_stage_key)
        for item_key in stage_keys[current_index + 1 :]:
            task_runs_service.cancel_item(
                run_id,
                item_type=_SYNC_ITEM_TYPE,
                item_key=item_key,
                details_json={"summary": "前序步骤失败，未继续执行"},
            )

    @staticmethod
    def _write_run_summary(*, run_id: str, payload: dict[str, object], error_message: str | None) -> None:
        current_run = TaskRun.query.filter_by(run_id=run_id).first()
        if current_run is None or current_run.status == "cancelled":
            return
        current_run.summary_json = payload
        current_run.error_message = error_message

    def _build_all_match_candidates(self, *, match_domains: object) -> tuple[set[str], set[str]]:
        domains = match_domains if isinstance(match_domains, list) else []
        instances = self._instances_repository.list_existing_instances()
        matched_machine_names: set[str] = set()
        matched_machine_ips: set[str] = set()
        for instance in instances:
            matched_machine_names.update(build_instance_match_candidates(getattr(instance, "name", None), domains))
            matched_machine_ips.update(build_instance_ip_candidates(getattr(instance, "host", None)))
        return matched_machine_names, matched_machine_ips

    @staticmethod
    def _select_latest_records(records: list[VeeamMachineBackupRecord]) -> list[VeeamMachineBackupRecord]:
        latest_by_machine: dict[str, VeeamMachineBackupRecord] = {}
        records_by_machine: dict[str, list[VeeamMachineBackupRecord]] = {}
        for record in records:
            normalized_machine_name = normalize_machine_name(record.machine_name)
            if not normalized_machine_name:
                continue
            records_by_machine.setdefault(normalized_machine_name, []).append(record)
            current = latest_by_machine.get(normalized_machine_name)
            if current is None or record.backup_at > current.backup_at:
                latest_by_machine[normalized_machine_name] = record
        return [
            VeeamSyncActionsService._attach_restore_point_snapshot(
                latest_record=record,
                related_records=records_by_machine.get(normalized_machine_name, []),
            )
            for normalized_machine_name, record in latest_by_machine.items()
        ]

    @staticmethod
    def _attach_restore_point_snapshot(
        *,
        latest_record: VeeamMachineBackupRecord,
        related_records: list[VeeamMachineBackupRecord],
    ) -> VeeamMachineBackupRecord:
        ordered_records = sorted(
            related_records,
            key=lambda item: (item.backup_at, item.source_record_id or ""),
            reverse=True,
        )
        restore_point_ids = VeeamSyncActionsService._collect_unique_strings(
            [record.source_record_id for record in ordered_records]
        )
        restore_point_times = [record.backup_at.isoformat() for record in ordered_records]
        raw_payload = dict(latest_record.raw_payload)
        if restore_point_ids:
            raw_payload["restore_point_ids"] = restore_point_ids
        if restore_point_times:
            raw_payload["restore_point_times"] = restore_point_times
        raw_payload["restore_points"] = [
            VeeamSyncActionsService._serialize_restore_point_payload(record) for record in ordered_records
        ]
        backup_size_values = [
            value
            for record in ordered_records
            if (
                value := VeeamSyncActionsService._extract_backup_metric_int(
                    record.raw_payload,
                    ("backupSize", "backup_size", "backupSizeBytes", "backup_size_bytes"),
                )
            )
            is not None
        ]
        restore_point_size_bytes = (
            latest_record.restore_point_size_bytes
            or VeeamSyncActionsService._extract_backup_metric_int(
                latest_record.raw_payload,
                ("dataSize", "data_size", "dataSizeBytes", "data_size_bytes"),
            )
        )
        resolved_restore_point_count = (
            len(restore_point_ids) or len(restore_point_times) or latest_record.restore_point_count
        )
        return VeeamMachineBackupRecord(
            machine_name=latest_record.machine_name,
            backup_at=latest_record.backup_at,
            backup_id=latest_record.backup_id,
            backup_file_id=latest_record.backup_file_id,
            job_name=latest_record.job_name,
            restore_point_name=latest_record.restore_point_name,
            source_record_id=latest_record.source_record_id,
            restore_point_size_bytes=restore_point_size_bytes,
            backup_chain_size_bytes=(
                sum(backup_size_values) if backup_size_values else latest_record.backup_chain_size_bytes
            ),
            restore_point_count=resolved_restore_point_count,
            raw_payload=raw_payload,
        )

    @staticmethod
    def _serialize_restore_point_payload(record: VeeamMachineBackupRecord) -> dict[str, object]:
        payload = dict(record.raw_payload) if isinstance(record.raw_payload, dict) else {}
        if record.source_record_id and not payload.get("id"):
            payload["id"] = record.source_record_id
        if record.restore_point_name and not payload.get("name"):
            payload["name"] = record.restore_point_name
        if record.backup_id and not payload.get("backupId"):
            payload["backupId"] = record.backup_id
        if record.backup_file_id and not payload.get("backupFileId"):
            payload["backupFileId"] = record.backup_file_id
        if record.backup_at and not payload.get("creationTime"):
            payload["creationTime"] = record.backup_at.isoformat()
        return payload

    @staticmethod
    def _collect_unique_strings(values: list[str | None]) -> list[str]:
        collected: list[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            if not normalized or normalized in collected:
                continue
            collected.append(normalized)
        return collected

    @staticmethod
    def _is_backup_files_partial_success(
        *,
        backup_ids_total: int,
        backup_ids_completed: int,
        timed_out_backup_ids_total: int,
        failed_backup_ids_total: int,
    ) -> bool:
        if timed_out_backup_ids_total > 0 or failed_backup_ids_total > 0:
            return True
        return backup_ids_total > 0 and backup_ids_completed < backup_ids_total

    @staticmethod
    def _summarize_backup_file_coverage(
        *,
        records: list[VeeamMachineBackupRecord],
        backup_files_result: VeeamBackupFileCollection,
    ) -> dict[str, int]:
        expected_restore_point_ids_by_backup: dict[str, set[str]] = {}
        for record in records:
            backup_id = str(record.backup_id or "").strip()
            restore_point_id = str(record.source_record_id or "").strip()
            if not backup_id or not restore_point_id:
                continue
            expected_restore_point_ids_by_backup.setdefault(backup_id, set()).add(restore_point_id)

        matched_restore_point_ids_by_backup: dict[str, set[str]] = {
            backup_id: set() for backup_id in expected_restore_point_ids_by_backup
        }
        for backup_file in backup_files_result.records:
            backup_id = str(backup_file.backup_id or "").strip()
            if backup_id not in expected_restore_point_ids_by_backup:
                continue
            expected_restore_point_ids = expected_restore_point_ids_by_backup[backup_id]
            matched_restore_point_ids = matched_restore_point_ids_by_backup.setdefault(backup_id, set())
            for restore_point_id in backup_file.restore_point_ids:
                normalized_restore_point_id = str(restore_point_id or "").strip()
                if normalized_restore_point_id and normalized_restore_point_id in expected_restore_point_ids:
                    matched_restore_point_ids.add(normalized_restore_point_id)

        restore_points_expected_total = sum(
            len(restore_point_ids) for restore_point_ids in expected_restore_point_ids_by_backup.values()
        )
        restore_points_enriched_total = sum(
            len(restore_point_ids) for restore_point_ids in matched_restore_point_ids_by_backup.values()
        )
        backup_ids_fully_covered_total = 0
        backup_ids_partially_covered_total = 0
        for backup_id, expected_restore_point_ids in expected_restore_point_ids_by_backup.items():
            matched_count = len(matched_restore_point_ids_by_backup.get(backup_id, set()))
            expected_count = len(expected_restore_point_ids)
            if expected_count <= 0 or matched_count <= 0:
                continue
            if matched_count >= expected_count:
                backup_ids_fully_covered_total += 1
                continue
            backup_ids_partially_covered_total += 1

        return {
            "restore_points_expected_total": restore_points_expected_total,
            "restore_points_enriched_total": restore_points_enriched_total,
            "restore_points_missing_metrics_total": max(
                restore_points_expected_total - restore_points_enriched_total, 0
            ),
            "backup_ids_fully_covered_total": backup_ids_fully_covered_total,
            "backup_ids_partially_covered_total": backup_ids_partially_covered_total,
        }

    @staticmethod
    def _merge_backup_file_metrics_into_records(  # noqa: PLR0912
        *,
        records: list[VeeamMachineBackupRecord],
        backup_files_result: VeeamBackupFileCollection,
    ) -> list[VeeamMachineBackupRecord]:
        if not records or not backup_files_result.records:
            return records

        backup_files_by_restore_point_id: dict[str, list[VeeamBackupFileRecord]] = {}
        for backup_file in backup_files_result.records:
            for restore_point_id in backup_file.restore_point_ids:
                normalized_restore_point_id = str(restore_point_id or "").strip()
                if not normalized_restore_point_id:
                    continue
                backup_files_by_restore_point_id.setdefault(normalized_restore_point_id, []).append(backup_file)

        merged_records: list[VeeamMachineBackupRecord] = []
        for record in records:
            restore_point_id = str(record.source_record_id or "").strip()
            candidates = backup_files_by_restore_point_id.get(restore_point_id, [])
            selected = VeeamSyncActionsService._select_best_backup_file_record(record=record, candidates=candidates)
            if selected is None:
                merged_records.append(record)
                continue

            merged_payload = dict(record.raw_payload) if isinstance(record.raw_payload, dict) else {}
            if selected.object_id and not merged_payload.get("objectId"):
                merged_payload["objectId"] = selected.object_id
            if selected.restore_point_ids:
                merged_payload["restorePointIds"] = list(selected.restore_point_ids)
            if selected.data_size_bytes is not None:
                merged_payload["dataSize"] = selected.data_size_bytes
            if selected.backup_size_bytes is not None:
                merged_payload["backupSize"] = selected.backup_size_bytes
            if selected.dedup_ratio is not None:
                merged_payload["dedupRatio"] = selected.dedup_ratio
            if selected.compress_ratio is not None:
                merged_payload["compressRatio"] = selected.compress_ratio
            gfs_periods = selected.raw_payload.get("gfsPeriods")
            if isinstance(gfs_periods, list):
                merged_payload["gfsPeriods"] = list(gfs_periods)
            if selected.backup_file_id and not merged_payload.get("backupFileId"):
                merged_payload["backupFileId"] = selected.backup_file_id

            merged_records.append(
                replace(
                    record,
                    raw_payload=merged_payload,
                    restore_point_size_bytes=selected.data_size_bytes or record.restore_point_size_bytes,
                )
            )
        return merged_records

    @staticmethod
    def _select_best_backup_file_record(
        *,
        record: VeeamMachineBackupRecord,
        candidates: list[VeeamBackupFileRecord],
    ) -> VeeamBackupFileRecord | None:
        if not candidates:
            return None

        filtered_candidates = candidates
        if record.backup_file_id:
            exact_matches = [candidate for candidate in candidates if candidate.backup_file_id == record.backup_file_id]
            if exact_matches:
                filtered_candidates = exact_matches

        if record.backup_at is not None:
            candidates_with_time = [candidate for candidate in filtered_candidates if candidate.backup_at is not None]
            if candidates_with_time:
                return min(
                    candidates_with_time,
                    key=lambda candidate: (
                        abs((candidate.backup_at - record.backup_at).total_seconds()),
                        0 if candidate.backup_file_id == record.backup_file_id else 1,
                        candidate.backup_file_id or "",
                    ),
                )

        return sorted(
            filtered_candidates,
            key=lambda candidate: (
                0 if candidate.backup_file_id == record.backup_file_id else 1,
                candidate.backup_file_id or "",
            ),
        )[0]

    @staticmethod
    def _extract_backup_metric_int(payload: object, keys: tuple[str, ...]) -> int | None:
        if not isinstance(payload, dict):
            return None
        for key in keys:
            value = payload.get(key)
            if value is None or value == "":
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _raise_restore_points_all_timeout(
        *,
        restore_points_result: VeeamMachineBackupCollection,
        match_result: VeeamBackupObjectMatchResult,
    ) -> None:
        raise VeeamRestorePointsFetchError(
            "Veeam restorePoints 全部请求超时，未获取到任何恢复点",
            matched_backup_objects_total=int(
                getattr(restore_points_result, "restore_points_backup_objects_total", 0)
                or getattr(match_result, "backups_matched_total", 0)
            ),
            completed_backup_objects_total=0,
            failed_backup_object_id=(
                getattr(restore_points_result, "timed_out_backup_ids_sample", [None])[0]
                if getattr(restore_points_result, "timed_out_backup_ids_sample", None)
                else None
            ),
            failed_machine_name=(
                getattr(restore_points_result, "timed_out_machine_names_sample", [None])[0]
                if getattr(restore_points_result, "timed_out_machine_names_sample", None)
                else None
            ),
            failed_url="",
        )

    @staticmethod
    def _validate_records_to_write(records: list[VeeamMachineBackupRecord]) -> None:
        for record in records:
            restore_point_count = int(record.restore_point_count or 0)
            if restore_point_count <= 0:
                continue
            raw_payload = record.raw_payload if isinstance(record.raw_payload, dict) else {}
            restore_point_times = raw_payload.get("restore_point_times")
            normalized_times = (
                [str(item).strip() for item in restore_point_times if isinstance(item, str) and item.strip()]
                if isinstance(restore_point_times, list)
                else []
            )
            if not normalized_times:
                raise ValidationError("Veeam 快照缺少恢复点时间，请重新执行一次 Veeam 同步")
