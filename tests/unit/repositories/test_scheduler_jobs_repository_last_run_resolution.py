from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app import create_app, db
from app.repositories.scheduler_jobs_repository import SchedulerJobsRepository
from app.settings import Settings


@pytest.fixture(scope="function")
def app(monkeypatch):
    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True
    return app


def _ensure_task_run_table(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["task_runs"],
            ],
        )


@pytest.mark.unit
def test_lookup_job_last_run_returns_none_when_no_task_runs(app) -> None:
    _ensure_task_run_table(app)
    with app.app_context():
        assert SchedulerJobsRepository.lookup_job_last_run(job_id="calculate_account_classification") is None


@pytest.mark.unit
def test_lookup_job_last_run_returns_latest_started_at(app) -> None:
    _ensure_task_run_table(app)

    from app.models.task_run import TaskRun

    older = datetime(2026, 1, 22, 2, 0, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 1, 22, 3, 0, 0, tzinfo=timezone.utc)

    with app.app_context():
        run_old = TaskRun()
        run_old.run_id = "run-old"
        run_old.task_key = "calculate_account_classification"
        run_old.task_name = "统计账户分类"
        run_old.task_category = "classification"
        run_old.trigger_source = "scheduled"
        run_old.status = "completed"
        run_old.started_at = older
        run_old.completed_at = older
        db.session.add(run_old)

        run_new = TaskRun()
        run_new.run_id = "run-new"
        run_new.task_key = "calculate_account_classification"
        run_new.task_name = "统计账户分类"
        run_new.task_category = "classification"
        run_new.trigger_source = "scheduled"
        run_new.status = "completed"
        run_new.started_at = newer
        run_new.completed_at = newer
        db.session.add(run_new)

        run_other = TaskRun()
        run_other.run_id = "run-other"
        run_other.task_key = "sync_accounts"
        run_other.task_name = "账户同步"
        run_other.task_category = "account"
        run_other.trigger_source = "scheduled"
        run_other.status = "completed"
        run_other.started_at = newer
        run_other.completed_at = newer
        db.session.add(run_other)
        db.session.commit()

        assert SchedulerJobsRepository.lookup_job_last_run(job_id="calculate_account_classification") == newer.isoformat()
