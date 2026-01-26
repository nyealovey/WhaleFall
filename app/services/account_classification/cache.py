"""账户分类缓存辅助工具."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from flask import current_app, has_app_context

from app.schemas.cache_actions import CLASSIFICATION_DB_TYPES
from app.settings import DEFAULT_CACHE_RULE_TTL_SECONDS
from app.utils.cache_utils import CacheManager, CacheManagerRegistry
from app.utils.structlog_config import log_error
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from app.core.types import JsonDict, JsonValue


_CLASSIFICATION_RULES_ALL_KEY = "classification_rules:all"


def _classification_rules_key_by_db_type(db_type: str) -> str:
    return f"classification_rules:{db_type}"


class ClassificationCache:
    """针对分类业务封装的缓存访问器."""

    def __init__(self, manager: CacheManager | None = None) -> None:
        """构造缓存访问器.

        Args:
            manager: 注入的缓存管理器；缺省时尝试使用 `CacheManagerRegistry`。

        """
        self.manager = manager

    def _get_manager(self) -> CacheManager | None:
        if self.manager is not None:
            return self.manager
        try:
            return CacheManagerRegistry.get()
        except RuntimeError:
            # 允许在 app 初始化前被构造（例如单元测试），此时视为“未启用缓存”。
            return None

    @staticmethod
    def _get_rule_ttl_seconds() -> int:
        if has_app_context():
            ttl_raw = current_app.config.get("CACHE_RULE_TTL")
            if isinstance(ttl_raw, int) and ttl_raw >= 0:
                return ttl_raw
        return DEFAULT_CACHE_RULE_TTL_SECONDS

    # ---- Rules cache -----------------------------------------------------
    def get_rules(self) -> list["JsonDict"] | None:
        """返回缓存中的分类规则数据.

        Returns:
            list[dict[str, Any]] | None: 命中缓存时返回规则列表,否则返回 None.

        """
        manager = self._get_manager()
        if not manager:
            return None

        cached_raw = cast("dict[str, object] | list[JsonDict] | None", manager.get(_CLASSIFICATION_RULES_ALL_KEY))
        if not cached_raw:
            return None

        if isinstance(cached_raw, dict) and "rules" in cached_raw:
            rules = cached_raw.get("rules")
            if isinstance(rules, list):
                return [cast("JsonDict", rule) for rule in rules]

        log_error("分类规则缓存格式无效", module="account_classification_cache")
        return None

    def set_rules(self, rules_data: "Iterable[Mapping[str, JsonValue]]") -> bool:
        """写入分类规则缓存.

        Args:
            rules_data: 需要缓存的规则可迭代对象.

        Returns:
            bool: 写入成功返回 True,数据为空或写入失败返回 False.

        """
        manager = self._get_manager()
        if not manager:
            return False

        payload = [dict(rule) for rule in rules_data]
        if not payload:
            return False

        cache_data = {
            "rules": payload,
            "cached_at": time_utils.now().isoformat(),
            "count": len(payload),
        }
        return manager.set(_CLASSIFICATION_RULES_ALL_KEY, cache_data, timeout=self._get_rule_ttl_seconds())

    # ---- Invalidation helpers -------------------------------------------
    def invalidate_all(self) -> bool:
        """清空全部分类缓存数据.

        Returns:
            bool: 成功执行失效操作时为 True,否则 False.

        """
        manager = self._get_manager()
        if not manager:
            return False

        ok = manager.delete(_CLASSIFICATION_RULES_ALL_KEY)
        for db_type in CLASSIFICATION_DB_TYPES:
            ok = manager.delete(_classification_rules_key_by_db_type(db_type)) and ok
        return ok

    def invalidate_db_type(self, db_type: str) -> bool:
        """按数据库类型清空规则缓存.

        Args:
            db_type: 需要刷新缓存的数据库类型.

        Returns:
            bool: 缓存存在且成功失效时为 True.

        """
        manager = self._get_manager()
        if not manager:
            return False
        # 当前分类规则读取仅依赖全量 key（`classification_rules:all`）。
        # db_type 定向清理为了保持对外语义可用，选择同时清理全量 key，确保后续读取可回源更新。
        ok = manager.delete(_CLASSIFICATION_RULES_ALL_KEY)
        return manager.delete(_classification_rules_key_by_db_type(db_type)) and ok
