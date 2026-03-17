from __future__ import annotations

import pytest

from app import db
import app.api.v1.namespaces.alerts as alerts_module


def _ensure_alert_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["email_alert_settings"],
                db.metadata.tables["email_alert_events"],
            ],
        )


def _get_csrf_token(client) -> str:
    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    return csrf_token


@pytest.mark.unit
def test_api_v1_alerts_requires_auth(client) -> None:
    csrf_token = _get_csrf_token(client)
    headers = {"X-CSRFToken": csrf_token}

    response = client.get("/api/v1/alerts/email-settings")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    update_response = client.put("/api/v1/alerts/email-settings", json={}, headers=headers)
    assert update_response.status_code == 401
    update_payload = update_response.get_json()
    assert isinstance(update_payload, dict)
    assert update_payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    test_response = client.post(
        "/api/v1/alerts/email-settings/actions/send-test",
        json={"recipients": ["ops@example.com"]},
        headers=headers,
    )
    assert test_response.status_code == 401
    test_payload = test_response.get_json()
    assert isinstance(test_payload, dict)
    assert test_payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_alerts_email_settings_contract(app, auth_client) -> None:
    _ensure_alert_tables(app)

    csrf_token = _get_csrf_token(auth_client)
    headers = {"X-CSRFToken": csrf_token}

    get_response = auth_client.get("/api/v1/alerts/email-settings")
    assert get_response.status_code == 200
    get_payload = get_response.get_json()
    assert isinstance(get_payload, dict)
    assert get_payload.get("success") is True
    get_data = get_payload.get("data")
    assert isinstance(get_data, dict)
    assert get_data.get("smtp_ready") is False
    assert get_data.get("from_address") in {"", None}
    settings = get_data.get("settings")
    assert isinstance(settings, dict)
    assert settings.get("global_enabled") is False
    assert settings.get("recipients") == []

    update_response = auth_client.put(
        "/api/v1/alerts/email-settings",
        json={
            "global_enabled": True,
            "recipients": ["ops@example.com", "dba@example.com"],
            "database_capacity_enabled": True,
            "database_capacity_percent_threshold": 30,
            "database_capacity_absolute_gb_threshold": 20,
            "account_sync_failure_enabled": True,
            "database_sync_failure_enabled": True,
            "privileged_account_enabled": True,
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    update_payload = update_response.get_json()
    assert isinstance(update_payload, dict)
    assert update_payload.get("success") is True
    update_data = update_payload.get("data")
    assert isinstance(update_data, dict)
    updated_settings = update_data.get("settings")
    assert isinstance(updated_settings, dict)
    assert updated_settings.get("global_enabled") is True
    assert updated_settings.get("recipients") == ["ops@example.com", "dba@example.com"]
    assert updated_settings.get("database_capacity_enabled") is True
    assert updated_settings.get("account_sync_failure_enabled") is True
    assert updated_settings.get("database_sync_failure_enabled") is True
    assert updated_settings.get("privileged_account_enabled") is True


@pytest.mark.unit
def test_api_v1_alerts_send_test_email_contract(app, auth_client, monkeypatch) -> None:
    _ensure_alert_tables(app)

    sent_payloads: list[dict[str, object]] = []

    class _StubEmailAlertSettingsService:
        def send_test_email(self, *, recipients: list[str]) -> dict[str, object]:
            sent_payloads.append({"recipients": list(recipients)})
            return {
                "sent": True,
                "recipient_count": len(recipients),
                "recipients": list(recipients),
            }

    monkeypatch.setattr(alerts_module, "EmailAlertSettingsService", _StubEmailAlertSettingsService)

    csrf_token = _get_csrf_token(auth_client)
    headers = {"X-CSRFToken": csrf_token}

    response = auth_client.post(
        "/api/v1/alerts/email-settings/actions/send-test",
        json={"recipients": ["ops@example.com", "dba@example.com"]},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("sent") is True
    assert data.get("recipient_count") == 2
    assert data.get("recipients") == ["ops@example.com", "dba@example.com"]
    assert sent_payloads == [{"recipients": ["ops@example.com", "dba@example.com"]}]
