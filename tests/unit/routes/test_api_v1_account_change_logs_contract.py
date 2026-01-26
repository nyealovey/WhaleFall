import pytest

from app.core.types.account_change_logs import (
    AccountChangeLogListItem,
    AccountChangeLogStatistics,
)
from app.core.types.listing import PaginatedResult
from app.services.history_account_change_logs.history_account_change_logs_read_service import (
    HistoryAccountChangeLogsReadService,
)


@pytest.mark.unit
def test_api_v1_account_change_logs_requires_auth(client) -> None:
    response = client.get("/api/v1/account-change-logs")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.get("/api/v1/account-change-logs/statistics")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.get("/api/v1/account-change-logs/1")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_account_change_logs_endpoints_contract(auth_client, monkeypatch) -> None:
    def _dummy_list_logs(self, filters):
        del self, filters
        return PaginatedResult(
            items=[
                AccountChangeLogListItem(
                    id=1,
                    account_id=4453,
                    instance_id=100,
                    instance_name="CBRAIN",
                    db_type="oracle",
                    username="CBRAIN",
                    change_type="add",
                    status="success",
                    message="新增账户,赋予 5 项权限",
                    change_time="2025-12-31 08:13:25",
                    session_id="session_123",
                    privilege_diff_count=5,
                    other_diff_count=1,
                ),
            ],
            total=1,
            page=1,
            pages=1,
            limit=20,
        )

    def _dummy_get_statistics(self, *, hours):
        del self, hours
        return AccountChangeLogStatistics(
            total_changes=1,
            success_count=1,
            failed_count=0,
            affected_accounts=1,
        )

    def _dummy_get_log_detail(self, log_id):
        del self, log_id
        return {
            "log": {
                "id": 1,
                "change_type": "add",
                "change_time": "2025-12-31 08:13:25",
                "status": "success",
                "message": "新增账户,赋予 5 项权限",
                "privilege_diff": [],
                "other_diff": [],
                "session_id": "session_123",
            },
        }

    monkeypatch.setattr(HistoryAccountChangeLogsReadService, "list_logs", _dummy_list_logs)
    monkeypatch.setattr(HistoryAccountChangeLogsReadService, "get_statistics", _dummy_get_statistics)
    monkeypatch.setattr(HistoryAccountChangeLogsReadService, "get_log_detail", _dummy_get_log_detail)

    list_response = auth_client.get("/api/v1/account-change-logs")
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())
    assert "per_page" not in data
    assert "perPage" not in data

    search_response = auth_client.get("/api/v1/account-change-logs?search=CBRAIN")
    assert search_response.status_code == 200
    payload = search_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    stats_response = auth_client.get("/api/v1/account-change-logs/statistics")
    assert stats_response.status_code == 200
    payload = stats_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"total_changes", "success_count", "failed_count", "affected_accounts"}.issubset(data.keys())

    detail_response = auth_client.get("/api/v1/account-change-logs/1")
    assert detail_response.status_code == 200
    payload = detail_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert "log" in data
