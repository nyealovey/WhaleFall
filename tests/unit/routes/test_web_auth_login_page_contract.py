"""Web 登录页面契约测试.

目标:
- “记住我”默认勾选（用户不操作即可获得 7 天登录态）
"""

from __future__ import annotations

import re

import pytest


@pytest.mark.unit
def test_web_auth_login_page_remember_checked_by_default(client) -> None:
    response = client.get("/auth/login")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert re.search(r'<input[^>]*id="remember"[^>]*checked', html, flags=re.IGNORECASE)
