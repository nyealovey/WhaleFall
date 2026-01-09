"""Web 端首页跳转行为测试.

目标:
- 未登录访问 `/` 应跳转到登录页
- 已登录访问 `/` 应跳转到仪表盘
"""

import pytest


@pytest.mark.unit
def test_main_index_redirects_to_login_when_not_authenticated(client) -> None:
    """未登录访问首页应跳转到登录页."""
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


@pytest.mark.unit
def test_main_index_redirects_to_dashboard_when_authenticated(auth_client) -> None:
    """已登录访问首页应跳转到仪表盘."""
    response = auth_client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard/")

