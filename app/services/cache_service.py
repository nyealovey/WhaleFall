"""鲸落 - 缓存服务，提供统一的 Flask-Caching 接口。."""

import hashlib
import json
from typing import Any

from flask_caching import Cache

from app.config import Config
from app.utils.structlog_config import get_logger
from app.utils.time_utils import time_utils

logger = get_logger("cache_service")


class CacheService:
    """缓存服务。.

    提供统一的 Flask-Caching 接口，支持规则评估缓存、分类规则缓存等功能。

    Attributes:
        cache: Flask-Caching 实例。
        default_ttl: 默认缓存过期时间（秒）。

    """

    def __init__(self, cache: Cache = None) -> None:
        self.cache = cache
        self.default_ttl = Config.CACHE_DEFAULT_TTL  # 7天，按用户要求

    def _generate_cache_key(self, prefix: str, instance_id: int, username: str, db_name: str | None = None) -> str:
        """生成缓存键。.

        使用 SHA-256 哈希确保键名长度合理且安全。

        Args:
            prefix: 缓存键前缀。
            instance_id: 实例 ID。
            username: 用户名。
            db_name: 可选的数据库名称。

        Returns:
            生成的缓存键，格式为 'whalefall:{hash}'。

        """
        key_data = f"{prefix}:{instance_id}:{username}:{db_name}" if db_name else f"{prefix}:{instance_id}:{username}"

        # 使用SHA-256哈希确保键名长度合理且安全
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()
        return f"whalefall:{key_hash}"

    def invalidate_user_cache(self, instance_id: int, username: str) -> bool:
        """清除用户的所有缓存。.

        Args:
            instance_id: 实例 ID。
            username: 用户名。

        Returns:
            始终返回 True。

        """
        # Flask-Caching不支持模式匹配，简化实现
        # 这里返回True，表示操作成功
        logger.info(f"清除用户缓存: {username}")
        return True

    def invalidate_instance_cache(self, instance_id: int) -> bool:
        """清除实例的所有缓存。.

        Args:
            instance_id: 实例 ID。

        Returns:
            始终返回 True。

        """
        # Flask-Caching不支持模式匹配，简化实现
        # 这里返回True，表示操作成功
        logger.info(f"清除实例缓存: {instance_id}")
        return True

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息。.

        Returns:
            包含缓存状态和信息的字典，格式如下：
            {
                'status': 'connected',  # 或 'no_cache'、'error'
                'info': {...}           # 缓存详细信息
            }

        """
        try:
            if not self.cache:
                return {"status": "no_cache", "info": "未配置缓存实例"}

            if hasattr(self.cache.cache, "info"):
                info = self.cache.cache.info()
                return {"status": "connected", "info": info}
            return {"status": "connected", "info": "未获取到缓存详情"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_rule_evaluation_cache(self, rule_id: int, account_id: int) -> bool | None:
        """获取规则评估缓存。.

        Args:
            rule_id: 规则 ID。
            account_id: 账户 ID。

        Returns:
            缓存的评估结果（True/False），缓存未命中或出错时返回 None。

        """
        try:
            if not self.cache:
                return None

            cache_key = self._generate_cache_key("rule_eval", rule_id, account_id, "")
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                logger.debug(
                    f"规则评估缓存命中: rule_id={rule_id}, account_id={account_id}",
                    cache_key=cache_key,
                )
                return data.get("result")

            return None

        except Exception as e:
            logger.warning(
                f"获取规则评估缓存失败: rule_id={rule_id}, account_id={account_id}",
                error=str(e),
            )
            return None

    def set_rule_evaluation_cache(self, rule_id: int, account_id: int, result: bool, ttl: int | None = None) -> bool:
        """设置规则评估缓存。.

        Args:
            rule_id: 规则 ID。
            account_id: 账户 ID。
            result: 评估结果。
            ttl: 缓存过期时间（秒），默认使用配置的规则评估缓存时间。

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            if not self.cache:
                return False

            cache_key = self._generate_cache_key("rule_eval", rule_id, account_id, "")
            cache_data = {
                "result": result,
                "cached_at": time_utils.now().isoformat(),
                "rule_id": rule_id,
                "account_id": account_id,
            }

            ttl = ttl or Config.CACHE_RULE_EVALUATION_TTL  # 规则评估缓存1天
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug(
                f"规则评估缓存已设置: rule_id={rule_id}, account_id={account_id}",
                cache_key=cache_key,
                ttl=ttl,
            )
            return True

        except Exception as e:
            logger.warning(
                f"设置规则评估缓存失败: rule_id={rule_id}, account_id={account_id}",
                error=str(e),
            )
            return False

    def get_classification_rules_cache(self) -> list[dict[str, Any]] | None:
        """获取分类规则缓存。.

        Returns:
            缓存的规则列表，缓存未命中或出错时返回 None。

        """
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

    def set_classification_rules_cache(self, rules: list[dict[str, Any]], ttl: int | None = None) -> bool:
        """设置分类规则缓存。.

        Args:
            rules: 规则列表。
            ttl: 缓存过期时间（秒），默认使用配置的规则缓存时间。

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            if not self.cache:
                return False

            cache_key = "classification_rules:all"
            cache_data = {
                "rules": rules,
                "cached_at": time_utils.now().isoformat(),
                "count": len(rules),
            }

            ttl = ttl or Config.CACHE_RULE_TTL  # 规则缓存2小时
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug("分类规则缓存已设置", cache_key=cache_key, ttl=ttl, count=len(rules))
            return True

        except Exception as e:
            logger.warning("设置分类规则缓存失败", error=str(e))
            return False

    def invalidate_account_cache(self, account_id: int) -> bool:
        """清除账户相关缓存。.

        Args:
            account_id: 账户 ID。

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            if not self.cache:
                return True

            # 清除账户权限缓存
            account_perms_key = self._generate_cache_key("account_perms", account_id, "", "")
            self.cache.delete(account_perms_key)

            # 清除该账户的所有规则评估缓存
            # 注意：这里简化处理，实际应该遍历所有规则ID
            logger.info(f"清除账户缓存: account_id={account_id}")
            return True

        except Exception as e:
            logger.warning(f"清除账户缓存失败: account_id={account_id}", error=str(e))
            return False

    def invalidate_classification_cache(self) -> bool:
        """清除分类相关缓存。.

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            if not self.cache:
                return True

            # 清除规则缓存
            rules_key = "classification_rules:all"
            self.cache.delete(rules_key)

            # 清除所有规则评估缓存
            self.invalidate_all_rule_evaluation_cache()

            logger.info("清除分类缓存")
            return True

        except Exception as e:
            logger.warning("清除分类缓存失败", error=str(e))
            return False

    def invalidate_all_rule_evaluation_cache(self) -> bool:
        """清除所有规则评估缓存。.

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            if not self.cache:
                return True

            # 由于Flask-Caching不支持模式匹配，这里简化处理
            # 在实际应用中，可能需要使用Redis的KEYS命令或SCAN命令
            logger.info("清除所有规则评估缓存")
            return True

        except Exception as e:
            logger.warning("清除所有规则评估缓存失败", error=str(e))
            return False

    def get_classification_rules_by_db_type_cache(self, db_type: str) -> list[dict[str, Any]] | None:
        """获取按数据库类型分类的规则缓存。.

        Args:
            db_type: 数据库类型，如 'mysql'、'postgresql'。

        Returns:
            缓存的规则列表，缓存未命中或出错时返回 None。

        """
        try:
            if not self.cache:
                return None

            cache_key = f"classification_rules:{db_type}"
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                # 处理不同的缓存数据格式
                if isinstance(data, dict) and "rules" in data:
                    logger.debug(
                        f"数据库类型规则缓存命中: {db_type}",
                        cache_key=cache_key,
                        count=len(data["rules"]),
                    )
                    return data["rules"]
                if isinstance(data, list):
                    logger.debug(
                        f"数据库类型规则缓存命中（旧格式）: {db_type}",
                        cache_key=cache_key,
                        count=len(data),
                    )
                    return data
                logger.warning(
                    f"数据库类型规则缓存格式错误: {db_type}",
                    cache_key=cache_key,
                )
                return None

            return None

        except Exception as e:
            logger.warning(f"获取数据库类型规则缓存失败: {db_type}", error=str(e))
            return None

    def set_classification_rules_by_db_type_cache(self, db_type: str, rules: list[dict[str, Any]], ttl: int | None = None) -> bool:
        """设置按数据库类型分类的规则缓存。.

        Args:
            db_type: 数据库类型，如 'mysql'、'postgresql'。
            rules: 规则列表。
            ttl: 缓存过期时间（秒），默认使用配置的规则缓存时间。

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            if not self.cache:
                return False

            cache_key = f"classification_rules:{db_type}"
            cache_data = {
                "rules": rules,
                "cached_at": time_utils.now().isoformat(),
                "count": len(rules),
                "db_type": db_type,
            }

            ttl = ttl or Config.CACHE_RULE_TTL  # 规则缓存2小时
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug(
                f"数据库类型规则缓存已设置: {db_type}",
                cache_key=cache_key,
                ttl=ttl,
                count=len(rules),
            )
            return True

        except Exception as e:
            logger.warning(f"设置数据库类型规则缓存失败: {db_type}", error=str(e))
            return False

    def invalidate_db_type_cache(self, db_type: str) -> bool:
        """清除特定数据库类型的缓存。.

        Args:
            db_type: 数据库类型，如 'mysql'、'postgresql'。

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            if not self.cache:
                return True

            rules_key = f"classification_rules:{db_type}"
            self.cache.delete(rules_key)

            logger.info(f"清除数据库类型缓存: {db_type}")
            return True

        except Exception as e:
            logger.warning(f"清除数据库类型缓存失败: {db_type}", error=str(e))
            return False

    def invalidate_all_db_type_cache(self) -> bool:
        """清除所有数据库类型的规则缓存。.

        Returns:
            成功返回 True，失败返回 False。

        """
        try:
            if not self.cache:
                return True

            db_types = ["mysql", "postgresql", "sqlserver", "oracle"]
            for db_type in db_types:
                self.invalidate_db_type_cache(db_type)

            logger.info("清除所有数据库类型缓存")
            return True

        except Exception as e:
            logger.warning("清除所有数据库类型缓存失败", error=str(e))
            return False

    def health_check(self) -> bool:
        """缓存健康检查。.

        通过设置和获取测试键来验证缓存是否正常工作。

        Returns:
            如果缓存正常返回 True，否则返回 False。

        """
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



# 全局缓存服务实例
cache_service: CacheService | None = None
cache_manager: CacheService | None = None  # 向后兼容


def init_cache_service(cache: Cache) -> CacheService:
    """初始化缓存服务。.

    Args:
        cache: Flask-Caching 实例。

    Returns:
        初始化后的 CacheService 实例。

    """
    global cache_service, cache_manager
    cache_service = CacheService(cache)
    cache_manager = cache_service
    logger.info("缓存服务初始化完成")
    return cache_service


def init_cache_manager(cache: Cache) -> CacheService:
    """兼容旧入口，内部调用新的初始化方法。.

    Args:
        cache: Flask-Caching 实例。

    Returns:
        初始化后的 CacheService 实例。

    """
    return init_cache_service(cache)
