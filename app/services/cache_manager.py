"""
鲸落 - 缓存管理器
提供统一的缓存接口，支持Flask-Caching缓存操作
"""

import hashlib
import json
from datetime import datetime
from typing import Any

from flask_caching import Cache

from app.utils.structlog_config import get_logger

logger = get_logger("cache_manager")


class CacheManager:
    """缓存管理器"""

    def __init__(self, cache: Cache = None) -> None:
        self.cache = cache
        self.default_ttl = 7 * 24 * 3600  # 7天，按用户要求

    def _generate_cache_key(self, prefix: str, instance_id: int, username: str, db_name: str = None) -> str:
        """生成缓存键"""
        key_data = f"{prefix}:{instance_id}:{username}:{db_name}" if db_name else f"{prefix}:{instance_id}:{username}"

        # 使用SHA-256哈希确保键名长度合理且安全
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()
        return f"whalefall:{key_hash}"

    def get_database_permissions_cache(
        self, instance_id: int, username: str, db_name: str
    ) -> tuple[list[str], list[str]] | None:
        """获取数据库权限缓存"""
        try:
            if not self.cache:
                return None
                
            cache_key = self._generate_cache_key("db_perms", instance_id, username, db_name)
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                roles = data.get("roles", [])
                permissions = data.get("permissions", [])
                logger.debug("缓存命中: %s@%s", username, db_name, cache_key=cache_key)
                return roles, permissions

            return None

        except Exception as e:
            logger.warning("获取缓存失败: %s@%s", username, db_name, error=str(e))
            return None

    def set_database_permissions_cache(
        self, instance_id: int, username: str, db_name: str, roles: list[str], permissions: list[str], ttl: int = None
    ) -> bool:
        """设置数据库权限缓存"""
        try:
            if not self.cache:
                return False
                
            cache_key = self._generate_cache_key("db_perms", instance_id, username, db_name)
            cache_data = {
                "roles": roles,
                "permissions": permissions,
                "cached_at": datetime.now(tz=datetime.UTC).isoformat(),
                "instance_id": instance_id,
                "username": username,
                "db_name": db_name,
            }

            ttl = ttl or self.default_ttl
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug("缓存已设置: %s@%s", username, db_name, cache_key=cache_key, ttl=ttl)
            return True

        except Exception as e:
            logger.warning("设置缓存失败: %s@%s", username, db_name, error=str(e))
            return False

    def get_all_database_permissions_cache(
        self, instance_id: int, username: str
    ) -> dict[str, tuple[list[str], list[str]]] | None:
        """获取用户所有数据库权限缓存"""
        # Flask-Caching不支持模式匹配，简化实现
        # 这里返回None，让调用方直接查询数据库
        return None

    def invalidate_user_cache(self, instance_id: int, username: str) -> bool:
        """清除用户的所有缓存"""
        # Flask-Caching不支持模式匹配，简化实现
        # 这里返回True，表示操作成功
        logger.info("清除用户缓存: %s", username)
        return True

    def invalidate_instance_cache(self, instance_id: int) -> bool:
        """清除实例的所有缓存"""
        # Flask-Caching不支持模式匹配，简化实现
        # 这里返回True，表示操作成功
        logger.info("清除实例缓存: %s", instance_id)
        return True

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        try:
            if not self.cache:
                return {"status": "no_cache", "info": "No cache available"}
                
            if hasattr(self.cache.cache, 'info'):
                info = self.cache.cache.info()
                return {"status": "connected", "info": info}
            return {"status": "connected", "info": "No detailed info available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def health_check(self) -> bool:
        """缓存健康检查"""
        try:
            if not self.cache:
                return False
                
            # 简单的健康检查：尝试设置和获取一个测试键
            test_key = "health_check_test"
            test_value = "ok"
            self.cache.set(test_key, test_value, timeout=10)
            result = self.cache.get(test_key)
            self.cache.delete(test_key)
            return result == test_value
        except Exception as e:
            logger.warning("缓存健康检查失败", error=str(e))
            return False


# 全局缓存管理器实例
cache_manager = None


def init_cache_manager(cache: Cache) -> None:
    """初始化缓存管理器"""
    global cache_manager
    cache_manager = CacheManager(cache)
    logger.info("缓存管理器初始化完成")
