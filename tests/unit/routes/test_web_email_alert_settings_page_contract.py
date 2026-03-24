from __future__ import annotations

import pytest


@pytest.mark.unit
def test_web_email_alert_settings_page_route_removed(auth_client) -> None:
    response = auth_client.get("/alerts/email-settings")

    assert response.status_code == 404
