"""通用筛选器选项缓存访问器."""

from __future__ import annotations

from typing import Any, cast

from flask import current_app, has_app_context

from app.core.types.common_filter_options import CommonDatabasesOptionsFilters
from app.settings import DEFAULT_CACHE_OPTIONS_TTL_SECONDS
from app.utils.cache_utils import CacheManagerRegistry

OptionList = list[dict[str, str]]
CommonInstanceOptionPayload = list[dict[str, object]]
CommonDatabasesOptionPayload = dict[str, object]

_ACTIVE_TAG_OPTIONS_KEY = "filter_options:active_tags"
_TAG_CATEGORIES_KEY = "filter_options:tag_categories"
_CLASSIFICATION_OPTIONS_KEY = "filter_options:classifications"
_INSTANCE_SELECT_PREFIX = "filter_options:instance_select"
_DATABASE_SELECT_PREFIX = "filter_options:database_select"
_COMMON_INSTANCES_PREFIX = "filter_options:common_instances"
_COMMON_DATABASES_PREFIX = "filter_options:common_databases"


def _options_ttl_seconds() -> int:
    if has_app_context():
        value = current_app.config.get("CACHE_OPTIONS_TTL", DEFAULT_CACHE_OPTIONS_TTL_SECONDS)
        return int(value)
    return DEFAULT_CACHE_OPTIONS_TTL_SECONDS


def _normalize_db_type(db_type: str | list[str] | None) -> tuple[str, ...]:
    if db_type is None:
        return ()
    if isinstance(db_type, str):
        normalized = db_type.strip().lower()
        return (normalized,) if normalized else ()
    return tuple(sorted({item.strip().lower() for item in db_type if item.strip()}))


class OptionsCache:
    """FilterOptionsService 使用的短 TTL 缓存封装."""

    def _get(self, key: str) -> object | None:
        return CacheManagerRegistry.get().get(key)

    def _set(self, key: str, value: object) -> bool:
        return CacheManagerRegistry.get().set(key, value, timeout=_options_ttl_seconds())

    @staticmethod
    def _build_key(prefix: str, *args: object, **kwargs: object) -> str:
        return CacheManagerRegistry.get().build_key(prefix, *args, **kwargs)

    def get_active_tag_options(self) -> OptionList | None:
        """读取启用标签选项缓存."""
        return cast(OptionList | None, self._get(_ACTIVE_TAG_OPTIONS_KEY))

    def set_active_tag_options(self, options: OptionList) -> bool:
        """写入启用标签选项缓存."""
        return self._set(_ACTIVE_TAG_OPTIONS_KEY, options)

    def get_tag_categories(self) -> OptionList | None:
        """读取标签分类选项缓存."""
        return cast(OptionList | None, self._get(_TAG_CATEGORIES_KEY))

    def set_tag_categories(self, options: OptionList) -> bool:
        """写入标签分类选项缓存."""
        return self._set(_TAG_CATEGORIES_KEY, options)

    def get_classification_options(self) -> OptionList | None:
        """读取账户分类选项缓存."""
        return cast(OptionList | None, self._get(_CLASSIFICATION_OPTIONS_KEY))

    def set_classification_options(self, options: OptionList) -> bool:
        """写入账户分类选项缓存."""
        return self._set(_CLASSIFICATION_OPTIONS_KEY, options)

    def _instance_select_key(self, db_type: str | list[str] | None) -> str:
        return self._build_key(_INSTANCE_SELECT_PREFIX, db_type=_normalize_db_type(db_type))

    def get_instance_select_options(self, db_type: str | list[str] | None) -> OptionList | None:
        """读取实例下拉选项缓存."""
        return cast(OptionList | None, self._get(self._instance_select_key(db_type)))

    def set_instance_select_options(self, db_type: str | list[str] | None, options: OptionList) -> bool:
        """写入实例下拉选项缓存."""
        return self._set(self._instance_select_key(db_type), options)

    def _database_select_key(self, instance_id: int) -> str:
        return self._build_key(_DATABASE_SELECT_PREFIX, instance_id=int(instance_id))

    def get_database_select_options(self, instance_id: int) -> OptionList | None:
        """读取数据库下拉选项缓存."""
        return cast(OptionList | None, self._get(self._database_select_key(instance_id)))

    def set_database_select_options(self, instance_id: int, options: OptionList) -> bool:
        """写入数据库下拉选项缓存."""
        return self._set(self._database_select_key(instance_id), options)

    def _common_instances_key(self, db_type: str | list[str] | None) -> str:
        return self._build_key(_COMMON_INSTANCES_PREFIX, db_type=_normalize_db_type(db_type))

    def get_common_instances_options(self, db_type: str | list[str] | None) -> CommonInstanceOptionPayload | None:
        """读取 Common API 实例选项缓存."""
        return cast(CommonInstanceOptionPayload | None, self._get(self._common_instances_key(db_type)))

    def set_common_instances_options(
        self,
        db_type: str | list[str] | None,
        options: CommonInstanceOptionPayload,
    ) -> bool:
        """写入 Common API 实例选项缓存."""
        return self._set(self._common_instances_key(db_type), options)

    def _common_databases_key(self, filters: CommonDatabasesOptionsFilters) -> str:
        return self._build_key(
            _COMMON_DATABASES_PREFIX,
            instance_id=int(filters.instance_id),
            limit=int(filters.limit),
            offset=int(filters.offset),
        )

    def get_common_databases_options(
        self,
        filters: CommonDatabasesOptionsFilters,
    ) -> CommonDatabasesOptionPayload | None:
        """读取 Common API 数据库选项缓存."""
        return cast(CommonDatabasesOptionPayload | None, self._get(self._common_databases_key(filters)))

    def set_common_databases_options(
        self,
        filters: CommonDatabasesOptionsFilters,
        options: CommonDatabasesOptionPayload,
    ) -> bool:
        """写入 Common API 数据库选项缓存."""
        sanitized: dict[str, Any] = dict(options)
        return self._set(self._common_databases_key(filters), sanitized)
