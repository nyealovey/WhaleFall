"""通用筛选器/下拉选项 Service.

覆盖:
- Common API 的 instances/databases/dbtypes options
- 多页面复用的标签/分类/实例/数据库下拉选项
"""

from __future__ import annotations

from typing import cast

from app.core.types.common_filter_options import (
    CommonDatabaseOptionItem,
    CommonDatabasesOptionsFilters,
    CommonDatabasesOptionsResult,
    CommonInstanceOptionItem,
    CommonInstancesOptionsResult,
)
from app.repositories.filter_options_repository import FilterOptionsRepository
from app.utils.query_filter_utils import (
    build_classification_options,
    build_database_select_options,
    build_instance_select_options,
    build_key_value_options,
    build_tag_options,
)

from .options_cache import OptionsCache


class FilterOptionsService:
    """筛选器选项读取服务."""

    def __init__(
        self,
        repository: FilterOptionsRepository | None = None,
        *,
        options_cache: OptionsCache | None = None,
    ) -> None:
        """初始化筛选器选项服务."""
        self._repository = repository or FilterOptionsRepository()
        self._options_cache = options_cache or OptionsCache()

    def list_active_tag_options(self) -> list[dict[str, str]]:
        """获取启用的标签选项."""
        cached = self._options_cache.get_active_tag_options()
        if cached is not None:
            return cached
        tags = self._repository.list_active_tags()
        options = build_tag_options(tags)
        self._options_cache.set_active_tag_options(options)
        return options

    def list_tag_categories(self) -> list[dict[str, str]]:
        """获取标签分类选项."""
        cached = self._options_cache.get_tag_categories()
        if cached is not None:
            return cached
        categories_raw = self._repository.list_active_tag_categories()
        options = build_key_value_options(categories_raw)
        self._options_cache.set_tag_categories(options)
        return options

    def list_classification_options(self) -> list[dict[str, str]]:
        """获取账户分类选项."""
        cached = self._options_cache.get_classification_options()
        if cached is not None:
            return cached
        classifications = self._repository.list_active_account_classifications()
        options = build_classification_options(classifications)
        self._options_cache.set_classification_options(options)
        return options

    def list_instance_select_options(self, db_type: str | None = None) -> list[dict[str, str]]:
        """获取实例下拉选项."""
        cached = self._options_cache.get_instance_select_options(db_type)
        if cached is not None:
            return cached
        instances = self._repository.list_active_instances(db_type=db_type)
        options = build_instance_select_options(instances)
        self._options_cache.set_instance_select_options(db_type, options)
        return options

    def list_database_select_options(self, instance_id: int) -> list[dict[str, str]]:
        """获取数据库下拉选项."""
        cached = self._options_cache.get_database_select_options(instance_id)
        if cached is not None:
            return cached
        databases = self._repository.list_active_databases_by_instance(instance_id)
        options = build_database_select_options(databases)
        self._options_cache.set_database_select_options(instance_id, options)
        return options

    def get_common_instances_options(self, db_type: str | None = None) -> CommonInstancesOptionsResult:
        """构建 Common API 的实例选项."""
        cached = self._options_cache.get_common_instances_options(db_type)
        if cached is not None:
            items = [
                CommonInstanceOptionItem(
                    id=int(item.get("id", 0)),
                    name=cast(str, item.get("name", "")),
                    db_type=cast(str, item.get("db_type", "")),
                    display_name=cast(str, item.get("display_name", "")),
                )
                for item in cached
                if isinstance(item, dict)
            ]
            return CommonInstancesOptionsResult(instances=items)

        instances = self._repository.list_active_instances(db_type=db_type)
        items = [
            CommonInstanceOptionItem(
                id=int(instance.id),
                name=instance.name,
                db_type=instance.db_type,
                display_name=f"{instance.name} ({instance.db_type.upper()})",
            )
            for instance in instances
        ]
        self._options_cache.set_common_instances_options(
            db_type,
            [
                {
                    "id": item.id,
                    "name": item.name,
                    "db_type": item.db_type,
                    "display_name": item.display_name,
                }
                for item in items
            ],
        )
        return CommonInstancesOptionsResult(instances=items)

    def get_common_databases_options(self, filters: CommonDatabasesOptionsFilters) -> CommonDatabasesOptionsResult:
        """构建 Common API 的数据库选项."""
        cached = self._options_cache.get_common_databases_options(filters)
        if cached is not None:
            databases_payload = cached.get("databases", [])
            if isinstance(databases_payload, list):
                items = [
                    CommonDatabaseOptionItem(
                        id=int(item.get("id", 0)),
                        database_name=cast(str, item.get("database_name", "")),
                        is_active=bool(item.get("is_active", False)),
                        first_seen_date=cast(str | None, item.get("first_seen_date")),
                        last_seen_date=cast(str | None, item.get("last_seen_date")),
                        deleted_at=cast(str | None, item.get("deleted_at")),
                    )
                    for item in databases_payload
                    if isinstance(item, dict)
                ]
            else:
                items = []

            raw_total_count = cached.get("total_count", 0)
            total_count = int(raw_total_count) if isinstance(raw_total_count, (int, str)) else 0
            return CommonDatabasesOptionsResult(
                databases=items,
                total_count=total_count,
                limit=filters.limit,
                offset=filters.offset,
            )

        databases, total_count = self._repository.list_databases_by_instance(
            filters.instance_id,
            limit=filters.limit,
            offset=filters.offset,
        )
        items: list[CommonDatabaseOptionItem] = []
        payload_items: list[dict[str, object]] = []
        for database in databases:
            item = CommonDatabaseOptionItem(
                id=int(database.id),
                database_name=database.database_name,
                is_active=database.is_active,
                first_seen_date=(database.first_seen_date.isoformat() if database.first_seen_date else None),
                last_seen_date=(database.last_seen_date.isoformat() if database.last_seen_date else None),
                deleted_at=(database.deleted_at.isoformat() if database.deleted_at else None),
            )
            items.append(item)
            payload_items.append(
                {
                    "id": item.id,
                    "database_name": item.database_name,
                    "is_active": item.is_active,
                    "first_seen_date": item.first_seen_date,
                    "last_seen_date": item.last_seen_date,
                    "deleted_at": item.deleted_at,
                }
            )

        self._options_cache.set_common_databases_options(
            filters,
            {
                "databases": payload_items,
                "total_count": total_count,
            },
        )

        return CommonDatabasesOptionsResult(
            databases=items,
            total_count=total_count,
            limit=filters.limit,
            offset=filters.offset,
        )
