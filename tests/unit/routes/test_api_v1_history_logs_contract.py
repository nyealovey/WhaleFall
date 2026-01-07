import pytest

from app.services.history_logs.history_logs_extras_service import HistoryLogsExtrasService
from app.services.history_logs.history_logs_list_service import HistoryLogsListService
from app.types.history_logs import HistoryLogListItem, HistoryLogStatistics, HistoryLogTopModule
from app.types.listing import PaginatedResult


@pytest.mark.unit
def test_api_v1_history_logs_requires_auth(client) -> None:
    response = client.get("/api/v1/logs")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.get("/api/v1/logs/statistics")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_history_logs_endpoints_contract(auth_client, monkeypatch) -> None:
    def _dummy_list_logs(self, filters):  # noqa: ANN001
        del self, filters
        return PaginatedResult(
            items=[
                HistoryLogListItem(
                    id=1,
                    timestamp="2025-12-27T00:00:00+08:00",
                    timestamp_display="2025-12-27 00:00:00",
                    level="INFO",
                    module="unit-test",
                    message="hello",
                    traceback=None,
                    context={"event": "contract"},
                ),
            ],
            total=1,
            page=1,
            pages=1,
            limit=20,
        )

    def _dummy_list_modules(self):  # noqa: ANN001
        del self
        return ["unit-test"]

    def _dummy_get_statistics(self, *, hours):  # noqa: ANN001
        del self, hours
        return HistoryLogStatistics(
            total_logs=1,
            error_count=0,
            warning_count=0,
            info_count=1,
            debug_count=0,
            critical_count=0,
            level_distribution={"INFO": 1},
            top_modules=[HistoryLogTopModule(module="unit-test", count=1)],
            error_rate=0.0,
        )

    def _dummy_get_log_detail(self, log_id):  # noqa: ANN001
        del self, log_id
        return HistoryLogListItem(
            id=1,
            timestamp="2025-12-27T00:00:00+08:00",
            timestamp_display="2025-12-27 00:00:00",
            level="INFO",
            module="unit-test",
            message="hello",
            traceback=None,
            context={"event": "contract"},
        )

    monkeypatch.setattr(HistoryLogsListService, "list_logs", _dummy_list_logs)
    monkeypatch.setattr(HistoryLogsExtrasService, "list_modules", _dummy_list_modules)
    monkeypatch.setattr(HistoryLogsExtrasService, "get_statistics", _dummy_get_statistics)
    monkeypatch.setattr(HistoryLogsExtrasService, "get_log_detail", _dummy_get_log_detail)

    list_response = auth_client.get("/api/v1/logs")
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())
    assert "per_page" not in data
    assert "perPage" not in data

    search_response = auth_client.get("/api/v1/logs?search=hello")
    assert search_response.status_code == 200
    payload = search_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())
    assert "per_page" not in data
    assert "perPage" not in data

    modules_response = auth_client.get("/api/v1/logs/modules")
    assert modules_response.status_code == 200
    payload = modules_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert "modules" in data

    stats_response = auth_client.get("/api/v1/logs/statistics")
    assert stats_response.status_code == 200
    payload = stats_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"total_logs", "level_distribution", "top_modules"}.issubset(data.keys())

    detail_response = auth_client.get("/api/v1/logs/1")
    assert detail_response.status_code == 200
    payload = detail_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert "log" in data
