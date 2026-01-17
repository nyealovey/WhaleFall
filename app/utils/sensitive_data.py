"""敏感字段脱敏工具.

提供通用的 `scrub_sensitive_fields` 方法,用于在写日志或回显
payload 前统一替换密码、令牌等敏感内容,避免泄露.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.types import JsonValue

DEFAULT_SENSITIVE_KEYS = {
    "password",
    "confirm_password",
    "current_password",
    "new_password",
    "old_password",
    "token",
    "api_key",
    "secret",
    "private_key",
}


def scrub_sensitive_fields(
    payload: Mapping[str, JsonValue] | None,
    *,
    extra_keys: Sequence[str] | None = None,
    mask: str = "***",
) -> dict[str, JsonValue]:
    """脱敏敏感字段,返回新的字典副本.

    Args:
        payload: 原始数据,可以是 dict 或 MultiDict.
        extra_keys: 额外需要脱敏的字段名集合.
        mask: 替换后的掩码字符串.

    Returns:
        已脱敏的字典,不会修改原始对象.

    """
    if not isinstance(payload, Mapping):
        return {}

    normalized_keys = set(DEFAULT_SENSITIVE_KEYS)
    if extra_keys:
        normalized_keys.update(str(key).lower() for key in extra_keys)

    def _scrub(value: JsonValue, *, field_name: str | None = None) -> JsonValue:
        if field_name and field_name.lower() in normalized_keys:
            return mask
        if isinstance(value, Mapping):
            return {k: _scrub(v, field_name=str(k)) for k, v in value.items()}
        if isinstance(value, list):
            return [_scrub(item, field_name=field_name) for item in value]
        if isinstance(value, tuple):
            return tuple(_scrub(item, field_name=field_name) for item in value)
        return value

    return {str(key): _scrub(value, field_name=str(key)) for key, value in payload.items()}
