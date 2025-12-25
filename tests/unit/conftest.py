# tests/unit/conftest.py
"""单元测试专用 fixtures.

提供 mock 和 monkeypatch 相关的通用 fixtures。
"""

import pytest


@pytest.fixture
def mock_time(monkeypatch):
    """Mock 时间相关函数，用于测试时间敏感的逻辑."""
    import datetime

    fixed_time = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

    def _set_time(new_time: datetime.datetime):
        nonlocal fixed_time
        fixed_time = new_time

    class MockTime:
        @staticmethod
        def now():
            return fixed_time

        @staticmethod
        def set(new_time: datetime.datetime):
            _set_time(new_time)

    return MockTime
