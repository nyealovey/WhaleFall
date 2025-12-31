import pytest


@pytest.mark.unit
def test_legacy_api_endpoints_return_gone(client) -> None:
    response = client.get("/auth/api/csrf-token")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"
