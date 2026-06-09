from __future__ import annotations

import pytest

from app import create_app, db
from app.models.task_run import TaskRun
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService
from app.services.veeam.run_summary_writer import VeeamRunSummaryWriter


@pytest.mark.unit
def test_veeam_run_summary_writer_appends_source_results_to_existing_summary() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
            ],
        )
        run_id = TaskRunsWriteService().start_run(
            task_key="sync_veeam_backups",
            task_name="Veeam 备份同步",
            task_category="other",
            trigger_source="manual",
            summary_json=None,
        )
        TaskRunsWriteService().finalize_run_with_summary(
            run_id,
            summary_json=VeeamRunSummaryWriter.build_backups_summary(
                inputs={"credential_id": 21},
                received_total=3,
                snapshots_written_total=1,
                skipped_invalid=0,
            ),
            clear_error=True,
        )
        db.session.commit()

        writer = VeeamRunSummaryWriter()
        writer.append_sources_to_run_summary(
            run_id=run_id,
            sources=[
                writer.build_source_summary(
                    source_binding_id=11,
                    source_name="生产 Veeam",
                    status="completed",
                    snapshots_written_total=1,
                    error_message=None,
                )
            ],
            partial_success=True,
        )

        run = TaskRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        assert run.summary_json["ext"]["type"] == "sync_veeam_backups"
        assert run.summary_json["ext"]["data"]["backups"]["received_total"] == 3
        assert run.summary_json["ext"]["data"]["partial_success"] is True
        assert run.summary_json["ext"]["data"]["sources"] == [
            {
                "source_binding_id": 11,
                "source_name": "生产 Veeam",
                "status": "completed",
                "snapshots_written_total": 1,
                "error_message": None,
            }
        ]


@pytest.mark.unit
def test_veeam_run_summary_writer_finalizes_multi_source_partial_success() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
            ],
        )
        run_id = TaskRunsWriteService().start_run(
            task_key="sync_veeam_backups",
            task_name="Veeam 备份同步",
            task_category="other",
            trigger_source="manual",
            summary_json=None,
        )
        db.session.commit()

        writer = VeeamRunSummaryWriter()
        writer.write_multi_source_run_result(
            run_id=run_id,
            sources=[
                writer.build_source_summary(
                    source_binding_id=11,
                    source_name="生产 Veeam",
                    status="completed",
                    snapshots_written_total=2,
                    error_message=None,
                ),
                writer.build_source_summary(
                    source_binding_id=12,
                    source_name="容灾 Veeam",
                    status="failed",
                    snapshots_written_total=0,
                    error_message="token error",
                ),
            ],
            partial_success=True,
            snapshots_written_total=2,
            error_message=None,
        )

        run = TaskRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        assert run.status == "completed"
        assert run.error_message is None
        assert run.summary_json["ext"]["data"]["backups"]["snapshots_written_total"] == 2
        assert run.summary_json["ext"]["data"]["partial_success"] is True
        assert [source["status"] for source in run.summary_json["ext"]["data"]["sources"]] == ["completed", "failed"]
