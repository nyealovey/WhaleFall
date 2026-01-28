import pytest


@pytest.mark.unit
def test_api_v1_task_runs_requires_auth(client) -> None:
    response = client.get("/api/v1/task-runs")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    cancel_response = client.post("/api/v1/task-runs/r-1/actions/cancel", json={}, headers=headers)
    assert cancel_response.status_code == 401
    payload = cancel_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_task_runs_endpoints_contract(auth_client, monkeypatch) -> None:
    from app.core.types.listing import PaginatedResult
    from app.core.types.task_runs import TaskRunDetailResult, TaskRunErrorLogsResult, TaskRunItemItem, TaskRunListItem
    from app.services.task_runs.task_runs_read_service import TaskRunsReadService
    from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

    def _dummy_list_runs(self, filters):
        del self, filters
        return PaginatedResult(
            items=[
                TaskRunListItem(
                    id=1,
                    run_id="r-1",
                    task_key="sync_accounts",
                    task_name="账户同步",
                    task_category="account",
                    trigger_source="manual",
                    status="running",
                    started_at="2026-01-20T00:00:00+08:00",
                    completed_at=None,
                    progress_total=2,
                    progress_completed=0,
                    progress_failed=0,
                    created_by=1,
                    summary_json={"hello": "world"},
                    result_url="/accounts/ledgers",
                    error_message=None,
                    created_at="2026-01-20T00:00:00+08:00",
                    updated_at="2026-01-20T00:00:00+08:00",
                ),
            ],
            total=1,
            page=1,
            pages=1,
            limit=20,
        )

    def _dummy_detail(self, run_id: str):
        del self
        run = TaskRunListItem(
            id=1,
            run_id=run_id,
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
            status="running",
            started_at="2026-01-20T00:00:00+08:00",
            completed_at=None,
            progress_total=2,
            progress_completed=0,
            progress_failed=0,
            created_by=1,
            summary_json={"hello": "world"},
            result_url="/accounts/ledgers",
            error_message=None,
            created_at="2026-01-20T00:00:00+08:00",
            updated_at="2026-01-20T00:00:00+08:00",
        )
        item = TaskRunItemItem(
            id=1,
            run_id=run_id,
            item_type="instance",
            item_key="1",
            item_name="inst-1",
            instance_id=1,
            status="running",
            started_at="2026-01-20T00:00:00+08:00",
            completed_at=None,
            metrics_json={},
            details_json={},
            error_message=None,
            created_at="2026-01-20T00:00:00+08:00",
            updated_at="2026-01-20T00:00:00+08:00",
        )
        return TaskRunDetailResult(run=run, items=[item])

    def _dummy_errors(self, run_id: str):
        del self
        run = TaskRunListItem(
            id=1,
            run_id=run_id,
            task_key="sync_accounts",
            task_name="账户同步",
            task_category="account",
            trigger_source="manual",
            status="failed",
            started_at="2026-01-20T00:00:00+08:00",
            completed_at="2026-01-20T00:01:00+08:00",
            progress_total=2,
            progress_completed=1,
            progress_failed=1,
            created_by=1,
            summary_json={},
            result_url="/accounts/ledgers",
            error_message=None,
            created_at="2026-01-20T00:00:00+08:00",
            updated_at="2026-01-20T00:01:00+08:00",
        )
        item = TaskRunItemItem(
            id=2,
            run_id=run_id,
            item_type="instance",
            item_key="2",
            item_name="inst-2",
            instance_id=2,
            status="failed",
            started_at="2026-01-20T00:00:30+08:00",
            completed_at="2026-01-20T00:01:00+08:00",
            metrics_json={},
            details_json={"where": "unit-test"},
            error_message="boom",
            created_at="2026-01-20T00:00:30+08:00",
            updated_at="2026-01-20T00:01:00+08:00",
        )
        return TaskRunErrorLogsResult(run=run, items=[item], error_count=1)

    monkeypatch.setattr(TaskRunsReadService, "list_runs", _dummy_list_runs)
    monkeypatch.setattr(TaskRunsReadService, "get_run_detail", _dummy_detail)
    monkeypatch.setattr(TaskRunsReadService, "get_run_error_logs", _dummy_errors)
    monkeypatch.setattr(TaskRunsWriteService, "cancel_run", lambda _self, run_id: True)
    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    list_response = auth_client.get("/api/v1/task-runs")
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages"}.issubset(data.keys())
    assert isinstance(data.get("items"), list)
    assert len(data["items"]) == 1
    assert data["items"][0].get("run_id") == "r-1"

    detail_response = auth_client.get("/api/v1/task-runs/r-1")
    assert detail_response.status_code == 200
    payload = detail_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("data", {}).get("run", {}).get("run_id") == "r-1"

    errors_response = auth_client.get("/api/v1/task-runs/r-1/error-logs")
    assert errors_response.status_code == 200
    payload = errors_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("data", {}).get("error_count") == 1

    cancel_response = auth_client.post("/api/v1/task-runs/r-1/actions/cancel", json={}, headers=headers)
    assert cancel_response.status_code == 200
    payload = cancel_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
