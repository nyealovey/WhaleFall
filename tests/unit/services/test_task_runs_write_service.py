from __future__ import annotations

from datetime import UTC as datetime_utc, date, datetime

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
def test_task_runs_write_service_start_run_creates_task_run(app) -> None:
    try:
        from app.models.task_run import TaskRun
        from app.models.task_run_item import TaskRunItem
        from app.services.task_runs.task_runs_write_service import TaskRunsWriteService
    except ModuleNotFoundError as exc:
        pytest.fail(f"TaskRun 功能未实现: {exc}")

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
            created_by=1,
            summary_json={"hello": "world"},
            result_url="/accounts/ledgers",
        )
        assert isinstance(run_id, str)
        assert run_id

        db.session.commit()

        row = TaskRun.query.filter_by(run_id=run_id).first()
        assert row is not None
        assert row.task_key == "sync_accounts"
        assert row.task_name == "账户同步"
        assert row.task_category == "account"
        assert row.trigger_source == "manual"
        assert row.created_by == 1
        assert row.status == "running"
        assert row.summary_json == {"hello": "world"}
        assert row.result_url == "/accounts/ledgers"


@pytest.mark.unit
def test_task_runs_write_service_init_items_creates_pending_items_and_updates_total(app) -> None:
    try:
        from app.models.task_run import TaskRun
        from app.models.task_run_item import TaskRunItem
        from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
    except ModuleNotFoundError as exc:
        pytest.fail(f"TaskRun 功能未实现: {exc}")

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
            created_by=1,
            summary_json=None,
            result_url="/accounts/ledgers",
        )

        if not hasattr(service, "init_items"):
            pytest.fail("TaskRunsWriteService.init_items 未实现")

        service.init_items(
            run_id,
            items=[
                TaskRunItemInit(item_type="instance", item_key="1", item_name="inst-1", instance_id=1),
                TaskRunItemInit(item_type="instance", item_key="2", item_name="inst-2", instance_id=2),
            ],
        )
        db.session.commit()

        run = TaskRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        assert run.progress_total == 2

        items = TaskRunItem.query.filter_by(run_id=run_id).order_by(TaskRunItem.item_key.asc()).all()
        assert [item.item_key for item in items] == ["1", "2"]
        assert all(item.status == "pending" for item in items)


@pytest.mark.unit
def test_task_runs_write_service_finalize_run_aggregates_item_statuses(app) -> None:
    try:
        from app.models.task_run import TaskRun
        from app.models.task_run_item import TaskRunItem
        from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
    except ModuleNotFoundError as exc:
        pytest.fail(f"TaskRun 功能未实现: {exc}")

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
            created_by=1,
            summary_json=None,
            result_url="/accounts/ledgers",
        )
        service.init_items(
            run_id,
            items=[
                TaskRunItemInit(item_type="instance", item_key="1", item_name="inst-1", instance_id=1),
                TaskRunItemInit(item_type="instance", item_key="2", item_name="inst-2", instance_id=2),
            ],
        )

        for method_name in ("start_item", "complete_item", "fail_item", "finalize_run"):
            if not hasattr(service, method_name):
                pytest.fail(f"TaskRunsWriteService.{method_name} 未实现")

        service.start_item(run_id, item_type="instance", item_key="1")
        service.complete_item(
            run_id,
            item_type="instance",
            item_key="1",
            metrics_json={"duration_ms": 12},
        )

        service.start_item(run_id, item_type="instance", item_key="2")
        service.fail_item(
            run_id,
            item_type="instance",
            item_key="2",
            error_message="boom",
            details_json={"where": "unit-test"},
        )

        service.finalize_run(run_id)
        db.session.commit()

        run = TaskRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        assert run.progress_total == 2
        assert run.progress_completed == 1
        assert run.progress_failed == 1
        assert run.status == "failed"
        assert run.completed_at is not None

        items = TaskRunItem.query.filter_by(run_id=run_id).order_by(TaskRunItem.item_key.asc()).all()
        assert [item.status for item in items] == ["completed", "failed"]
        assert items[1].error_message == "boom"
        assert items[1].details_json == {"where": "unit-test"}


@pytest.mark.unit
def test_task_runs_write_service_cancel_run_marks_pending_running_items_cancelled(app) -> None:
    try:
        from app.models.task_run import TaskRun
        from app.models.task_run_item import TaskRunItem
        from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
    except ModuleNotFoundError as exc:
        pytest.fail(f"TaskRun 功能未实现: {exc}")

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
            created_by=1,
            summary_json=None,
            result_url="/accounts/ledgers",
        )
        service.init_items(
            run_id,
            items=[
                TaskRunItemInit(item_type="instance", item_key="1", item_name="inst-1", instance_id=1),
                TaskRunItemInit(item_type="instance", item_key="2", item_name="inst-2", instance_id=2),
            ],
        )

        if not hasattr(service, "cancel_run"):
            pytest.fail("TaskRunsWriteService.cancel_run 未实现")

        service.start_item(run_id, item_type="instance", item_key="1")
        service.complete_item(run_id, item_type="instance", item_key="1")
        service.start_item(run_id, item_type="instance", item_key="2")

        service.cancel_run(run_id)
        db.session.commit()

        run = TaskRun.query.filter_by(run_id=run_id).first()
        assert run is not None
        assert run.status == "cancelled"

        items = TaskRunItem.query.filter_by(run_id=run_id).order_by(TaskRunItem.item_key.asc()).all()
        assert [item.status for item in items] == ["completed", "cancelled"]


@pytest.mark.unit
def test_task_runs_write_service_serializes_date_values_in_json_columns(app) -> None:
    try:
        from app.models.task_run_item import TaskRunItem
        from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
    except ModuleNotFoundError as exc:
        pytest.fail(f"TaskRun 功能未实现: {exc}")

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_databases",
            task_name="数据库同步",
            task_category="capacity",
            trigger_source="manual",
            created_by=1,
            summary_json={"stat_date": date(2025, 1, 1)},
            result_url="/databases/ledgers",
        )
        service.init_items(
            run_id,
            items=[
                TaskRunItemInit(item_type="instance", item_key="1", item_name="inst-1", instance_id=1),
            ],
        )

        details = {
            "stat_date": date(2025, 1, 1),
            "window": {
                "started_at": datetime(2025, 1, 1, 12, 0, tzinfo=datetime_utc),
            },
            "days": [date(2025, 1, 1), date(2025, 1, 2)],
        }
        service.complete_item(
            run_id,
            item_type="instance",
            item_key="1",
            details_json=details,
        )

        # If JSON columns keep raw date objects, SQLAlchemy/psycopg JSON serialization will raise.
        db.session.commit()

        item = TaskRunItem.query.filter_by(run_id=run_id, item_type="instance", item_key="1").first()
        assert item is not None
        assert item.details_json["stat_date"] == "2025-01-01"
        assert item.details_json["window"]["started_at"].startswith("2025-01-01T12:00:00")
        assert item.details_json["days"] == ["2025-01-01", "2025-01-02"]
