import pytest


@pytest.mark.unit
def test_credentials_list_contract(client) -> None:
    response = client.get("/credentials/api/credentials")
    assert response.status_code == 404
