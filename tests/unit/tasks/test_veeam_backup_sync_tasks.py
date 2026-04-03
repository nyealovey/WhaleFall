from __future__ import annotations

import pytest

import app.tasks.veeam_backup_sync_tasks as task_module
from app import create_app, db
from app.models.task_run import TaskRun
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.services.veeam.sync_actions_service import VeeamSyncPreparedRun


@pytest.mark.unit
def test_sync_veeam_backups_commits_prepared_run_before_sync_once(monkeypatch) -> None:
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

        class _StubBinding:
            credential_id = 21

        def _fake_create_app(*, init_scheduler_on_start: bool = False):
            _ = init_scheduler_on_start
            return app

        def _fake_get_binding_or_error(self):
            _ = self
            return _StubBinding()

        def _fake_prepare_background_sync(
            self,
            *,
            created_by: int | None,
            trigger_source: str = "manual",
            result_url: str = "/admin/system-settings#system-settings-veeam",
        ):
            _ = (self, trigger_source, result_url)
            task_runs_service = TaskRunsWriteService()
            run_id = task_runs_service.start_run(
                task_key="sync_veeam_backups",
                task_name="Veeam 备份同步",
                task_category="other",
                trigger_source="manual",
                created_by=created_by,
                summary_json=None,
                result_url="/history/sessions",
            )
            task_runs_service.init_items(
                run_id,
                items=[TaskRunItemInit(item_type="step", item_key="sync_backups", item_name="同步 Veeam 备份")],
            )
            return VeeamSyncPreparedRun(run_id=run_id, credential_id=21)

        observed: dict[str, object] = {}

        def _fake_sync_once(self, *, created_by: int | None, run_id: str, credential_id: int) -> None:
            _ = (self, created_by, credential_id)
            db.session.rollback()
            observed["run_id"] = run_id
            observed["run_exists_after_rollback"] = TaskRun.query.filter_by(run_id=run_id).first() is not None

        monkeypatch.setattr(task_module, "create_app", _fake_create_app)
        monkeypatch.setattr(
            task_module.VeeamSourceService, "get_binding_or_error", _fake_get_binding_or_error, raising=True
        )
        monkeypatch.setattr(
            task_module.VeeamSyncActionsService, "prepare_background_sync", _fake_prepare_background_sync, raising=True
        )
        monkeypatch.setattr(task_module.VeeamSyncActionsService, "_sync_once", _fake_sync_once, raising=True)

        task_module.sync_veeam_backups(manual_run=True, created_by=1)

        assert isinstance(observed.get("run_id"), str)
        assert observed["run_exists_after_rollback"] is True
