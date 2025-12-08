"""敏感字段脱敏工具函数的单元测试。"""

import pytest

from app.utils.sensitive_data import scrub_sensitive_fields

MASK = "__MASK__"


@pytest.mark.unit
def test_scrub_sensitive_fields_masks_nested_values() -> None:
    """验证嵌套字段会统一替换为自定义掩码。"""

    payload = {
        "username": "demo",
        "password": "Pa55word",
        "profile": {"token": "abc", "display": "Demo"},
        "secrets": [{"secret": "value"}, {"note": "safe"}],
    }

    sanitized = scrub_sensitive_fields(payload, mask=MASK)

    assert sanitized["password"] == MASK
    assert sanitized["profile"]["token"] == MASK
    assert sanitized["secrets"][0]["secret"] == MASK
    assert sanitized["profile"]["display"] == "Demo"


@pytest.mark.unit
def test_scrub_sensitive_fields_supports_extra_keys() -> None:
    """验证可通过 extra_keys 参数扩展脱敏字段。"""

    payload = {"custom": "value", "api_key": "key"}

    sanitized = scrub_sensitive_fields(payload, extra_keys=["custom"], mask=MASK)

    assert sanitized["custom"] == MASK
    assert sanitized["api_key"] == MASK
