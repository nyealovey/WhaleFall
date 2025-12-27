import pytest


@pytest.mark.unit
def test_credentials_list_contract(client) -> None:
    response = client.get("/credentials/api/credentials")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"
