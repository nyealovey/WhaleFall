"""重定向目标安全校验工具的单元测试."""

import pytest

from app.utils.redirect_safety import is_safe_redirect_target, resolve_safe_redirect_target


@pytest.mark.unit
def test_is_safe_redirect_target_enforces_minimal_policy() -> None:
    """验证仅允许以 / 开头的站内路径."""
    cases: list[tuple[str, bool]] = [
        ("/dashboard", True),
        ("/auth/login?next=%2F", True),
        ("https://evil.com", False),
        ("//evil.com", False),
        ("dashboard", False),
        ("/\\evil", False),
        ("/\r\nSet-Cookie: injected=1", False),
    ]
    for target, expected in cases:
        assert is_safe_redirect_target(target) is expected


@pytest.mark.unit
def test_resolve_safe_redirect_target_returns_fallback_when_target_missing() -> None:
    """验证 next 缺失时会回退."""
    assert resolve_safe_redirect_target(None, fallback="/dashboard") == "/dashboard"


@pytest.mark.unit
def test_resolve_safe_redirect_target_returns_fallback_when_target_unsafe() -> None:
    """验证 next 不安全时会回退."""
    assert resolve_safe_redirect_target("https://evil.com", fallback="/dashboard") == "/dashboard"


@pytest.mark.unit
def test_resolve_safe_redirect_target_returns_normalized_target() -> None:
    """验证 next 会被 strip 后返回."""
    assert resolve_safe_redirect_target(" /dashboard ", fallback="/") == "/dashboard"
