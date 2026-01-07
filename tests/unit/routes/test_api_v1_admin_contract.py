import pytest


@pytest.mark.unit
def test_api_v1_admin_app_info_contract(client) -> None:
    response = client.get("/api/v1/admin/app-info")
    assert response.status_code == 404
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True
    assert payload.get("message_code") == "INVALID_REQUEST"
