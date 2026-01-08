import pytest


@pytest.mark.unit
def test_api_v1_csrf_token_is_not_accepted_from_json_body(auth_client) -> None:
    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        "/api/v1/auth/logout",
        json={"csrf_token": csrf_token},
    )
    assert response.status_code in {400, 403}
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True
