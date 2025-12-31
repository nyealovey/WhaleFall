import pytest


@pytest.mark.unit
def test_legacy_api_endpoints_return_not_found(client) -> None:
    response = client.get("/auth/api/csrf-token")
    assert response.status_code == 404
