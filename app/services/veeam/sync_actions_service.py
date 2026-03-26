"""Veeam 备份同步动作服务."""

from __future__ import annotations

import threading
from dataclasses import dataclass

from flask import current_app, has_app_context

from app import db
from app.core.exceptions import ValidationError
from app.infra.route_safety import log_with_context
from app.models.task_run import TaskRun
from app.repositories.instances_repository import InstancesRepository
from app.repositories.veeam_repository import VeeamRepository
from app.services.task_runs.task_run_summary_builders import build_sync_veeam_backups_summary
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.services.veeam.matching import build_instance_match_candidates, normalize_machine_name
from app.services.veeam.provider import HttpVeeamProvider, VeeamMachineBackupRecord, VeeamProvider
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
        instances_repository: InstancesRepository | None = None,
        provider: VeeamProvider | None = None,
    ) -> None:
        self._source_service = source_service or VeeamSourceService(provider=provider)
        self._veeam_repository = veeam_repository or VeeamRepository()
        self._instances_repository = instances_repository or InstancesRepository()
        self._provider = provider or HttpVeeamProvider()

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
        sync_context = {"created_by": created_by, "run_id": run_id}
        try:
            task_runs_service.start_item(run_id, item_type=_SYNC_ITEM_TYPE, item_key=_SYNC_ITEM_KEY)
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
            match_machine_names = self._build_all_match_candidates(match_domains=binding.match_domains)
            log_with_context(
                "info",
                "Veeam 候选机器池已构建",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "candidate_machine_count": len(match_machine_names),
                    "candidate_machine_sample": sorted(match_machine_names)[:20],
                },
                include_actor=False,
            )
            result = self._provider.list_machine_backups(
                server_host=str(binding.server_host or ""),
                server_port=int(binding.server_port),
                username=str(credential.username or ""),
                password=str(credential.get_plain_password() or ""),
                api_version=str(binding.api_version or ""),
                match_machine_names=match_machine_names,
                verify_ssl=bool(binding.verify_ssl),
            )
            log_with_context(
                "info",
                "Veeam 备份链匹配完成",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "backups_received_total": result.backups_received_total,
                    "backups_matched_total": result.backups_matched_total,
                    "backups_unmatched_total": result.backups_unmatched_total,
                    "backups_missing_machine_name": result.backups_missing_machine_name,
                    "backup_objects_received_total": result.backups_received_total,
                    "backup_objects_matched_total": result.backups_matched_total,
                    "backup_objects_unmatched_total": result.backups_unmatched_total,
                    "backup_objects_missing_machine_name": result.backups_missing_machine_name,
                    "matched_backup_ids_sample": result.matched_backup_ids_sample,
                    "unmatched_backup_ids_sample": result.unmatched_backup_ids_sample,
                    "unmatched_machine_names_sample": result.unmatched_machine_names_sample,
                    "missing_machine_name_backup_ids_sample": result.missing_machine_name_backup_ids_sample,
                    "missing_machine_name_backup_names_sample": result.missing_machine_name_backup_names_sample,
                    "restore_points_received_total": result.received_total,
                    "skipped_invalid": result.skipped_invalid,
                },
                include_actor=False,
            )
            if result.backups_matched_total <= 0:
                log_with_context(
                    "warning",
                    "Veeam 未命中任何备份链",
                    module="veeam",
                    action="sync_backups_background",
                    context=sync_context,
                    extra={
                        "candidate_machine_count": len(match_machine_names),
                        "candidate_machine_sample": sorted(match_machine_names)[:20],
                        "backups_received_total": result.backups_received_total,
                        "backups_missing_machine_name": result.backups_missing_machine_name,
                        "backup_objects_received_total": result.backups_received_total,
                        "backup_objects_missing_machine_name": result.backups_missing_machine_name,
                        "unmatched_backup_ids_sample": result.unmatched_backup_ids_sample,
                        "unmatched_machine_names_sample": result.unmatched_machine_names_sample,
                        "missing_machine_name_backup_ids_sample": result.missing_machine_name_backup_ids_sample,
                        "missing_machine_name_backup_names_sample": result.missing_machine_name_backup_names_sample,
                    },
                    include_actor=False,
                )
            latest_records = self._select_latest_records(result.records)
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
            enrichment_targets = latest_records
            enriched_records = self._provider.enrich_machine_backups(
                server_host=str(binding.server_host or ""),
                server_port=int(binding.server_port),
                username=str(credential.username or ""),
                password=str(credential.get_plain_password() or ""),
                api_version=str(binding.api_version or ""),
                records=enrichment_targets,
                verify_ssl=bool(binding.verify_ssl),
            ) if enrichment_targets else []
            log_with_context(
                "info",
                "Veeam 备份详情补全完成",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "enriched_machine_count": len(enriched_records),
                    "job_name_filled_count": sum(1 for record in enriched_records if record.job_name),
                    "restore_point_size_filled_count": sum(
                        1 for record in enriched_records if record.restore_point_size_bytes is not None
                    ),
                    "backup_chain_size_filled_count": sum(
                        1 for record in enriched_records if record.backup_chain_size_bytes is not None
                    ),
                    "restore_point_count_filled_count": sum(
                        1 for record in enriched_records if record.restore_point_count is not None
                    ),
                },
                include_actor=False,
            )
            records_to_write = self._merge_enriched_records(latest_records, enriched_records)
            snapshots_written_total = self._veeam_repository.replace_machine_backup_snapshots(
                records_to_write,
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
            log_with_context(
                "info",
                "Veeam 备份同步完成",
                module="veeam",
                action="sync_backups_background",
                context=sync_context,
                extra={
                    "candidate_machine_count": len(match_machine_names),
                    "backups_received_total": result.backups_received_total,
                    "backups_matched_total": result.backups_matched_total,
                    "backups_unmatched_total": result.backups_unmatched_total,
                    "backups_missing_machine_name": result.backups_missing_machine_name,
                    "backup_objects_received_total": result.backups_received_total,
                    "backup_objects_matched_total": result.backups_matched_total,
                    "backup_objects_unmatched_total": result.backups_unmatched_total,
                    "backup_objects_missing_machine_name": result.backups_missing_machine_name,
                    "missing_machine_name_backup_ids_sample": result.missing_machine_name_backup_ids_sample,
                    "restore_points_received_total": result.received_total,
                    "latest_machine_count": len(latest_records),
                    "enriched_machine_count": len(enriched_records),
                    "snapshots_written_total": snapshots_written_total,
                    "skipped_invalid": result.skipped_invalid,
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
                context=sync_context,
                extra={"error_type": exc.__class__.__name__, "error_message": str(exc), "stage": "sync_backups"},
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

    def _build_all_match_candidates(self, *, match_domains: object) -> set[str]:
        domains = match_domains if isinstance(match_domains, list) else []
        instances = self._instances_repository.list_existing_instances()
        matched_machine_names: set[str] = set()
        for instance in instances:
            matched_machine_names.update(
                build_instance_match_candidates(getattr(instance, "name", None), domains)
            )
        return matched_machine_names

    @staticmethod
    def _select_latest_records(records: list[VeeamMachineBackupRecord]) -> list[VeeamMachineBackupRecord]:
        latest_by_machine: dict[str, VeeamMachineBackupRecord] = {}
        for record in records:
            normalized_machine_name = normalize_machine_name(record.machine_name)
            if not normalized_machine_name:
                continue
            current = latest_by_machine.get(normalized_machine_name)
            if current is None or record.backup_at > current.backup_at:
                latest_by_machine[normalized_machine_name] = record
        return list(latest_by_machine.values())

    @staticmethod
    def _merge_enriched_records(
        base_records: list[VeeamMachineBackupRecord],
        enriched_records: list[VeeamMachineBackupRecord],
    ) -> list[VeeamMachineBackupRecord]:
        enriched_map = {
            (normalize_machine_name(record.machine_name), record.source_record_id): record
            for record in enriched_records
        }
        merged: list[VeeamMachineBackupRecord] = []
        for record in base_records:
            key = (normalize_machine_name(record.machine_name), record.source_record_id)
            merged.append(enriched_map.get(key, record))
        return merged
