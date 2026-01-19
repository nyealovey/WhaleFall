import pytest

from app.core.types.history_sessions import (
    SyncInstanceRecordItem,
    SyncSessionDetailItem,
    SyncSessionDetailResult,
    SyncSessionErrorLogsResult,
    SyncSessionItem,
)
from app.core.types.listing import PaginatedResult
from app.services.history_sessions.history_sessions_read_service import HistorySessionsReadService
from app.services.sync_session_service import sync_session_service


@pytest.mark.unit
def test_api_v1_history_sessions_requires_auth(client) -> None:
    response = client.get("/api/v1/sync-sessions")
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

    cancel_response = client.post("/api/v1/sync-sessions/s-1/actions/cancel", json={}, headers=headers)
    assert cancel_response.status_code == 401
    payload = cancel_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_history_sessions_endpoints_contract(auth_client, monkeypatch) -> None:
    def _dummy_list_sessions(self, filters):  # noqa: ANN001
        del self, filters
        return PaginatedResult(
            items=[
                SyncSessionItem(
                    id=1,
                    session_id="s-1",
                    sync_type="full",
                    sync_category="accounts",
                    status="running",
                    started_at="2025-12-27T00:00:00+08:00",
                    completed_at=None,
                    total_instances=1,
                    successful_instances=0,
                    failed_instances=0,
                    created_by=1,
                    created_at="2025-12-27T00:00:00+08:00",
                    updated_at="2025-12-27T00:00:00+08:00",
                ),
            ],
            total=1,
            page=1,
            pages=1,
            limit=20,
        )

    def _dummy_detail(self, session_id: str):  # noqa: ANN001
        del self
        record = SyncInstanceRecordItem(
            id=1,
            session_id=session_id,
            instance_id=1,
            instance_name="instance-1",
            sync_category="accounts",
            status="running",
            started_at="2025-12-27T00:00:00+08:00",
            completed_at=None,
            items_synced=0,
            items_created=0,
            items_updated=0,
            items_deleted=0,
            error_message=None,
            sync_details={},
            created_at="2025-12-27T00:00:00+08:00",
        )
        session = SyncSessionDetailItem(
            id=1,
            session_id=session_id,
            sync_type="full",
            sync_category="accounts",
            status="running",
            started_at="2025-12-27T00:00:00+08:00",
            completed_at=None,
            total_instances=1,
            successful_instances=0,
            failed_instances=0,
            created_by=1,
            created_at="2025-12-27T00:00:00+08:00",
            updated_at="2025-12-27T00:00:00+08:00",
            instance_records=[record],
            progress_percentage=0.0,
        )
        return SyncSessionDetailResult(session=session)

    def _dummy_errors(self, session_id: str):  # noqa: ANN001
        del self
        session = SyncSessionItem(
            id=1,
            session_id=session_id,
            sync_type="full",
            sync_category="accounts",
            status="running",
            started_at="2025-12-27T00:00:00+08:00",
            completed_at=None,
            total_instances=1,
            successful_instances=0,
            failed_instances=0,
            created_by=1,
            created_at="2025-12-27T00:00:00+08:00",
            updated_at="2025-12-27T00:00:00+08:00",
        )
        return SyncSessionErrorLogsResult(session=session, error_records=[], error_count=0)

    monkeypatch.setattr(HistorySessionsReadService, "list_sessions", _dummy_list_sessions)
    monkeypatch.setattr(HistorySessionsReadService, "get_session_detail", _dummy_detail)
    monkeypatch.setattr(HistorySessionsReadService, "get_session_error_logs", _dummy_errors)
    monkeypatch.setattr(sync_session_service, "cancel_session", lambda session_id: True)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    list_response = auth_client.get("/api/v1/sync-sessions")
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages"}.issubset(data.keys())

    detail_response = auth_client.get("/api/v1/sync-sessions/s-1")
    assert detail_response.status_code == 200
    payload = detail_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    errors_response = auth_client.get("/api/v1/sync-sessions/s-1/error-logs")
    assert errors_response.status_code == 200
    payload = errors_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    cancel_response = auth_client.post("/api/v1/sync-sessions/s-1/actions/cancel", json={}, headers=headers)
    assert cancel_response.status_code == 200
    payload = cancel_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
