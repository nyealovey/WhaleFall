"""账户分类缓存辅助工具."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.services.cache_service import CacheService, cache_manager
from app.utils.structlog_config import log_error

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from app.types import JsonDict, JsonValue


class ClassificationCache:
    """针对分类业务封装的缓存访问器."""

    def __init__(self, manager: CacheService | None = None) -> None:
        """构造缓存访问器.

        Args:
            manager: 注入的缓存管理器,缺省使用全局 `cache_manager`.

        """
        self.manager = manager or cache_manager

    # ---- Rules cache -----------------------------------------------------
    def get_rules(self) -> list[JsonDict] | None:
        """返回缓存中的分类规则数据.

        Returns:
            list[dict[str, Any]] | None: 命中缓存时返回规则列表,否则返回 None.

        """
        if not self.manager:
            return None
        cached_raw = cast(
            "dict[str, object] | list[JsonDict] | None",
            self.manager.get_classification_rules_cache(),
        )
        cached = cached_raw
        if not cached:
            return None
        if isinstance(cached, dict) and "rules" in cached:
            rules = cached.get("rules")
            if isinstance(rules, list):
                return [cast("JsonDict", rule) for rule in rules]
        if isinstance(cached, list):
            return cached  # type: ignore[return-value]
        log_error("分类规则缓存格式无效", module="account_classification_cache")
        return None

    def set_rules(self, rules_data: Iterable[Mapping[str, JsonValue]]) -> bool:
        """写入分类规则缓存.

        Args:
            rules_data: 需要缓存的规则可迭代对象.

        Returns:
            bool: 写入成功返回 True,数据为空或写入失败返回 False.

        """
        if not self.manager:
            return False
        payload = [dict(rule) for rule in rules_data]
        if not payload:
            return False
        return self.manager.set_classification_rules_cache(payload)

    # ---- Rules cache (per db type) --------------------------------------
    def set_rules_by_db_type(self, db_type: str, rules: Iterable[Mapping[str, JsonValue]]) -> bool:
        """写入指定数据库类型的分类规则缓存.

        Args:
            db_type: 数据库类型标识,例如 mysql、postgres.
            rules: 分类规则列表,将持久化到缓存.

        Returns:
            bool: 写入成功返回 True,失败返回 False.

        """
        if not self.manager:
            return False
        normalized_rules = [dict(rule) for rule in rules]
        if not normalized_rules:
            return False
        return self.manager.set_classification_rules_by_db_type_cache(db_type, normalized_rules)

    # ---- Invalidation helpers -------------------------------------------
    def invalidate_all(self) -> bool:
        """清空全部分类缓存数据.

        Returns:
            bool: 成功执行失效操作时为 True,否则 False.

        """
        if not self.manager:
            return False
        self.manager.invalidate_classification_cache()
        self.manager.invalidate_all_db_type_cache()
        return True

    def invalidate_db_type(self, db_type: str) -> bool:
        """按数据库类型清空规则缓存.

        Args:
            db_type: 需要刷新缓存的数据库类型.

        Returns:
            bool: 缓存存在且成功失效时为 True.

        """
        if not self.manager:
            return False
        self.manager.invalidate_db_type_cache(db_type)
        return True
