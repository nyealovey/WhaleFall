import pytest


@pytest.mark.unit
def test_api_v1_admin_app_info_contract(client) -> None:
    response = client.get("/api/v1/admin/app-info")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"app_name", "app_version"}.issubset(data.keys())
