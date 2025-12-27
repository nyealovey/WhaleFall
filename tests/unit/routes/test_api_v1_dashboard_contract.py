import pytest

from app import db


def _ensure_dashboard_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_classifications"],
                db.metadata.tables["classification_rules"],
                db.metadata.tables["account_classification_assignments"],
                db.metadata.tables["instance_databases"],
                db.metadata.tables["unified_logs"],
                db.metadata.tables["sync_sessions"],
            ],
        )


@pytest.mark.unit
def test_api_v1_dashboard_requires_auth(client) -> None:
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 401

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_dashboard_overview_contract(app, auth_client) -> None:
    _ensure_dashboard_tables(app)

    response = auth_client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"users", "instances", "accounts", "classified_accounts", "capacity", "databases"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_dashboard_status_contract(app, auth_client) -> None:
    _ensure_dashboard_tables(app)

    response = auth_client.get("/api/v1/dashboard/status")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"system", "services", "uptime"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_dashboard_activities_contract(app, auth_client) -> None:
    _ensure_dashboard_tables(app)

    response = auth_client.get("/api/v1/dashboard/activities")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    data = payload.get("data")
    assert isinstance(data, list)
    assert data == []


@pytest.mark.unit
def test_api_v1_dashboard_charts_logs_contract(app, auth_client) -> None:
    _ensure_dashboard_tables(app)

    response = auth_client.get("/api/v1/dashboard/charts?type=logs")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"log_trend", "log_levels"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_dashboard_charts_syncs_contract(app, auth_client) -> None:
    _ensure_dashboard_tables(app)

    response = auth_client.get("/api/v1/dashboard/charts?type=syncs")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False

    data = payload.get("data")
    assert isinstance(data, dict)
    assert "sync_trend" in data

    trend = data.get("sync_trend")
    assert isinstance(trend, list)
    assert len(trend) >= 1
    item = trend[0]
    assert isinstance(item, dict)
    assert {"date", "count"}.issubset(item.keys())


@pytest.mark.unit
def test_api_v1_dashboard_charts_unknown_type_returns_empty_dict(auth_client) -> None:
    response = auth_client.get("/api/v1/dashboard/charts?type=unknown")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    data = payload.get("data")
    assert data == {}
