import pytest

from app.services.capacity.current_aggregation_service import CurrentAggregationService


@pytest.mark.unit
def test_api_v1_capacity_current_aggregation_requires_auth(client) -> None:
    csrf_response = client.get("/auth/api/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = client.post(
        "/api/v1/capacity/aggregations/current",
        json={"period_type": "daily", "scope": "all"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_capacity_current_aggregation_contract(auth_client, monkeypatch) -> None:
    def _dummy_aggregate_current(self, request):  # noqa: ANN001
        del self, request
        return {
            "status": "completed",
            "message": "ok",
            "period_type": "daily",
            "period_start": "2025-01-01",
            "period_end": "2025-01-01",
            "scope": "all",
            "requested_period_type": "daily",
            "effective_period_type": "daily",
            "database_summary": {},
            "instance_summary": {},
            "session": {},
        }

    monkeypatch.setattr(CurrentAggregationService, "aggregate_current", _dummy_aggregate_current)

    csrf_response = auth_client.get("/auth/api/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        "/api/v1/capacity/aggregations/current",
        json={"period_type": "daily", "scope": "all"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    result = data.get("result")
    assert isinstance(result, dict)
    assert {
        "status",
        "message",
        "period_type",
        "period_start",
        "period_end",
        "scope",
        "requested_period_type",
        "effective_period_type",
        "database_summary",
        "instance_summary",
        "session",
    }.issubset(result.keys())

