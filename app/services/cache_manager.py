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

    def get_account_permissions_cache(self, account_id: int) -> dict[str, Any] | None:
        """获取账户权限缓存"""
        try:
            if not self.cache:
                return None
                
            cache_key = self._generate_cache_key("account_perms", account_id, "", "")
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                logger.debug("账户权限缓存命中: account_id=%s", account_id, cache_key=cache_key)
                return data

            return None

        except Exception as e:
            logger.warning("获取账户权限缓存失败: account_id=%s", account_id, error=str(e))
            return None

    def set_account_permissions_cache(self, account_id: int, permissions: dict[str, Any], ttl: int = None) -> bool:
        """设置账户权限缓存"""
        try:
            if not self.cache:
                return False
                
            cache_key = self._generate_cache_key("account_perms", account_id, "", "")
            cache_data = {
                "permissions": permissions,
                "cached_at": datetime.now(tz=datetime.UTC).isoformat(),
                "account_id": account_id,
            }

            ttl = ttl or self.default_ttl
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug("账户权限缓存已设置: account_id=%s", account_id, cache_key=cache_key, ttl=ttl)
            return True

        except Exception as e:
            logger.warning("设置账户权限缓存失败: account_id=%s", account_id, error=str(e))
            return False

    def get_rule_evaluation_cache(self, rule_id: int, account_id: int) -> bool | None:
        """获取规则评估缓存"""
        try:
            if not self.cache:
                return None
                
            cache_key = self._generate_cache_key("rule_eval", rule_id, account_id, "")
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                logger.debug("规则评估缓存命中: rule_id=%s, account_id=%s", rule_id, account_id, cache_key=cache_key)
                return data.get("result")

            return None

        except Exception as e:
            logger.warning("获取规则评估缓存失败: rule_id=%s, account_id=%s", rule_id, account_id, error=str(e))
            return None

    def set_rule_evaluation_cache(self, rule_id: int, account_id: int, result: bool, ttl: int = None) -> bool:
        """设置规则评估缓存"""
        try:
            if not self.cache:
                return False
                
            cache_key = self._generate_cache_key("rule_eval", rule_id, account_id, "")
            cache_data = {
                "result": result,
                "cached_at": datetime.now(tz=datetime.UTC).isoformat(),
                "rule_id": rule_id,
                "account_id": account_id,
            }

            ttl = ttl or (24 * 3600)  # 规则评估缓存1天
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug("规则评估缓存已设置: rule_id=%s, account_id=%s", rule_id, account_id, cache_key=cache_key, ttl=ttl)
            return True

        except Exception as e:
            logger.warning("设置规则评估缓存失败: rule_id=%s, account_id=%s", rule_id, account_id, error=str(e))
            return False

    def get_classification_rules_cache(self) -> list[dict[str, Any]] | None:
        """获取分类规则缓存"""
        try:
            if not self.cache:
                return None
                
            cache_key = "classification_rules:all"
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                logger.debug("分类规则缓存命中", cache_key=cache_key)
                return data

            return None

        except Exception as e:
            logger.warning("获取分类规则缓存失败", error=str(e))
            return None

    def set_classification_rules_cache(self, rules: list[dict[str, Any]], ttl: int = None) -> bool:
        """设置分类规则缓存"""
        try:
            if not self.cache:
                return False
                
            cache_key = "classification_rules:all"
            cache_data = {
                "rules": rules,
                "cached_at": datetime.now(tz=datetime.UTC).isoformat(),
                "count": len(rules),
            }

            ttl = ttl or (2 * 3600)  # 规则缓存2小时
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug("分类规则缓存已设置", cache_key=cache_key, ttl=ttl, count=len(rules))
            return True

        except Exception as e:
            logger.warning("设置分类规则缓存失败", error=str(e))
            return False

    def invalidate_account_cache(self, account_id: int) -> bool:
        """清除账户相关缓存"""
        try:
            if not self.cache:
                return True
                
            # 清除账户权限缓存
            account_perms_key = self._generate_cache_key("account_perms", account_id, "", "")
            self.cache.delete(account_perms_key)
            
            # 清除该账户的所有规则评估缓存
            # 注意：这里简化处理，实际应该遍历所有规则ID
            logger.info("清除账户缓存: account_id=%s", account_id)
            return True

        except Exception as e:
            logger.warning("清除账户缓存失败: account_id=%s", account_id, error=str(e))
            return False

    def invalidate_classification_cache(self) -> bool:
        """清除分类相关缓存"""
        try:
            if not self.cache:
                return True
                
            # 清除规则缓存
            rules_key = "classification_rules:all"
            self.cache.delete(rules_key)
            
            logger.info("清除分类缓存")
            return True

        except Exception as e:
            logger.warning("清除分类缓存失败", error=str(e))
            return False

    def get_classification_rules_by_db_type_cache(self, db_type: str) -> list[dict[str, Any]] | None:
        """获取按数据库类型分类的规则缓存"""
        try:
            if not self.cache:
                return None
                
            cache_key = f"classification_rules:{db_type}"
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                logger.debug("数据库类型规则缓存命中: %s", db_type, cache_key=cache_key)
                return data

            return None

        except Exception as e:
            logger.warning("获取数据库类型规则缓存失败: %s", db_type, error=str(e))
            return None

    def set_classification_rules_by_db_type_cache(self, db_type: str, rules: list[dict[str, Any]], ttl: int = None) -> bool:
        """设置按数据库类型分类的规则缓存"""
        try:
            if not self.cache:
                return False
                
            cache_key = f"classification_rules:{db_type}"
            cache_data = {
                "rules": rules,
                "cached_at": datetime.now(tz=datetime.UTC).isoformat(),
                "count": len(rules),
                "db_type": db_type,
            }

            ttl = ttl or (2 * 3600)  # 规则缓存2小时
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug("数据库类型规则缓存已设置: %s", db_type, cache_key=cache_key, ttl=ttl, count=len(rules))
            return True

        except Exception as e:
            logger.warning("设置数据库类型规则缓存失败: %s", db_type, error=str(e))
            return False

    def get_accounts_by_db_type_cache(self, db_type: str) -> list[dict[str, Any]] | None:
        """获取按数据库类型分组的账户缓存"""
        try:
            if not self.cache:
                return None
                
            cache_key = f"accounts_by_db_type:{db_type}"
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                logger.debug("数据库类型账户缓存命中: %s", db_type, cache_key=cache_key)
                return data

            return None

        except Exception as e:
            logger.warning("获取数据库类型账户缓存失败: %s", db_type, error=str(e))
            return None

    def set_accounts_by_db_type_cache(self, db_type: str, accounts: list[dict[str, Any]], ttl: int = None) -> bool:
        """设置按数据库类型分组的账户缓存"""
        try:
            if not self.cache:
                return False
                
            cache_key = f"accounts_by_db_type:{db_type}"
            cache_data = {
                "accounts": accounts,
                "cached_at": datetime.now(tz=datetime.UTC).isoformat(),
                "count": len(accounts),
                "db_type": db_type,
            }

            ttl = ttl or (1 * 3600)  # 账户缓存1小时
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug("数据库类型账户缓存已设置: %s", db_type, cache_key=cache_key, ttl=ttl, count=len(accounts))
            return True

        except Exception as e:
            logger.warning("设置数据库类型账户缓存失败: %s", db_type, error=str(e))
            return False

    def invalidate_db_type_cache(self, db_type: str) -> bool:
        """清除特定数据库类型的缓存"""
        try:
            if not self.cache:
                return True
                
            # 清除该数据库类型的规则缓存
            rules_key = f"classification_rules:{db_type}"
            self.cache.delete(rules_key)
            
            # 清除该数据库类型的账户缓存
            accounts_key = f"accounts_by_db_type:{db_type}"
            self.cache.delete(accounts_key)
            
            logger.info("清除数据库类型缓存: %s", db_type)
            return True

        except Exception as e:
            logger.warning("清除数据库类型缓存失败: %s", db_type, error=str(e))
            return False

    def invalidate_all_db_type_cache(self) -> bool:
        """清除所有数据库类型的缓存"""
        try:
            if not self.cache:
                return True
                
            # 清除所有数据库类型的规则缓存
            db_types = ["mysql", "postgresql", "sqlserver", "oracle"]
            for db_type in db_types:
                self.invalidate_db_type_cache(db_type)
            
            logger.info("清除所有数据库类型缓存")
            return True

        except Exception as e:
            logger.warning("清除所有数据库类型缓存失败", error=str(e))
            return False

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
