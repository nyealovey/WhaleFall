"""
鲸落 - 速率限制工具
"""

import time
from collections.abc import Callable
from functools import wraps

from flask import flash, redirect, request, url_for
from flask_caching import Cache

from app.constants.system_constants import ErrorMessages
from app.utils.response_utils import jsonify_unified_error_message
from app.utils.structlog_config import get_system_logger

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class RateLimiter:
    """速率限制器"""

    def __init__(self, cache: Cache = None):
        self.cache = cache
        self.memory_store = {}  # 内存存储，用于无缓存环境

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """生成缓存键"""
        return f"rate_limit:{endpoint}:{identifier}"

    def _get_memory_key(self, identifier: str, endpoint: str) -> str:
        """生成内存键"""
        return f"{endpoint}:{identifier}"

    def is_allowed(self, identifier: str, endpoint: str, limit: int, window: int) -> dict[str, any]:
        """
        检查是否允许请求

        Args:
            identifier: 标识符（IP地址或用户ID）
            endpoint: 端点名称
            limit: 限制次数
            window: 时间窗口（秒）

        Returns:
            dict: 包含是否允许、剩余次数、重置时间等信息
        """
        current_time = int(time.time())
        window_start = current_time - window

        if self.cache:
            try:
                return self._check_cache(identifier, endpoint, limit, window, current_time, window_start)
            except Exception as e:
                system_logger = get_system_logger()
                system_logger.warning(
                    "缓存速率限制检查失败，降级到内存模式",
                    module="rate_limiter",
                    exception=str(e),
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
    ) -> dict[str, any]:
        """使用缓存检查速率限制"""
        key = self._get_key(identifier, endpoint)
        
        # 获取当前窗口内的请求记录
        requests = self.cache.get(key) or []
        
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
    ) -> dict[str, any]:
        """使用内存检查速率限制"""
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


# 全局速率限制器实例
rate_limiter = RateLimiter()


def login_rate_limit(func=None, *, limit: int = None, window: int = None):
    """登录速率限制"""
    from app.config import Config

    if limit is None:
        limit = Config.LOGIN_RATE_LIMIT
    if window is None:
        window = Config.LOGIN_RATE_WINDOW

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            if request.method.upper() in SAFE_METHODS:
                return f(*args, **kwargs)

            endpoint = "login_attempts"
            identifier = request.remote_addr or "unknown"
            system_logger = get_system_logger()

            result = rate_limiter.is_allowed(identifier, endpoint, limit, window)

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

                flash(ErrorMessages.RATE_LIMIT_EXCEEDED, "error")
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


def password_reset_rate_limit(func=None, *, limit: int = None, window: int = None):
    from app.config import Config

    if limit is None:
        limit = 3  # 密码重置限制
    if window is None:
        window = Config.SESSION_LIFETIME  # 1小时
    """密码重置速率限制"""
    if func is None:
        return login_rate_limit(limit=limit, window=window)
    return login_rate_limit(func, limit=limit, window=window)


# 初始化速率限制器
def init_rate_limiter(cache: Cache = None):
    """初始化速率限制器"""
    global rate_limiter
    rate_limiter = RateLimiter(cache)
    system_logger = get_system_logger()
    system_logger.info("速率限制器初始化完成", module="rate_limiter")


__all__ = [
    "rate_limiter",
    "login_rate_limit",
    "password_reset_rate_limit",
    "init_rate_limiter",
]
