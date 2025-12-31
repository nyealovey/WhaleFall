import pytest

import app.scheduler as scheduler_module
from app.services.scheduler.scheduler_job_write_service import SchedulerJobWriteService
from app.services.scheduler.scheduler_jobs_read_service import SchedulerJobsReadService
from app.types.scheduler import SchedulerJobDetail, SchedulerJobListItem


@pytest.mark.unit
def test_api_v1_scheduler_requires_auth(client) -> None:
    response = client.get("/api/v1/scheduler/jobs")
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

    reload_response = client.post("/api/v1/scheduler/jobs/reload", json={}, headers=headers)
    assert reload_response.status_code == 401
    payload = reload_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_scheduler_endpoints_contract(auth_client, monkeypatch) -> None:
    class _DummyJob:
        id = "job-1"
        name = "job-1"

        @staticmethod
        def func(*args, **kwargs):  # noqa: ANN001
            del args, kwargs

        args = ()
        kwargs = {}

    class _DummyScheduler:
        running = True

        @staticmethod
        def get_jobs():  # noqa: ANN001
            return [_DummyJob()]

        @staticmethod
        def get_job(job_id: str):  # noqa: ANN001
            return _DummyJob() if job_id == "job-1" else None

        @staticmethod
        def pause_job(job_id: str) -> None:
            del job_id

        @staticmethod
        def resume_job(job_id: str) -> None:
            del job_id

        @staticmethod
        def remove_job(job_id: str) -> None:
            del job_id

    def _dummy_list_jobs(self):  # noqa: ANN001
        del self
        return [
            SchedulerJobListItem(
                id="job-1",
                name="job-1",
                description="job-1",
                next_run_time=None,
                last_run_time=None,
                trigger_type="cron",
                trigger_args={"minute": "*"},
                state="STATE_RUNNING",
                is_builtin=True,
                func="func",
                args=(),
                kwargs={},
            ),
        ]

    def _dummy_get_job(self, job_id: str):  # noqa: ANN001
        del self, job_id
        return SchedulerJobDetail(
            id="job-1",
            name="job-1",
            next_run_time=None,
            trigger="cron",
            func="func",
            args=(),
            kwargs={},
            misfire_grace_time=None,
            max_instances=None,
            coalesce=None,
        )

    monkeypatch.setattr(SchedulerJobsReadService, "list_jobs", _dummy_list_jobs)
    monkeypatch.setattr(SchedulerJobsReadService, "get_job", _dummy_get_job)
    monkeypatch.setattr(SchedulerJobWriteService, "load", lambda self, resource_id: object())
    monkeypatch.setattr(SchedulerJobWriteService, "upsert", lambda self, payload, resource=None: resource)

    monkeypatch.setattr(scheduler_module, "get_scheduler", lambda: _DummyScheduler())
    monkeypatch.setattr(scheduler_module, "_reload_all_jobs", lambda: None)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    list_response = auth_client.get("/api/v1/scheduler/jobs")
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, list)

    detail_response = auth_client.get("/api/v1/scheduler/jobs/job-1")
    assert detail_response.status_code == 200
    payload = detail_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("id") == "job-1"

    update_response = auth_client.put(
        "/api/v1/scheduler/jobs/job-1",
        json={"trigger_type": "cron", "cron_expression": "*/5 * * * *"},
        headers=headers,
    )
    assert update_response.status_code == 200
    payload = update_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    pause_response = auth_client.post("/api/v1/scheduler/jobs/job-1/pause", json={}, headers=headers)
    assert pause_response.status_code == 200
    payload = pause_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    resume_response = auth_client.post("/api/v1/scheduler/jobs/job-1/resume", json={}, headers=headers)
    assert resume_response.status_code == 200
    payload = resume_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    run_response = auth_client.post("/api/v1/scheduler/jobs/job-1/run", json={}, headers=headers)
    assert run_response.status_code == 200
    payload = run_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert "manual_job_id" in data

    reload_response = auth_client.post("/api/v1/scheduler/jobs/reload", json={}, headers=headers)
    assert reload_response.status_code == 200
    payload = reload_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
