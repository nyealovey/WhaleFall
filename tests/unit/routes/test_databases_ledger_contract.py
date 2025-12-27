import pytest


@pytest.mark.unit
def test_databases_ledger_contract(client) -> None:
    response = client.get("/databases/api/ledgers")
    assert response.status_code == 410
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "API_GONE"
