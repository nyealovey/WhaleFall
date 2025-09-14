"""
泰摸鱼吧 - 速率限制工具
"""

import time
from collections.abc import Callable
from functools import wraps

from flask import jsonify, request

from app.utils.structlog_config import get_system_logger


class RateLimiter:
    """速率限制器"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.memory_store = {}  # 内存存储，用于无Redis环境

    def _get_key(self, identifier: str, endpoint: str) -> str:
        """生成Redis键"""
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

        if self.redis_client:
            try:
                return self._check_redis(identifier, endpoint, limit, window, current_time, window_start)
            except Exception as e:
                system_logger = get_system_logger()
                system_logger.warning(
                    "Redis速率限制检查失败，降级到内存模式",
                    module="rate_limiter",
                    exception=e,
                )
                # 降级到内存模式
                return self._check_memory(identifier, endpoint, limit, window, current_time, window_start)
        else:
            return self._check_memory(identifier, endpoint, limit, window, current_time, window_start)

    def _check_redis(
        self,
        identifier: str,
        endpoint: str,
        limit: int,
        window: int,
        current_time: int,
        window_start: int,
    ) -> dict[str, any]:
        """使用Redis检查速率限制"""
        key = self._get_key(identifier, endpoint)
        pipe = self.redis_client.pipeline()

        # 移除过期的记录
        pipe.zremrangebyscore(key, 0, window_start)

        # 获取当前窗口内的请求数
        pipe.zcard(key)

        # 添加当前请求
        pipe.zadd(key, {str(current_time): current_time})

        # 设置过期时间
        pipe.expire(key, window)

        results = pipe.execute()
        current_count = results[1]

        if current_count >= limit:
            return {
                "allowed": False,
                "remaining": 0,
                "reset_time": current_time + window,
                "retry_after": window,
            }

        return {
            "allowed": True,
            "remaining": limit - current_count - 1,
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

    def get_remaining(self, identifier: str, endpoint: str, limit: int, window: int) -> int:
        """获取剩余请求次数"""
        try:
            result = self.is_allowed(identifier, endpoint, limit, window)
            return result["remaining"]
        except Exception as e:
            system_logger = get_system_logger()
            system_logger.warning("获取剩余请求次数失败", module="rate_limiter", exception=e)
            return limit  # 出错时返回最大限制

    def reset(self, identifier: str, endpoint: str):
        """重置速率限制"""
        if self.redis_client:
            try:
                key = self._get_key(identifier, endpoint)
                self.redis_client.delete(key)
            except Exception as e:
                system_logger = get_system_logger()
                system_logger.warning("Redis重置速率限制失败", module="rate_limiter", exception=e)
                # 降级到内存模式
                key = self._get_memory_key(identifier, endpoint)
                if key in self.memory_store:
                    del self.memory_store[key]
        else:
            key = self._get_memory_key(identifier, endpoint)
            if key in self.memory_store:
                del self.memory_store[key]


# 全局速率限制器实例
rate_limiter = RateLimiter()


def rate_limit(
    limit: int,
    window: int = 60,
    per: str = "ip",
    identifier_func: Callable | None = None,
):
    """
    速率限制装饰器

    Args:
        limit: 限制次数
        window: 时间窗口（秒）
        per: 限制类型（'ip' 或 'user'）
        identifier_func: 自定义标识符函数
    """

    def rate_limit_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取标识符
            if identifier_func:
                identifier = identifier_func()
            elif per == "user":
                from flask_login import current_user

                identifier = str(current_user.id) if current_user.is_authenticated else request.remote_addr
            else:
                identifier = request.remote_addr

            # 检查速率限制
            result = rate_limiter.is_allowed(identifier, f.__name__, limit, window)

            if not result["allowed"]:
                response = jsonify(
                    {
                        "error": "请求过于频繁",
                        "message": f"每分钟最多允许 {limit} 次请求",
                        "retry_after": result["retry_after"],
                    }
                )
                response.status_code = 429
                response.headers["Retry-After"] = str(result["retry_after"])
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                response.headers["X-RateLimit-Reset"] = str(result["reset_time"])
                return response

            # 添加速率限制头
            response = f(*args, **kwargs)
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                response.headers["X-RateLimit-Reset"] = str(result["reset_time"])

            return response

        return decorated_function

    return rate_limit_decorator


def login_rate_limit(func=None, *, limit: int = None, window: int = None):
    """登录速率限制"""
    from app.constants import SystemConstants

    if limit is None:
        limit = SystemConstants.LOGIN_RATE_LIMIT
    if window is None:
        window = SystemConstants.LOGIN_RATE_WINDOW
    if func is None:
        return lambda f: rate_limit(limit, window, per="ip")(f)
    return rate_limit(limit, window, per="ip")(func)


def api_rate_limit(func=None, *, limit: int = None, window: int = None):
    """API速率限制"""
    from app.constants import SystemConstants

    if limit is None:
        limit = SystemConstants.RATE_LIMIT_REQUESTS
    if window is None:
        window = SystemConstants.RATE_LIMIT_WINDOW
    if func is None:
        return lambda f: rate_limit(limit, window, per="user")(f)
    return rate_limit(limit, window, per="user")(func)


def password_reset_rate_limit(func=None, *, limit: int = None, window: int = None):
    from app.constants import SystemConstants

    if limit is None:
        limit = 3  # 密码重置限制
    if window is None:
        window = SystemConstants.SESSION_LIFETIME  # 1小时
    """密码重置速率限制"""
    if func is None:
        return lambda f: rate_limit(limit, window, per="ip")(f)
    return rate_limit(limit, window, per="ip")(func)


def registration_rate_limit(func=None, *, limit: int = None, window: int = None):
    from app.constants import SystemConstants

    if limit is None:
        limit = 3  # 注册限制
    if window is None:
        window = SystemConstants.SESSION_LIFETIME  # 1小时
    """注册速率限制"""
    if func is None:
        return lambda f: rate_limit(limit, window, per="ip")(f)
    return rate_limit(limit, window, per="ip")(func)


def task_execution_rate_limit(func=None, *, limit: int = 10, window: int = 60):
    """任务执行速率限制"""
    if func is None:
        return lambda f: rate_limit(limit, window, per="user")(f)
    return rate_limit(limit, window, per="user")(func)


# 初始化速率限制器
def init_rate_limiter(redis_client=None):
    """初始化速率限制器"""
    global rate_limiter
    rate_limiter = RateLimiter(redis_client)
    system_logger = get_system_logger()
    system_logger.info("速率限制器初始化完成", module="rate_limiter")


# 获取速率限制状态
def get_rate_limit_status(identifier: str, endpoint: str, limit: int, window: int) -> dict[str, any]:
    """获取速率限制状态"""
    return rate_limiter.is_allowed(identifier, endpoint, limit, window)


# 清理过期的速率限制记录
def cleanup_rate_limits():
    """清理过期的速率限制记录"""
    if rate_limiter.redis_client:
        # Redis会自动清理过期键
        pass
    else:
        # 清理内存中的过期记录
        current_time = int(time.time())
        for key in list(rate_limiter.memory_store.keys()):
            timestamps = rate_limiter.memory_store[key]
            # 保留最近1小时的记录
            rate_limiter.memory_store[key] = [ts for ts in timestamps if ts > current_time - 3600]
            # 如果列表为空，删除键
            if not rate_limiter.memory_store[key]:
                del rate_limiter.memory_store[key]
