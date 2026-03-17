from __future__ import annotations

import pytest


@pytest.mark.unit
def test_web_email_alert_settings_page_renders(auth_client) -> None:
    response = auth_client.get("/alerts/email-settings")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "邮件告警配置" in html
    assert "/api/v1/alerts/email-settings" in html
