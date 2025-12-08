"""
鲸落 - 缓存管理工具
基于Flask-Caching的通用缓存管理器，提供装饰器和通用缓存功能
"""

import hashlib
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from flask_caching import Cache

from app.utils.structlog_config import get_system_logger


class CacheManager:
    """缓存管理器。

    基于 Flask-Caching 的通用缓存管理器，提供缓存的增删改查和装饰器功能。

    Attributes:
        cache: Flask-Caching 实例。
        default_timeout: 默认超时时间（秒），默认 300 秒。
        system_logger: 系统日志记录器。

    """

    def __init__(self, cache: Cache) -> None:
        self.cache = cache
        self.default_timeout = 300  # 5分钟默认超时
        self.system_logger = get_system_logger()

    def _generate_key(self, prefix: str, *args, **kwargs: Any) -> str:
        """生成缓存键。

        使用 SHA256 哈希算法生成唯一的缓存键。

        Args:
            prefix: 缓存键前缀。
            *args: 位置参数。
            **kwargs: 关键字参数。

        Returns:
            格式为 "prefix:hash" 的缓存键。

        """
        # 将参数序列化为字符串
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}
        key_string = json.dumps(key_data, sort_keys=True, default=str)

        # 生成哈希值（使用SHA256替代MD5）
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Any | None:
        """获取缓存值。

        Args:
            key: 缓存键。

        Returns:
            缓存值，如果不存在或获取失败返回 None。

        """
        try:
            return self.cache.get(key)
        except Exception as e:
            self.system_logger.warning("获取缓存失败", module="cache", key=key, exception=str(e))
            return None

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """设置缓存值。

        Args:
            key: 缓存键。
            value: 缓存值。
            timeout: 超时时间（秒），默认使用 default_timeout。

        Returns:
            设置成功返回 True，失败返回 False。

        """
        try:
            timeout = timeout or self.default_timeout
            self.cache.set(key, value, timeout=timeout)
            return True
        except Exception as e:
            self.system_logger.warning("设置缓存失败", module="cache", key=key, exception=str(e))
            return False

    def delete(self, key: str) -> bool:
        """删除缓存值。

        Args:
            key: 缓存键。

        Returns:
            删除成功返回 True，失败返回 False。

        """
        try:
            self.cache.delete(key)
            return True
        except Exception:
            self.system_logger.warning("删除缓存失败: {key}, 错误: {e}")
            return False

    def clear(self) -> bool:
        """清空所有缓存。

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            self.cache.clear()
            return True
        except Exception:
            self.system_logger.warning("清空缓存失败: {e}")
            return False

    def get_or_set(self, key: str, func: Callable, timeout: int | None = None, *args, **kwargs: Any) -> Any:
        """获取缓存值，如果不存在则调用函数生成并写入。

        Args:
            key: 缓存键。
            func: 当缓存缺失时执行的回调。
            timeout: 缓存超时时间，None 表示使用默认值。
            *args: 传递给回调的可变位置参数。
            **kwargs: 传递给回调的关键字参数。

        Returns:
            缓存中已有的值或刚计算出的函数返回值。

        """
        value = self.get(key)
        if value is None:
            value = func(*args, **kwargs)
            self.set(key, value, timeout)
        return value

    def invalidate_pattern(self, pattern: str) -> int:
        """根据模式批量删除缓存项。

        Args:
            pattern: Redis 等后端支持的通配模式。

        Returns:
            实际删除的键数量，不支持模式删除时返回 0。

        """
        try:
            # 这里需要根据具体的缓存后端实现
            # Redis支持模式匹配，其他后端可能需要遍历
            if hasattr(self.cache.cache, "delete_pattern"):
                return self.cache.cache.delete_pattern(pattern)
            self.system_logger.warning("当前缓存后端不支持模式删除")
            return 0
        except Exception:
            self.system_logger.warning("模式删除缓存失败: {pattern}, 错误: {e}")
            return 0


# 全局缓存管理器实例
cache_manager = None


def init_cache_manager(cache: Cache) -> None:
    """初始化全局缓存管理器。

    Args:
        cache: Flask-Caching 创建的缓存实例。

    Returns:
        None. 函数执行后全局 cache_manager 变量会被初始化。

    """
    global cache_manager
    cache_manager = CacheManager(cache)
    system_logger = get_system_logger()
    system_logger.info("缓存管理器初始化完成", module="cache")


def cached(
    timeout: int = 300,
    key_prefix: str = "default",
    unless: Callable | None = None,
    key_func: Callable | None = None,
) -> Callable:
    """缓存装饰器，自动复用函数返回值。

    Args:
        timeout: 缓存超时时间（秒）。
        key_prefix: 键前缀，用于区分不同函数。
        unless: 条件函数，返回 True 时跳过缓存。
        key_func: 自定义缓存键生成函数。

    Returns:
        可用于装饰目标函数的包装器。

    """

    def cache_decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: "Any", **kwargs: "Any") -> "Any":
            # 检查是否跳过缓存
            if unless and unless():
                return f(*args, **kwargs)

            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager._generate_key(f"{key_prefix}:{f.__name__}", *args, **kwargs)

            # 尝试获取缓存
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                system_logger = get_system_logger()
                system_logger.debug("缓存命中", module="cache", cache_key=cache_key)
                return cached_value

            # 执行函数并缓存结果
            result = f(*args, **kwargs)
            cache_manager.set(cache_key, result, timeout)
            system_logger = get_system_logger()
            system_logger.debug("缓存设置", module="cache", cache_key=cache_key)

            return result

        return decorated_function

    return cache_decorator


def dashboard_cache(timeout: int = 60) -> Callable:
    """仪表板缓存装饰器，绑定统一前缀。

    Args:
        timeout: 缓存超时时间（秒），默认为 1 分钟。

    Returns:
        应用于仪表板查询函数的缓存装饰器。

    """
    return cached(timeout=timeout, key_prefix="dashboard")
