from __future__ import annotations

import pytest

from app import create_app, db
from app.settings import Settings


@pytest.fixture(scope="function")
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True
    return app


def _ensure_task_run_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
            ],
        )


@pytest.mark.unit
def test_task_runs_read_service_list_runs_returns_paginated_items(app) -> None:
    try:
        from app.core.types.task_runs import TaskRunsListFilters
        from app.services.task_runs.task_runs_read_service import TaskRunsReadService
        from app.services.task_runs.task_runs_write_service import TaskRunsWriteService
    except ModuleNotFoundError as exc:
        pytest.fail(f"TaskRun 功能未实现: {exc}")

    _ensure_task_run_tables(app)

    with app.app_context():
        write_service = TaskRunsWriteService()
        run_id = write_service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
            created_by=1,
            summary_json=None,
            result_url="/accounts/ledgers",
        )
        db.session.commit()

        filters = TaskRunsListFilters(
            task_key="",
            task_category="",
            trigger_source="",
            status="",
            page=1,
            limit=20,
            sort_field="started_at",
            sort_order="desc",
        )

        result = TaskRunsReadService().list_runs(filters)
        assert result.total == 1
        assert result.page == 1
        assert result.pages == 1
        assert len(result.items) == 1
        assert result.items[0].run_id == run_id
