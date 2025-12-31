import pytest


@pytest.mark.unit
def test_databases_ledger_contract(client) -> None:
    response = client.get("/databases/api/ledgers")
    assert response.status_code == 404
