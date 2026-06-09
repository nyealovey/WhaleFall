"""Veeam 同步 TaskRun summary 写入."""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.task_run import TaskRun
from app.services.task_runs.task_run_summary_builders import (
    build_sync_veeam_backups_summary,
    merge_sync_veeam_sources_summary,
)
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService


class VeeamRunSummaryWriter:
    """集中维护 Veeam 同步 run summary 的写入策略."""

    @staticmethod
    def build_source_summary(
        *,
        source_binding_id: int,
        source_name: str,
        status: str,
        snapshots_written_total: int,
        error_message: str | None,
    ) -> dict[str, object]:
        return {
            "source_binding_id": int(source_binding_id),
            "source_name": str(source_name or ""),
            "status": status,
            "snapshots_written_total": snapshots_written_total,
            "error_message": error_message,
        }

    @staticmethod
    def build_backups_summary(
        *,
        inputs: dict[str, Any] | None,
        received_total: int,
        snapshots_written_total: int,
        skipped_invalid: int,
        timed_out_backup_objects_total: int = 0,
        backup_files_scanned_total: int = 0,
        backup_ids_total: int = 0,
        backup_ids_completed: int = 0,
        timed_out_backup_ids_total: int = 0,
        failed_backup_ids_total: int = 0,
        restore_points_expected_total: int = 0,
        restore_points_enriched_total: int = 0,
        restore_points_missing_metrics_total: int = 0,
        backup_ids_fully_covered_total: int = 0,
        backup_ids_partially_covered_total: int = 0,
        partial_success: bool = False,
        sources: list[dict[str, Any]] | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        return build_sync_veeam_backups_summary(
            task_key="sync_veeam_backups",
            inputs=inputs,
            received_total=received_total,
            snapshots_written_total=snapshots_written_total,
            skipped_invalid=skipped_invalid,
            timed_out_backup_objects_total=timed_out_backup_objects_total,
            backup_files_scanned_total=backup_files_scanned_total,
            backup_ids_total=backup_ids_total,
            backup_ids_completed=backup_ids_completed,
            timed_out_backup_ids_total=timed_out_backup_ids_total,
            failed_backup_ids_total=failed_backup_ids_total,
            restore_points_expected_total=restore_points_expected_total,
            restore_points_enriched_total=restore_points_enriched_total,
            restore_points_missing_metrics_total=restore_points_missing_metrics_total,
            backup_ids_fully_covered_total=backup_ids_fully_covered_total,
            backup_ids_partially_covered_total=backup_ids_partially_covered_total,
            partial_success=partial_success,
            sources=sources,
            error_message=error_message,
        )

    @staticmethod
    def append_sources_to_run_summary(
        *,
        run_id: str,
        sources: list[dict[str, object]],
        partial_success: bool,
    ) -> None:
        try:
            run = TaskRun.query.filter_by(run_id=run_id).first()
        except SQLAlchemyError:
            return
        if run is None:
            return
        summary = merge_sync_veeam_sources_summary(
            run.summary_json,
            sources=sources,
            partial_success=partial_success,
        )
        task_runs_service = TaskRunsWriteService()
        if task_runs_service.write_summary(run_id, summary):
            db.session.commit()

    @staticmethod
    def write_multi_source_run_result(
        *,
        run_id: str,
        sources: list[dict[str, object]],
        partial_success: bool,
        snapshots_written_total: int,
        error_message: str | None,
    ) -> None:
        task_runs_service = TaskRunsWriteService()
        task_runs_service.finalize_run_with_summary(
            run_id,
            summary_json=VeeamRunSummaryWriter.build_backups_summary(
                inputs={"source_binding_ids": [source["source_binding_id"] for source in sources]},
                received_total=0,
                snapshots_written_total=snapshots_written_total,
                skipped_invalid=0,
                sources=sources,
                partial_success=partial_success,
                error_message=error_message,
            ),
            error_message=error_message,
            status_override="completed" if partial_success else None,
            clear_error=partial_success,
        )
        db.session.commit()
