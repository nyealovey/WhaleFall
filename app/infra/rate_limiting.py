"""Flask-Limiter 相关辅助函数.

职责:
- 统一管理限流口径（limit 字符串与 key_func），避免分散在 routes/api 中.
- 不实现自定义限流算法；只负责 glue code.
"""

from __future__ import annotations

from flask import current_app, request
from flask_limiter.util import get_remote_address
from flask_login import current_user


def _extract_login_username() -> str:
    """从登录请求中提取用户名(用于组合限流标识)."""
    username: object | None = None
    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            username = payload.get("username")
    else:
        username = request.form.get("username")

    if isinstance(username, str):
        cleaned = username.strip()
        if cleaned:
            return cleaned
    return "anonymous"


def login_rate_limit_key() -> str:
    """登录限流 key：username + ip."""
    return f"{_extract_login_username()}:{get_remote_address()}"


def password_reset_rate_limit_key() -> str:
    """改密/重置密码限流 key：user_id + ip."""
    user_id = getattr(current_user, "id", None)
    user_key = str(user_id) if user_id is not None else "anonymous"
    return f"{user_key}:{get_remote_address()}"


def build_login_rate_limit() -> str:
    """从 Settings 注入的 app.config 生成登录限流规则."""
    # 约束: Settings -> app.config 是唯一真源，因此这里不做额外兜底链。
    limit = int(current_app.config["LOGIN_RATE_LIMIT"])
    window = int(current_app.config["LOGIN_RATE_WINDOW"])
    return f"{limit} per {window} seconds"


__all__ = [
    "build_login_rate_limit",
    "login_rate_limit_key",
    "password_reset_rate_limit_key",
]
