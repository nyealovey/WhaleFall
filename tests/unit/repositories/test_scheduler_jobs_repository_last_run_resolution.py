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
        db.session.add(
            TaskRun(
                run_id="run-old",
                task_key="calculate_account_classification",
                task_name="统计账户分类",
                task_category="classification",
                trigger_source="scheduled",
                status="completed",
                started_at=older,
                completed_at=older,
            ),
        )
        db.session.add(
            TaskRun(
                run_id="run-new",
                task_key="calculate_account_classification",
                task_name="统计账户分类",
                task_category="classification",
                trigger_source="scheduled",
                status="completed",
                started_at=newer,
                completed_at=newer,
            ),
        )
        db.session.add(
            TaskRun(
                run_id="run-other",
                task_key="sync_accounts",
                task_name="账户同步",
                task_category="account",
                trigger_source="scheduled",
                status="completed",
                started_at=newer,
                completed_at=newer,
            ),
        )
        db.session.commit()

        assert SchedulerJobsRepository.lookup_job_last_run(job_id="calculate_account_classification") == newer.isoformat()
