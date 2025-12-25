import pytest

from app import db


@pytest.mark.unit
def test_dashboard_charts_logs_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["unified_logs"],
            ],
        )

    response = auth_client.get("/dashboard/api/charts?type=logs")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False
    assert "message" in payload
    assert "timestamp" in payload

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"log_trend", "log_levels"}.issubset(data.keys())

    trend = data.get("log_trend")
    assert isinstance(trend, list)
    if trend:
        item = trend[0]
        assert isinstance(item, dict)
        assert {"date", "error_count", "warning_count"}.issubset(item.keys())

    levels = data.get("log_levels")
    assert isinstance(levels, list)


@pytest.mark.unit
def test_dashboard_charts_syncs_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["sync_sessions"],
            ],
        )

    response = auth_client.get("/dashboard/api/charts?type=syncs")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False
    assert "message" in payload
    assert "timestamp" in payload

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
def test_dashboard_charts_unknown_type_returns_empty_dict(auth_client) -> None:
    response = auth_client.get("/dashboard/api/charts?type=unknown")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    data = payload.get("data")
    assert data == {}

