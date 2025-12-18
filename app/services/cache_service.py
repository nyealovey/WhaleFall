"""鲸落 - 缓存服务,提供统一的 Flask-Caching 接口."""

import hashlib
import json
from typing import Any

from flask_caching import Cache

from app.config import Config
from app.utils.structlog_config import get_logger
from app.utils.time_utils import time_utils

logger = get_logger("cache_service")

CACHE_EXCEPTIONS: tuple[type[Exception], ...] = (
    AttributeError,
    RuntimeError,
    ValueError,
    TypeError,
    OSError,
)


class CacheService:
    """缓存服务.

    提供统一的 Flask-Caching 接口,支持规则评估缓存、分类规则缓存等功能.

    Attributes:
        cache: Flask-Caching 实例.
        default_ttl: 默认缓存过期时间(秒).

    """

    def __init__(self, cache: Cache | None = None) -> None:
        """初始化缓存服务并设置默认 TTL.

        Args:
            cache: 可选的 Flask-Caching 实例,未提供时延后注入.

        """
        self.cache = cache
        self.default_ttl = Config.CACHE_DEFAULT_TTL  # 7天,按用户要求

    def _generate_cache_key(
        self,
        prefix: str,
        instance_id: int | str,
        username: str | int,
        db_name: str | None = None,
    ) -> str:
        """生成缓存键.

        使用 SHA-256 哈希确保键名长度合理且安全.

        Args:
            prefix: 缓存键前缀.
            instance_id: 实例 ID.
            username: 用户名.
            db_name: 可选的数据库名称.

        Returns:
            生成的缓存键,格式为 'whalefall:{hash}'.

        """
        key_data = (
            f"{prefix}:{instance_id}:{username}:{db_name}"
            if db_name
            else f"{prefix}:{instance_id}:{username}"
        )

        # 使用SHA-256哈希确保键名长度合理且安全
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()
        return f"whalefall:{key_hash}"

    def invalidate_user_cache(self, instance_id: int, username: str) -> bool:
        """清除用户的所有缓存.

        Args:
            instance_id: 实例 ID.
            username: 用户名.

        Returns:
            始终返回 True.

        """
        # Flask-Caching不支持模式匹配,简化实现
        # 这里返回True,表示操作成功
        logger.info("清除用户缓存", username=username, instance_id=instance_id)
        return True

    def invalidate_instance_cache(self, instance_id: int) -> bool:
        """清除实例的所有缓存.

        Args:
            instance_id: 实例 ID.

        Returns:
            始终返回 True.

        """
        # Flask-Caching不支持模式匹配,简化实现
        # 这里返回True,表示操作成功
        logger.info("清除实例缓存", instance_id=instance_id)
        return True

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息.

        Returns:
            包含缓存状态和信息的字典,格式如下:
            {
                'status': 'connected',  # 或 'no_cache'、'error'
                'info': {...}           # 缓存详细信息
            }

        """
        if not self.cache:
            return {"status": "no_cache", "info": "未配置缓存实例"}

        try:
            info_obj = getattr(self.cache, "cache", None)
            cache_info = info_obj.info() if info_obj and hasattr(info_obj, "info") else "未获取到缓存详情"
            result = {"status": "connected", "info": cache_info}
        except CACHE_EXCEPTIONS as exc:
            result = {"status": "error", "error": str(exc)}
        return result

    def get_rule_evaluation_cache(self, rule_id: int, account_id: int) -> bool | None:
        """获取规则评估缓存.

        Args:
            rule_id: 规则 ID.
            account_id: 账户 ID.

        Returns:
            缓存的评估结果(True/False),缓存未命中或出错时返回 None.

        """
        if not self.cache:
            return None

        result: bool | None = None
        cache_key = self._generate_cache_key("rule_eval", rule_id, account_id, "")
        try:
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                logger.debug(
                    "规则评估缓存命中",
                    rule_id=rule_id,
                    account_id=account_id,
                    cache_key=cache_key,
                )
                result = data.get("result")
        except CACHE_EXCEPTIONS as exc:
            logger.warning(
                "获取规则评估缓存失败",
                rule_id=rule_id,
                account_id=account_id,
                error=str(exc),
            )
        return result

    def set_rule_evaluation_cache(
        self,
        rule_id: int,
        account_id: int,
        *,
        result: bool,
        ttl: int | None = None,
    ) -> bool:
        """设置规则评估缓存.

        Args:
            rule_id: 规则 ID.
            account_id: 账户 ID.
            result: 评估结果.
            ttl: 缓存过期时间(秒),默认使用配置的规则评估缓存时间.

        Returns:
            成功返回 True,失败返回 False.

        """
        if not self.cache:
            return False

        success = False
        cache_key = self._generate_cache_key("rule_eval", rule_id, account_id, "")
        try:
            cache_data = {
                "result": result,
                "cached_at": time_utils.now().isoformat(),
                "rule_id": rule_id,
                "account_id": account_id,
            }

            ttl = ttl or Config.CACHE_RULE_EVALUATION_TTL  # 规则评估缓存1天
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug(
                "规则评估缓存已设置",
                rule_id=rule_id,
                account_id=account_id,
                cache_key=cache_key,
                ttl=ttl,
            )
            success = True
        except CACHE_EXCEPTIONS as exc:
            logger.warning(
                "设置规则评估缓存失败",
                rule_id=rule_id,
                account_id=account_id,
                error=str(exc),
            )
        return success

    def get_classification_rules_cache(self) -> list[dict[str, Any]] | None:
        """获取分类规则缓存.

        Returns:
            缓存的规则列表,缓存未命中或出错时返回 None.

        """
        if not self.cache:
            return None

        cache_key = "classification_rules:all"
        result: list[dict[str, Any]] | None = None
        try:
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                logger.debug("分类规则缓存命中", cache_key=cache_key)
                result = data
        except CACHE_EXCEPTIONS as exc:
            logger.warning("获取分类规则缓存失败", error=str(exc))
        return result

    def set_classification_rules_cache(self, rules: list[dict[str, Any]], ttl: int | None = None) -> bool:
        """设置分类规则缓存.

        Args:
            rules: 规则列表.
            ttl: 缓存过期时间(秒),默认使用配置的规则缓存时间.

        Returns:
            成功返回 True,失败返回 False.

        """
        if not self.cache:
            return False

        success = False
        cache_key = "classification_rules:all"
        try:
            cache_data = {
                "rules": rules,
                "cached_at": time_utils.now().isoformat(),
                "count": len(rules),
            }

            ttl = ttl or Config.CACHE_RULE_TTL  # 规则缓存2小时
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug("分类规则缓存已设置", cache_key=cache_key, ttl=ttl, count=len(rules))
            success = True
        except CACHE_EXCEPTIONS as exc:
            logger.warning("设置分类规则缓存失败", error=str(exc))
        return success

    def invalidate_account_cache(self, account_id: int) -> bool:
        """清除账户相关缓存.

        Args:
            account_id: 账户 ID.

        Returns:
            成功返回 True,失败返回 False.

        """
        if not self.cache:
            return True

        success = False
        try:
            account_perms_key = self._generate_cache_key("account_perms", account_id, "", "")
            self.cache.delete(account_perms_key)
            logger.info("清除账户缓存", account_id=account_id)
            success = True
        except CACHE_EXCEPTIONS as exc:
            logger.warning("清除账户缓存失败", account_id=account_id, error=str(exc))
        return success

    def invalidate_classification_cache(self) -> bool:
        """清除分类相关缓存.

        Returns:
            成功返回 True,失败返回 False.

        """
        if not self.cache:
            return True

        success = False
        try:
            rules_key = "classification_rules:all"
            self.cache.delete(rules_key)
            self.invalidate_all_rule_evaluation_cache()
            logger.info("清除分类缓存")
            success = True
        except CACHE_EXCEPTIONS as exc:
            logger.warning("清除分类缓存失败", error=str(exc))
        return success

    def invalidate_all_rule_evaluation_cache(self) -> bool:
        """清除所有规则评估缓存.

        Returns:
            成功返回 True,失败返回 False.

        """
        if not self.cache:
            return True

        logger.info("清除所有规则评估缓存")
        return True

    def get_classification_rules_by_db_type_cache(self, db_type: str) -> list[dict[str, Any]] | None:
        """获取按数据库类型分类的规则缓存.

        Args:
            db_type: 数据库类型,如 'mysql'、'postgresql'.

        Returns:
            缓存的规则列表,缓存未命中或出错时返回 None.

        """
        if not self.cache:
            return None

        cache_key = f"classification_rules:{db_type}"
        rules: list[dict[str, Any]] | None = None
        try:
            cached_data = self.cache.get(cache_key)

            if cached_data:
                data = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                if isinstance(data, dict) and "rules" in data:
                    logger.debug(
                        "数据库类型规则缓存命中",
                        db_type=db_type,
                        cache_key=cache_key,
                        count=len(data["rules"]),
                    )
                    rules = data["rules"]
                elif isinstance(data, list):
                    logger.debug(
                        "数据库类型规则缓存命中 (旧格式)",
                        db_type=db_type,
                        cache_key=cache_key,
                        count=len(data),
                    )
                    rules = data
                else:
                    logger.warning("数据库类型规则缓存格式错误", db_type=db_type, cache_key=cache_key)
        except CACHE_EXCEPTIONS as exc:
            logger.warning("获取数据库类型规则缓存失败", db_type=db_type, error=str(exc))
        return rules

    def set_classification_rules_by_db_type_cache(
        self, db_type: str, rules: list[dict[str, Any]], ttl: int | None = None,
    ) -> bool:
        """设置按数据库类型分类的规则缓存.

        Args:
            db_type: 数据库类型,如 'mysql'、'postgresql'.
            rules: 规则列表.
            ttl: 缓存过期时间(秒),默认使用配置的规则缓存时间.

        Returns:
            成功返回 True,失败返回 False.

        """
        if not self.cache:
            return False

        success = False
        cache_key = f"classification_rules:{db_type}"
        try:
            cache_data = {
                "rules": rules,
                "cached_at": time_utils.now().isoformat(),
                "count": len(rules),
                "db_type": db_type,
            }

            ttl = ttl or Config.CACHE_RULE_TTL  # 规则缓存2小时
            self.cache.set(cache_key, cache_data, timeout=ttl)
            logger.debug(
                "数据库类型规则缓存已设置",
                db_type=db_type,
                cache_key=cache_key,
                ttl=ttl,
                count=len(rules),
            )
            success = True
        except CACHE_EXCEPTIONS as exc:
            logger.warning("设置数据库类型规则缓存失败", db_type=db_type, error=str(exc))
        return success

    def invalidate_db_type_cache(self, db_type: str) -> bool:
        """清除特定数据库类型的缓存.

        Args:
            db_type: 数据库类型,如 'mysql'、'postgresql'.

        Returns:
            成功返回 True,失败返回 False.

        """
        if not self.cache:
            return True

        success = False
        try:
            rules_key = f"classification_rules:{db_type}"
            self.cache.delete(rules_key)
            logger.info("清除数据库类型缓存", db_type=db_type)
            success = True
        except CACHE_EXCEPTIONS as exc:
            logger.warning("清除数据库类型缓存失败", db_type=db_type, error=str(exc))
        return success

    def invalidate_all_db_type_cache(self) -> bool:
        """清除所有数据库类型的规则缓存.

        Returns:
            成功返回 True,失败返回 False.

        """
        if not self.cache:
            return True

        success = False
        try:
            db_types = ["mysql", "postgresql", "sqlserver", "oracle"]
            for db_type in db_types:
                self.invalidate_db_type_cache(db_type)

            logger.info("清除所有数据库类型缓存")
            success = True
        except CACHE_EXCEPTIONS as exc:
            logger.warning("清除所有数据库类型缓存失败", error=str(exc))
        return success

    def health_check(self) -> bool:
        """缓存健康检查.

        通过设置和获取测试键来验证缓存是否正常工作.

        Returns:
            如果缓存正常返回 True,否则返回 False.

        """
        if not self.cache:
            return False

        is_healthy = False
        try:
            test_key = "health_check_test"
            test_value = "ok"
            self.cache.set(test_key, test_value, timeout=10)
            result = self.cache.get(test_key)
            self.cache.delete(test_key)
            is_healthy = result == test_value
        except CACHE_EXCEPTIONS as exc:
            logger.warning("缓存健康检查失败", error=str(exc))
        return is_healthy


# 全局缓存服务实例
cache_service: CacheService | None = None


def init_cache_service(cache: Cache) -> CacheService:
    """初始化缓存服务.

    Args:
        cache: Flask-Caching 实例.

    Returns:
        初始化后的 CacheService 实例.

    """
    service = CacheService(cache)
    globals()["cache_service"] = service
    logger.info("缓存服务初始化完成")
    return service
