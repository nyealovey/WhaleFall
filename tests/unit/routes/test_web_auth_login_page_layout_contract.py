"""Web 登录页面布局契约测试.

目标:
- 登录页保持简洁：不展示平台介绍/营销信息框。
- 登录页背景不使用渐变或大色块，避免干扰表单输入。
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_web_auth_login_page_does_not_render_marketing_hero(client) -> None:
    response = client.get("/auth/login")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert "login-hero" not in html
    assert "统一的数据库运维控制台" not in html


@pytest.mark.unit
def test_web_auth_login_page_css_does_not_use_gradient_background() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    css_path = repo_root / "app/static/css/pages/auth/login.css"

    css = css_path.read_text(encoding="utf-8")
    assert "radial-gradient(" not in css
    assert "linear-gradient(" not in css
