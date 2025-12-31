import pytest


@pytest.mark.unit
def test_users_list_contract(client) -> None:
    response = client.get("/users/api/users")
    assert response.status_code == 404
