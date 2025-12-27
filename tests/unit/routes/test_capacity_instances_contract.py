import pytest


@pytest.mark.unit
def test_capacity_instances_contract(client) -> None:
    response = client.get(
        "/capacity/api/instances?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
    )
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"

    summary_response = client.get(
        "/capacity/api/instances/summary?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
    )
    assert summary_response.status_code == 410
    summary_payload = summary_response.get_json()
    assert isinstance(summary_payload, dict)
    assert summary_payload.get("message_code") == "API_GONE"
