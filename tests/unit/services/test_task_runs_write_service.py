from __future__ import annotations

from datetime import UTC as datetime_utc, date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

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
        from app.schemas.task_run_summary import TaskRunSummaryFactory
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
            summary_json=None,
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
        assert row.summary_json == TaskRunSummaryFactory.base(task_key="sync_accounts")
        assert row.result_url == "/accounts/ledgers"


@pytest.mark.unit
def test_task_runs_write_service_start_run_rejects_raw_dict_summary(app) -> None:
    try:
        from app.services.task_runs.task_runs_write_service import TaskRunsWriteService
    except ModuleNotFoundError as exc:
        pytest.fail(f"TaskRun 功能未实现: {exc}")

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()

        with pytest.raises(ValidationError):
            service.start_run(
                task_key="sync_accounts",
                task_name="账户同步",
                task_category="account",
                trigger_source="manual",
                created_by=1,
                summary_json={"hello": "world"},
                result_url="/accounts/ledgers",
            )


@pytest.mark.unit
def test_task_runs_write_service_write_summary_rejects_raw_dict_summary(app) -> None:
    from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
        )

        with pytest.raises(ValidationError):
            service.write_summary(run_id, {"hello": "world"})


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
        from app.schemas.task_run_summary import TaskRunSummaryFactory
        from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
    except ModuleNotFoundError as exc:
        pytest.fail(f"TaskRun 功能未实现: {exc}")

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()

        summary_json = TaskRunSummaryFactory.base(task_key="sync_databases")
        summary_json["common"]["inputs"]["stat_date"] = date(2025, 1, 1)
        run_id = service.start_run(
            task_key="sync_databases",
            task_name="数据库同步",
            task_category="capacity",
            trigger_source="manual",
            created_by=1,
            summary_json=summary_json,
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


@pytest.mark.unit
def test_task_runs_write_service_resolve_or_start_run_reuses_existing_run(app) -> None:
    from app.models.task_run import TaskRun
    from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        existing_run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
        )
        db.session.commit()

        resolved_run_id = service.resolve_or_start_run(
            run_id=existing_run_id,
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="scheduled",
        )

        assert resolved_run_id == existing_run_id
        assert TaskRun.query.count() == 1


@pytest.mark.unit
def test_task_runs_write_service_resolve_or_start_run_creates_missing_run(app) -> None:
    from app.models.task_run import TaskRun
    from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.resolve_or_start_run(
            run_id=None,
            task_key="sync_databases",
            task_name="数据库同步",
            task_category="capacity",
            trigger_source="scheduled",
            result_url="/databases/ledgers",
        )
        db.session.commit()

        run = TaskRun.query.filter_by(run_id=run_id).one()
        assert run.task_key == "sync_databases"
        assert run.trigger_source == "scheduled"
        assert run.result_url == "/databases/ledgers"


@pytest.mark.unit
def test_task_runs_write_service_resolve_or_start_run_rejects_unknown_run(app) -> None:
    from app.core.exceptions import ValidationError as AppValidationError
    from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

    _ensure_task_run_tables(app)

    with app.app_context(), pytest.raises(AppValidationError):
        TaskRunsWriteService().resolve_or_start_run(
            run_id="missing-run",
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
        )


@pytest.mark.unit
def test_task_runs_write_service_mark_run_failed_fails_only_pending_running_items(app) -> None:
    from app.core.constants.status_types import TaskRunStatus
    from app.models.task_run import TaskRun
    from app.models.task_run_item import TaskRunItem
    from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
        )
        service.init_items(
            run_id,
            items=[
                TaskRunItemInit(item_type="instance", item_key="1"),
                TaskRunItemInit(item_type="instance", item_key="2"),
                TaskRunItemInit(item_type="instance", item_key="3"),
                TaskRunItemInit(item_type="instance", item_key="4"),
            ],
        )
        service.start_item(run_id, item_type="instance", item_key="1")
        service.complete_item(run_id, item_type="instance", item_key="2")
        service.cancel_item(run_id, item_type="instance", item_key="4")

        service.mark_run_failed(run_id, error_message="boom")
        db.session.commit()

        run = TaskRun.query.filter_by(run_id=run_id).one()
        assert run.status == TaskRunStatus.FAILED
        assert run.error_message == "boom"
        items = {
            item.item_key: item
            for item in TaskRunItem.query.filter_by(run_id=run_id).order_by(TaskRunItem.item_key.asc()).all()
        }
        assert items["1"].status == TaskRunStatus.FAILED
        assert items["1"].error_message == "boom"
        assert items["2"].status == TaskRunStatus.COMPLETED
        assert items["3"].status == TaskRunStatus.FAILED
        assert items["4"].status == TaskRunStatus.CANCELLED


@pytest.mark.unit
def test_task_runs_write_service_finalize_run_with_summary_supports_status_override(app) -> None:
    from app.core.constants.status_types import TaskRunStatus
    from app.models.task_run import TaskRun
    from app.schemas.task_run_summary import TaskRunSummaryFactory
    from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
        )
        service.init_items(
            run_id,
            items=[
                TaskRunItemInit(item_type="instance", item_key="1"),
                TaskRunItemInit(item_type="instance", item_key="2"),
            ],
        )
        service.complete_item(run_id, item_type="instance", item_key="1")
        service.fail_item(run_id, item_type="instance", item_key="2", error_message="partial")
        summary = TaskRunSummaryFactory.base(task_key="sync_accounts", flags={"skipped": False})

        service.finalize_run_with_summary(
            run_id,
            summary_json=summary,
            status_override=TaskRunStatus.COMPLETED_WITH_ERRORS,
        )
        db.session.commit()

        run = TaskRun.query.filter_by(run_id=run_id).one()
        assert run.summary_json == summary
        assert run.status == TaskRunStatus.COMPLETED_WITH_ERRORS
        assert run.progress_completed == 1
        assert run.progress_failed == 1


@pytest.mark.unit
def test_task_runs_write_service_write_summary_skips_cancelled_run(app) -> None:
    from app.models.task_run import TaskRun
    from app.schemas.task_run_summary import TaskRunSummaryFactory
    from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

    _ensure_task_run_tables(app)

    with app.app_context():
        service = TaskRunsWriteService()
        run_id = service.start_run(
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
        )
        original = TaskRunSummaryFactory.base(task_key="sync_accounts")
        service.cancel_run(run_id)
        replacement = TaskRunSummaryFactory.base(task_key="sync_accounts", flags={"skipped": True})

        assert service.write_summary(run_id, replacement) is False
        db.session.commit()

        run = TaskRun.query.filter_by(run_id=run_id).one()
        assert run.summary_json == original


@pytest.mark.unit
def test_task_files_delegate_pending_running_failure_sweep_to_write_service() -> None:
    root = Path(__file__).resolve().parents[3]
    task_paths = [
        "app/tasks/accounts_sync_tasks.py",
        "app/tasks/capacity_collection_tasks.py",
        "app/tasks/capacity_aggregation_tasks.py",
        "app/tasks/capacity_current_aggregation_tasks.py",
        "app/tasks/account_classification_daily_tasks.py",
        "app/tasks/account_classification_auto_tasks.py",
        "app/tasks/cluster_status_sync_tasks.py",
    ]

    offenders = [
        path
        for path in task_paths
        if "for item in TaskRunItem.query.filter_by(run_id" in (root / path).read_text(encoding="utf-8")
    ]

    assert offenders == []
