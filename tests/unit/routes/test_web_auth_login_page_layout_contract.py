"""Web 登录页面布局契约测试.

目标:
- 登录页保持简洁：不展示平台介绍/营销信息框。
- 登录页背景不使用渐变或大色块，避免干扰表单输入。
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_web_auth_login_page_does_not_render_marketing_hero(client) -> None:
    response = client.get("/auth/login")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "login-hero" not in html
    assert "统一的数据库运维控制台" not in html
