from __future__ import annotations

import pytest


@pytest.mark.unit
def test_web_system_settings_page_renders_aggregated_sections(auth_client) -> None:
    response = auth_client.get("/admin/system-settings")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "系统设置" in html
    assert "邮件设置" in html
    assert "JumpServer 数据源设置" in html
    assert "Veeam 数据源设置" in html
    assert 'data-system-settings-nav="true"' in html
    assert 'href="#system-settings-email-alerts"' in html
    assert 'href="#system-settings-jumpserver"' in html
    assert 'href="#system-settings-veeam"' in html
    assert 'id="system-settings-email-alerts"' in html
    assert 'id="system-settings-jumpserver"' in html
    assert 'id="system-settings-veeam"' in html
    assert 'id="email-alert-settings-page"' in html
    assert 'id="jumpserver-source-page"' in html
    assert 'id="veeam-source-page"' in html
    assert "/api/v1/alerts/email-settings" in html
    assert "/api/v1/integrations/jumpserver/source" in html
    assert "/api/v1/integrations/veeam/source" in html
    assert "发送测试邮件" in html
    assert "同步 JumpServer 资源" in html
    assert "同步 Veeam 备份" in html
