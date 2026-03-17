from __future__ import annotations

import pytest


@pytest.mark.unit
def test_web_email_alert_settings_page_renders(auth_client) -> None:
    response = auth_client.get("/alerts/email-settings")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "邮件告警配置" in html
    assert "发送设置" in html
    assert "规则设置" in html
    assert "告警控制台" not in html
    assert "规则矩阵" not in html
    assert "邮件投递控制台" not in html
    assert "SMTP 通道状态" not in html
    assert "当前收件人数" not in html
    assert "/api/v1/alerts/email-settings" in html
    assert "发送测试邮件" in html
    assert "/api/v1/alerts/email-settings/actions/send-test" in html
