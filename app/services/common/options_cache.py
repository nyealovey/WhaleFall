"""通用下拉/筛选项缓存访问器.

目标：
- 为“读多写少”的 options 类数据提供统一短 TTL 缓存
- 固定 key（可枚举），避免 scan/keys 之类的模式删除
- 默认通过 `CacheManagerRegistry` 获取缓存能力；未初始化时视为“未启用缓存”
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from flask import current_app, has_app_context

from app.settings import DEFAULT_CACHE_OPTIONS_TTL_SECONDS
from app.utils.cache_utils import CacheManager, CacheManagerRegistry

if TYPE_CHECKING:
    from app.core.types.common_filter_options import CommonDatabasesOptionsFilters

_OPTIONS_KEY_PREFIX = "whalefall:v1:options"


def _normalize_optional_str(value: str | None, *, default: str) -> str:
    if value is None:
        return default
    cleaned = value.strip()
    if not cleaned:
        return default
    return cleaned.lower()


class OptionsCache:
    """Options 缓存访问器（短 TTL + 固定 key）。"""

    def __init__(self, *, manager: CacheManager | None = None) -> None:
        self._manager = manager

    def _get_manager(self) -> CacheManager | None:
        if self._manager is not None:
            return self._manager
        try:
            return CacheManagerRegistry.get()
        except RuntimeError:
            return None

    @staticmethod
    def _get_ttl_seconds() -> int:
        if has_app_context():
            ttl_raw = current_app.config.get("CACHE_OPTIONS_TTL")
            if isinstance(ttl_raw, int) and ttl_raw >= 0:
                return ttl_raw
        return DEFAULT_CACHE_OPTIONS_TTL_SECONDS

    # ---- Keys -----------------------------------------------------------
    @staticmethod
    def _key_active_tags() -> str:
        return f"{_OPTIONS_KEY_PREFIX}:tags:active"

    @staticmethod
    def _key_tag_categories() -> str:
        return f"{_OPTIONS_KEY_PREFIX}:tag-categories:active"

    @staticmethod
    def _key_classifications() -> str:
        return f"{_OPTIONS_KEY_PREFIX}:classifications:active"

    @staticmethod
    def _key_instance_select_options(db_type: str | None) -> str:
        normalized = _normalize_optional_str(db_type, default="all")
        return f"{_OPTIONS_KEY_PREFIX}:instances-select:{normalized}"

    @staticmethod
    def _key_database_select_options(instance_id: int) -> str:
        return f"{_OPTIONS_KEY_PREFIX}:databases-select:{instance_id}"

    @staticmethod
    def _key_common_instances_options(db_type: str | None) -> str:
        normalized = _normalize_optional_str(db_type, default="all")
        return f"{_OPTIONS_KEY_PREFIX}:instances-common:{normalized}"

    @staticmethod
    def _key_common_databases_options(filters: "CommonDatabasesOptionsFilters") -> str:
        return f"{_OPTIONS_KEY_PREFIX}:databases-common:{filters.instance_id}:{filters.limit}:{filters.offset}"

    # ---- Get/Set helpers ------------------------------------------------
    def get_active_tag_options(self) -> list[dict[str, str]] | None:
        manager = self._get_manager()
        if not manager:
            return None
        cached = manager.get(self._key_active_tags())
        return cast("list[dict[str, str]] | None", cached) if isinstance(cached, list) else None

    def set_active_tag_options(self, options: list[dict[str, str]]) -> bool:
        manager = self._get_manager()
        if not manager:
            return False
        return manager.set(self._key_active_tags(), options, timeout=self._get_ttl_seconds())

    def get_tag_categories(self) -> list[dict[str, str]] | None:
        manager = self._get_manager()
        if not manager:
            return None
        cached = manager.get(self._key_tag_categories())
        return cast("list[dict[str, str]] | None", cached) if isinstance(cached, list) else None

    def set_tag_categories(self, options: list[dict[str, str]]) -> bool:
        manager = self._get_manager()
        if not manager:
            return False
        return manager.set(self._key_tag_categories(), options, timeout=self._get_ttl_seconds())

    def get_classification_options(self) -> list[dict[str, str]] | None:
        manager = self._get_manager()
        if not manager:
            return None
        cached = manager.get(self._key_classifications())
        return cast("list[dict[str, str]] | None", cached) if isinstance(cached, list) else None

    def set_classification_options(self, options: list[dict[str, str]]) -> bool:
        manager = self._get_manager()
        if not manager:
            return False
        return manager.set(self._key_classifications(), options, timeout=self._get_ttl_seconds())

    def get_instance_select_options(self, db_type: str | None) -> list[dict[str, str]] | None:
        manager = self._get_manager()
        if not manager:
            return None
        cached = manager.get(self._key_instance_select_options(db_type))
        return cast("list[dict[str, str]] | None", cached) if isinstance(cached, list) else None

    def set_instance_select_options(self, db_type: str | None, options: list[dict[str, str]]) -> bool:
        manager = self._get_manager()
        if not manager:
            return False
        return manager.set(self._key_instance_select_options(db_type), options, timeout=self._get_ttl_seconds())

    def get_database_select_options(self, instance_id: int) -> list[dict[str, str]] | None:
        manager = self._get_manager()
        if not manager:
            return None
        cached = manager.get(self._key_database_select_options(instance_id))
        return cast("list[dict[str, str]] | None", cached) if isinstance(cached, list) else None

    def set_database_select_options(self, instance_id: int, options: list[dict[str, str]]) -> bool:
        manager = self._get_manager()
        if not manager:
            return False
        return manager.set(self._key_database_select_options(instance_id), options, timeout=self._get_ttl_seconds())

    def get_common_instances_options(self, db_type: str | None) -> list[dict[str, Any]] | None:
        manager = self._get_manager()
        if not manager:
            return None
        cached = manager.get(self._key_common_instances_options(db_type))
        return cast("list[dict[str, Any]] | None", cached) if isinstance(cached, list) else None

    def set_common_instances_options(self, db_type: str | None, items: list[dict[str, Any]]) -> bool:
        manager = self._get_manager()
        if not manager:
            return False
        return manager.set(self._key_common_instances_options(db_type), items, timeout=self._get_ttl_seconds())

    def get_common_databases_options(self, filters: "CommonDatabasesOptionsFilters") -> dict[str, Any] | None:
        manager = self._get_manager()
        if not manager:
            return None
        cached = manager.get(self._key_common_databases_options(filters))
        return cast("dict[str, Any] | None", cached) if isinstance(cached, dict) else None

    def set_common_databases_options(self, filters: "CommonDatabasesOptionsFilters", payload: dict[str, Any]) -> bool:
        manager = self._get_manager()
        if not manager:
            return False
        return manager.set(self._key_common_databases_options(filters), payload, timeout=self._get_ttl_seconds())
