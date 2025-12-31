import pytest


@pytest.mark.unit
def test_accounts_ledgers_contract(client) -> None:
    response = client.get("/accounts/api/ledgers")
    assert response.status_code == 404
