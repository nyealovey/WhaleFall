# tests/unit/conftest.py
"""单元测试专用 fixtures.

提供 mock 和 monkeypatch 相关的通用 fixtures。
"""

import pytest


@pytest.fixture(autouse=True)
def _unit_test_env(monkeypatch):
    """为 unit tests 强制注入隔离环境变量.

    目标:
    - unit tests 不依赖外部 Redis/数据库等基础设施
    - 避免开发者本机环境变量影响测试稳定性
    """
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    # Block `.env` from injecting an invalid key; let PasswordManager fall back to a temp key.
    monkeypatch.setenv("PASSWORD_ENCRYPTION_KEY", "")
