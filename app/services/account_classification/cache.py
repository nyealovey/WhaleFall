"""账户分类缓存辅助工具。"""

from __future__ import annotations

from typing import Any, Iterable

from app.services.cache_service import cache_manager
from app.utils.structlog_config import log_error


class ClassificationCache:
    """针对分类业务封装的缓存访问器。"""

    def __init__(self, manager: Any | None = None) -> None:  # noqa: ANN401
        self.manager = manager or cache_manager

    # ---- Rules cache -----------------------------------------------------
    def get_rules(self) -> list[dict[str, Any]] | None:
        """返回缓存中的分类规则数据。"""
        if not self.manager:
            return None
        cached = self.manager.get_classification_rules_cache()
        if not cached:
            return None
        if isinstance(cached, dict) and "rules" in cached:
            return cached["rules"]
        if isinstance(cached, list):
            return cached
        log_error("分类规则缓存格式无效", module="account_classification_cache")
        return None

    def set_rules(self, rules_data: Iterable[dict[str, Any]]) -> bool:
        """写入分类规则缓存。"""
        if not self.manager:
            return False
        payload = list(rules_data)
        if not payload:
            return False
        return self.manager.set_classification_rules_cache(payload)

    # ---- Rules cache (per db type) --------------------------------------
    def set_rules_by_db_type(self, db_type: str, rules: Iterable[dict[str, Any]]) -> bool:
        """写入指定数据库类型的分类规则缓存。

        Args:
            db_type: 数据库类型标识，例如 mysql、postgres。
            rules: 分类规则列表，将持久化到缓存。

        Returns:
            bool: 写入成功返回 True，失败返回 False。
        """

        if not self.manager:
            return False
        return self.manager.set_classification_rules_by_db_type_cache(db_type, list(rules))

    # ---- Invalidation helpers -------------------------------------------
    def invalidate_all(self) -> bool:
        """清空全部分类缓存数据。

        Returns:
            bool: 成功执行失效操作时为 True，否则 False。
        """

        if not self.manager:
            return False
        self.manager.invalidate_classification_cache()
        self.manager.invalidate_all_db_type_cache()
        return True

    def invalidate_db_type(self, db_type: str) -> bool:
        """按数据库类型清空规则缓存。

        Args:
            db_type: 需要刷新缓存的数据库类型。

        Returns:
            bool: 缓存存在且成功失效时为 True。
        """

        if not self.manager:
            return False
        self.manager.invalidate_db_type_cache(db_type)
        return True
