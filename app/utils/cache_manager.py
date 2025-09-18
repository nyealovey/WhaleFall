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
    """缓存管理器"""

    def __init__(self, cache: Cache) -> None:
        self.cache = cache
        self.default_timeout = 300  # 5分钟默认超时
        self.system_logger = get_system_logger()

    def _generate_key(self, prefix: str, *args, **kwargs: Any) -> str:  # noqa: ANN401
        """生成缓存键"""
        # 将参数序列化为字符串
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}
        key_string = json.dumps(key_data, sort_keys=True, default=str)

        # 生成哈希值（使用SHA256替代MD5）
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        try:
            return self.cache.get(key)
        except Exception as e:
            self.system_logger.warning("获取缓存失败", module="cache", key=key, exception=str(e))
            return None

    def set(self, key: str, value: Any, timeout: int | None = None) -> bool:
        """设置缓存值"""
        try:
            timeout = timeout or self.default_timeout
            self.cache.set(key, value, timeout=timeout)
            return True
        except Exception as e:
            self.system_logger.warning("设置缓存失败", module="cache", key=key, exception=str(e))
            return False

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            self.cache.delete(key)
            return True
        except Exception:
            self.system_logger.warning("删除缓存失败: {key}, 错误: {e}")
            return False

    def clear(self) -> bool:
        """清空所有缓存"""
        try:
            self.cache.clear()
            return True
        except Exception:
            self.system_logger.warning("清空缓存失败: {e}")
            return False

    def get_or_set(self, key: str, func: Callable, timeout: int | None = None, *args, **kwargs: Any) -> Any:  # noqa: ANN401
        """获取缓存值，如果不存在则设置"""
        value = self.get(key)
        if value is None:
            value = func(*args, **kwargs)
            self.set(key, value, timeout)
        return value

    def invalidate_pattern(self, pattern: str) -> int:
        """根据模式删除缓存"""
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
    """初始化缓存管理器"""
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
    """
    缓存装饰器

    Args:
        timeout: 缓存超时时间（秒）
        key_prefix: 键前缀
        unless: 条件函数，返回True时跳过缓存
        key_func: 自定义键生成函数
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


def cache_invalidate(pattern: str) -> Callable:
    """缓存失效装饰器"""

    def cache_decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: "Any", **kwargs: "Any") -> "Any":
            result = f(*args, **kwargs)
            cache_manager.invalidate_pattern(pattern)
            system_logger = get_system_logger()
            system_logger.debug("缓存失效", module="cache", pattern=pattern)
            return result

        return decorated_function

    return cache_decorator


# 特定功能的缓存装饰器
def user_cache(timeout: int = 600) -> Callable:
    """用户相关缓存"""
    return cached(timeout=timeout, key_prefix="user")


def instance_cache(timeout: int = 300) -> Callable:
    """实例相关缓存"""
    return cached(timeout=timeout, key_prefix="instance")


def task_cache(timeout: int = 180) -> Callable:
    """任务相关缓存"""
    return cached(timeout=timeout, key_prefix="task")


def dashboard_cache(timeout: int = 60) -> Callable:
    """仪表板缓存"""
    return cached(timeout=timeout, key_prefix="dashboard")


def api_cache(timeout: int = 300) -> Callable:
    """API缓存"""
    return cached(timeout=timeout, key_prefix="api")


# 缓存键生成函数
def user_key_func(user_id: int, *args, **kwargs: Any) -> str:  # noqa: ANN401
    """用户缓存键生成函数"""
    return f"user:{user_id}"


def instance_key_func(instance_id: int, *args, **kwargs: Any) -> str:  # noqa: ANN401
    """实例缓存键生成函数"""
    return f"instance:{instance_id}"


def task_key_func(task_id: int, *args, **kwargs: Any) -> str:  # noqa: ANN401
    """任务缓存键生成函数"""
    return f"task:{task_id}"


def dashboard_key_func(*args, **kwargs: Any) -> str:  # noqa: ANN401
    """仪表板缓存键生成函数"""
    from flask_login import current_user

    user_id = current_user.id if current_user.is_authenticated else "anonymous"
    return f"dashboard:{user_id}"


# 仪表板缓存相关函数
def cache_dashboard_data(data: "Any", timeout: int = 300) -> None:
    """缓存仪表板数据"""
    cache_manager.set("dashboard_data", data, timeout)


def get_cached_dashboard_data() -> "Any":
    """获取缓存的仪表板数据"""
    return cache_manager.get("dashboard_data")


def invalidate_dashboard_cache() -> None:
    """使仪表板缓存失效"""
    cache_manager.delete("dashboard_data")


# 缓存管理函数
def clear_user_cache(user_id: int) -> None:
    """清除用户相关缓存"""
    cache_manager.invalidate_pattern(f"user:{user_id}*")


def clear_instance_cache(instance_id: int) -> None:
    """清除实例相关缓存"""
    cache_manager.invalidate_pattern(f"instance:{instance_id}*")


def clear_task_cache(task_id: int) -> None:
    """清除任务相关缓存"""
    cache_manager.invalidate_pattern(f"task:{task_id}*")


def clear_dashboard_cache() -> None:
    """清除仪表板缓存"""
    cache_manager.invalidate_pattern("dashboard:*")


def clear_all_cache() -> None:
    """清除所有缓存"""
    cache_manager.clear()


# 缓存统计
def get_cache_stats() -> dict[str, Any]:
    """获取缓存统计信息"""
    try:
        if hasattr(cache_manager.cache.cache, "info"):
            info = cache_manager.cache.cache.info()
            return {"status": "connected", "info": info}
        return {"status": "connected", "info": "No detailed info available"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# 缓存预热
def warm_up_cache() -> "bool | None":
    """缓存预热"""
    try:
        from app.models.instance import Instance
        from app.models.user import User

        # 预热用户缓存
        users = User.query.limit(10).all()
        for user in users:
            cache_manager.set(f"user:{user.id}", user.to_dict(), 600)

        # 预热实例缓存
        instances = Instance.query.limit(10).all()
        for instance in instances:
            cache_manager.set(f"instance:{instance.id}", instance.to_dict(), 300)

        # 预热任务缓存（使用APScheduler）
        from app.scheduler import get_scheduler
        scheduler = get_scheduler()
        jobs = scheduler.get_jobs()
        for job in jobs:
            cache_manager.set(f"job:{job.id}", {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }, 180)

        system_logger = get_system_logger()
        system_logger.info("缓存预热完成", module="cache")
        return True
    except Exception as e:
        system_logger = get_system_logger()
        system_logger.error("缓存预热失败", module="cache", exception=str(e))
        return False
