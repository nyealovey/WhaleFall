import pytest


@pytest.mark.unit
def test_tags_list_contract(client) -> None:
    response = client.get("/tags/api/list")
    assert response.status_code == 404
