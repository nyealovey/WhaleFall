import pytest

from app import db


@pytest.mark.unit
def test_api_v1_capacity_current_aggregation_requires_auth(client) -> None:
    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = client.post(
        "/api/v1/capacity/aggregations/current",
        json={"period_type": "daily", "scope": "all"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_capacity_current_aggregation_contract(app, auth_client, monkeypatch) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["task_runs"],
                db.metadata.tables["task_run_items"],
            ],
        )

    class _DummyThread:
        name = "dummy_capacity_aggregate_current_manual"

    import app.services.capacity.capacity_current_aggregation_actions_service as actions_module

    monkeypatch.setattr(actions_module, "_launch_background_aggregation", lambda **_kwargs: _DummyThread())

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)

    response = auth_client.post(
        "/api/v1/capacity/aggregations/current",
        json={"period_type": "daily", "scope": "all"},
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert isinstance(data.get("run_id"), str)
