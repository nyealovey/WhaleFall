import pytest


@pytest.mark.unit
def test_api_v1_swagger_json_renders(client) -> None:
    response = client.get("/api/v1/swagger.json")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("swagger") == "2.0"
    assert "paths" in payload
