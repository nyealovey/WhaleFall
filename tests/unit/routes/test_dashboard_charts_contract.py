import pytest


@pytest.mark.unit
def test_dashboard_charts_logs_contract(auth_client) -> None:
    response = auth_client.get("/dashboard/api/charts?type=logs")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"


@pytest.mark.unit
def test_dashboard_charts_syncs_contract(auth_client) -> None:
    response = auth_client.get("/dashboard/api/charts?type=syncs")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"


@pytest.mark.unit
def test_dashboard_charts_unknown_type_returns_empty_dict(auth_client) -> None:
    response = auth_client.get("/dashboard/api/charts?type=unknown")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"
