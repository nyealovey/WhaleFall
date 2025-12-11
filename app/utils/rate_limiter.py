"""鲸落 - 速率限制工具."""

import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from flask import flash, redirect, request, url_for
from flask_caching import Cache

from app.constants import FlashCategory
from app.constants.system_constants import ErrorMessages
from app.utils.response_utils import jsonify_unified_error_message
from app.utils.structlog_config import get_system_logger

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
P = ParamSpec("P")
R = TypeVar("R")
RATE_LIMITER_CACHE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
)


class RateLimiter:
    """速率限制器.

    基于滑动窗口算法实现的速率限制器,支持缓存和内存两种存储方式.
    当缓存不可用时自动降级到内存模式.

    Attributes:
        cache: Flask-Caching 缓存实例,可选.
        memory_store: 内存存储字典,用于无缓存环境.

    Example:
        >>> limiter = RateLimiter(cache)
        >>> result = limiter.is_allowed('192.168.1.1', 'login', limit=5, window=60)
        >>> if not result['allowed']:
        ...     print(f"请在 {result['retry_after']} 秒后重试")

    """

    def __init__(self, cache: Cache | None = None) -> None:
        self.cache = cache
        self.memory_store: dict[str, list[int]] = {}  # 内存存储,用于无缓存环境

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """生成缓存键.

        Args:
            identifier: 唯一标识符,例如 IP 地址或用户 ID.
            endpoint: 端点名称.

        Returns:
            缓存键字符串,格式:'rate_limit:endpoint:identifier'.

        """
        return f"rate_limit:{endpoint}:{identifier}"

    def _get_memory_key(self, identifier: str, endpoint: str) -> str:
        """生成内存键.

        Args:
            identifier: 唯一标识符.
            endpoint: 端点名称.

        Returns:
            内存键字符串,格式:'endpoint:identifier'.

        """
        return f"{endpoint}:{identifier}"

    def is_allowed(self, identifier: str, endpoint: str, limit: int, window: int) -> dict[str, object]:
        """判断给定标识符在当前窗口内是否允许访问.

        Args:
            identifier: 唯一标识(IP 或用户 ID).
            endpoint: 限流的端点名称.
            limit: 允许的请求次数.
            window: 时间窗口(秒).

        Returns:
            dict[str, Any]: 包含是否允许、剩余次数及 reset 时间等信息.

        """
        current_time = int(time.time())
        window_start = current_time - window

        if self.cache:
            try:
                return self._check_cache(identifier, endpoint, limit, window, current_time, window_start)
            except RATE_LIMITER_CACHE_EXCEPTIONS as cache_error:
                system_logger = get_system_logger()
                system_logger.warning(
                    "缓存速率限制检查失败,降级到内存模式",
                    module="rate_limiter",
                    error=str(cache_error),
                )
                # 降级到内存模式
                return self._check_memory(identifier, endpoint, limit, window, current_time, window_start)
        else:
            return self._check_memory(identifier, endpoint, limit, window, current_time, window_start)

    def _check_cache(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
        window: int,
        current_time: int,
        window_start: int,
    ) -> dict[str, object]:
        """基于缓存记录检查速率限制.

        Args:
            identifier: 标识符.
            endpoint: 端点名称.
            limit: 限制次数.
            window: 时间窗口(秒).
            current_time: 当前时间戳.
            window_start: 窗口起始时间戳.

        Returns:
            dict[str, Any]: 限流检查结果.

        """
        key = self._get_key(identifier, endpoint)

        # 获取当前窗口内的请求记录
        requests: list[int] = list(self.cache.get(key) or [])

        # 移除过期的记录
        requests = [req_time for req_time in requests if req_time > window_start]

        # 检查是否超过限制
        if len(requests) >= limit:
            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": current_time + window,
                "retry_after": window,
            }

        # 添加当前请求
        requests.append(current_time)

        # 保存更新后的请求记录
        self.cache.set(key, requests, timeout=window)

        return {
            "allowed": True,
            "remaining": limit - len(requests),
            "reset_time": current_time + window,
            "retry_after": 0,
        }

    def _check_memory(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
        window: int,
        current_time: int,
        window_start: int,
    ) -> dict[str, object]:
        """在无缓存情况下,使用内存列表进行限流.

        Args:
            identifier: 标识符.
            endpoint: 端点名称.
            limit: 限制次数.
            window: 时间窗口(秒).
            current_time: 当前时间戳.
            window_start: 窗口起始时间戳.

        Returns:
            dict[str, Any]: 限流检查结果.

        """
        key = self._get_memory_key(identifier, endpoint)

        if key not in self.memory_store:
            self.memory_store[key] = []

        # 清理过期记录
        self.memory_store[key] = [timestamp for timestamp in self.memory_store[key] if timestamp > window_start]

        current_count = len(self.memory_store[key])

        if current_count >= limit:
            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": current_time + window,
                "retry_after": window,
            }

        # 添加当前请求
        self.memory_store[key].append(current_time)

        return {
            "allowed": True,
            "remaining": limit - current_count - 1,
            "reset_time": current_time + window,
            "retry_after": 0,
        }


class RateLimiterRegistry:
    """速率限制器注册表,用于集中管理实例并避免修改全局变量."""

    _limiter: RateLimiter = RateLimiter()

    @classmethod
    def configure(cls, cache: Cache | None) -> RateLimiter:
        """初始化或替换当前速率限制器实例."""
        cls._limiter = RateLimiter(cache)
        return cls._limiter

    @classmethod
    def get(cls) -> RateLimiter:
        """返回当前注册的速率限制器."""
        return cls._limiter


def login_rate_limit(
    func: Callable[P, R] | None = None,
    *,
    limit: int | None = None,
    window: int | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]] | Callable[P, R]:
    """登录接口速率限制装饰器.

    Args:
        func: 被装饰的函数.
        limit: 可选自定义限制次数.
        window: 可选自定义时间窗口(秒).

    Returns:
        Callable: 包装后的视图函数.

    """
    from app.config import Config

    if limit is None:
        limit = Config.LOGIN_RATE_LIMIT
    if window is None:
        window = Config.LOGIN_RATE_WINDOW

    def decorator(f: Callable[P, R]) -> Callable[P, R]:
        @wraps(f)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if request.method.upper() in SAFE_METHODS:
                return f(*args, **kwargs)

            endpoint = "login_attempts"
            identifier = request.remote_addr or "unknown"
            system_logger = get_system_logger()

            limiter = RateLimiterRegistry.get()
            result = limiter.is_allowed(identifier, endpoint, limit, window)

            if not result["allowed"]:
                system_logger.warning(
                    "登录被速率限制",
                    module="rate_limiter",
                    identifier=identifier,
                    endpoint=endpoint,
                    retry_after=result["retry_after"],
                )
                extra = {
                    "identifier": identifier,
                    "endpoint": endpoint,
                    "retry_after": result["retry_after"],
                    "limit": limit,
                    "remaining": result["remaining"],
                    "reset_time": result["reset_time"],
                }

                if request.is_json:
                    response, status = jsonify_unified_error_message(
                        ErrorMessages.RATE_LIMIT_EXCEEDED,
                        status_code=429,
                        message_key="RATE_LIMIT_EXCEEDED",
                        extra=extra,
                    )
                    response.headers["Retry-After"] = str(result["retry_after"])
                    response.headers["X-RateLimit-Limit"] = str(limit)
                    response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                    response.headers["X-RateLimit-Reset"] = str(result["reset_time"])
                    return response, status

                flash(ErrorMessages.RATE_LIMIT_EXCEEDED, FlashCategory.ERROR)
                response = redirect(url_for("auth.login"))
                response.status_code = 429
                response.headers["Retry-After"] = str(result["retry_after"])
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                response.headers["X-RateLimit-Reset"] = str(result["reset_time"])
                return response

            response = f(*args, **kwargs)
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                response.headers["X-RateLimit-Reset"] = str(result["reset_time"])
            return response

        return wrapped

    if func is None:
        return decorator
    return decorator(func)


def password_reset_rate_limit(
    func: Callable[P, R] | None = None,
    *,
    limit: int | None = None,
    window: int | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]] | Callable[P, R]:
    """密码重置速率限制装饰器.

    默认限制:3 次/小时.

    Args:
        func: 被装饰的函数.
        limit: 可选自定义限制次数,默认 3 次.
        window: 可选自定义时间窗口(秒),默认 1 小时.

    Returns:
        包装后的视图函数.

    Example:
        >>> @password_reset_rate_limit
        ... def reset_password():
        ...     pass

    """
    from app.config import Config

    if limit is None:
        limit = 3  # 密码重置限制
    if window is None:
        window = Config.SESSION_LIFETIME  # 1小时
    if func is None:
        return login_rate_limit(limit=limit, window=window)
    return login_rate_limit(func, limit=limit, window=window)


# 初始化速率限制器
def init_rate_limiter(cache: Cache | None = None) -> None:
    """初始化速率限制器.

    Args:
        cache: Flask-Caching 缓存实例,可选.如果不提供则使用内存模式.

    Returns:
        None.

    Example:
        >>> from flask_caching import Cache
        >>> cache = Cache(app)
        >>> init_rate_limiter(cache)

    """
    RateLimiterRegistry.configure(cache)
    system_logger = get_system_logger()
    system_logger.info("速率限制器初始化完成", module="rate_limiter")


__all__ = [
    "RateLimiterRegistry",
    "init_rate_limiter",
    "login_rate_limit",
    "password_reset_rate_limit",
]
