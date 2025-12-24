"""鲸落 - 重定向安全工具.

统一处理 `next` 参数等重定向目标的校验,避免开放重定向(Open Redirect).
"""

from __future__ import annotations

from urllib.parse import urlparse


def is_safe_redirect_target(target: str) -> bool:
    """判断重定向目标是否安全.

    安全定义(最小策略):
    - 仅允许以 `/` 开头的站内路径(不允许 scheme/netloc).
    - 禁止以 `//` 开头,避免被浏览器解析为 scheme-relative URL.
    - 禁止包含 CR/LF 等控制字符,避免响应头注入类风险.
    - 禁止反斜杠,防止部分客户端对 `\\` 的 URL 归一化产生绕过.

    Args:
        target: 目标 URL.

    Returns:
        True 表示允许跳转,False 表示应当拒绝并回退到安全地址.

    """
    normalized = target.strip()
    if not normalized:
        return False
    if "\r" in normalized or "\n" in normalized:
        return False
    if "\\" in normalized:
        return False
    if not normalized.startswith("/"):
        return False
    if normalized.startswith("//"):
        return False

    parsed = urlparse(normalized)
    return not (parsed.scheme or parsed.netloc)


def resolve_safe_redirect_target(target: str | None, *, fallback: str) -> str:
    """解析安全的重定向目标,并在不安全时回退到默认地址.

    Args:
        target: 传入的 next 参数.
        fallback: 兜底跳转目标,必须是站内安全路径.

    Returns:
        最终可用于 redirect() 的目标路径.

    """
    if not target:
        return fallback
    normalized = target.strip()
    if not normalized:
        return fallback
    return normalized if is_safe_redirect_target(normalized) else fallback
