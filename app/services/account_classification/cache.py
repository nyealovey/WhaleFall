"""账户分类规则缓存访问器."""

from __future__ import annotations

from typing import cast

from flask import current_app, has_app_context

from app.settings import DEFAULT_CACHE_RULE_TTL_SECONDS
from app.utils.cache_utils import CacheManagerRegistry

_CLASSIFICATION_RULES_ALL_KEY = "classification_rules:all"


def _rule_ttl_seconds() -> int:
    if has_app_context():
        value = current_app.config.get("CACHE_RULE_TTL", DEFAULT_CACHE_RULE_TTL_SECONDS)
        return int(value)
    return DEFAULT_CACHE_RULE_TTL_SECONDS


class ClassificationCache:
    """分类规则缓存封装."""

    def get_rules(self) -> list[dict] | None:
        """读取全部启用分类规则缓存."""
        cached = CacheManagerRegistry.get().get(_CLASSIFICATION_RULES_ALL_KEY)
        if cached is None:
            return None
        if isinstance(cached, list):
            return cast(list[dict], cached)
        if isinstance(cached, dict):
            rules = cached.get("rules")
            if isinstance(rules, list):
                return cast(list[dict], rules)
        return None

    def set_rules(self, rules: list[dict]) -> bool:
        """写入全部启用分类规则缓存."""
        return CacheManagerRegistry.get().set(
            _CLASSIFICATION_RULES_ALL_KEY,
            {"rules": rules},
            timeout=_rule_ttl_seconds(),
        )

    def invalidate_all(self) -> bool:
        """清除全部分类规则缓存."""
        return CacheManagerRegistry.get().delete(_CLASSIFICATION_RULES_ALL_KEY)

    def invalidate_db_type(self, db_type: str) -> bool:
        """按数据库类型清理分类缓存.

        当前分类规则缓存只保留全量 key,定向清理同样删除全量 key 以保持对外语义。
        """
        del db_type
        return self.invalidate_all()
