"""通用筛选器/下拉选项 Service.

覆盖:
- Common API 的 instances/databases/dbtypes options
- 多页面复用的标签/分类/实例/数据库下拉选项
"""

from __future__ import annotations

from typing import Any, cast

from app.models.tag import Tag
from app.repositories.filter_options_repository import FilterOptionsRepository
from app.types.common_filter_options import (
    CommonDatabaseOptionItem,
    CommonDatabasesOptionsFilters,
    CommonDatabasesOptionsResult,
    CommonDatabaseTypeOptionItem,
    CommonDatabaseTypesOptionsResult,
    CommonInstanceOptionItem,
    CommonInstancesOptionsResult,
)
from app.utils.query_filter_utils import (
    build_category_options,
    build_classification_options,
    build_database_select_options,
    build_instance_select_options,
    build_tag_options,
)


class FilterOptionsService:
    """筛选器选项读取服务."""

    def __init__(self, repository: FilterOptionsRepository | None = None) -> None:
        self._repository = repository or FilterOptionsRepository()

    def list_active_tag_options(self) -> list[dict[str, str]]:
        tags = self._repository.list_active_tags()
        return build_tag_options(tags)

    def list_tag_categories(self) -> list[dict[str, str]]:
        label_mapping = dict(Tag.get_category_choices())
        categories_raw = self._repository.list_active_tag_categories()
        return build_category_options(categories_raw, label_mapping)

    def list_classification_options(self) -> list[dict[str, str]]:
        classifications = self._repository.list_active_account_classifications()
        return build_classification_options(classifications)

    def list_instance_select_options(self, db_type: str | None = None) -> list[dict[str, str]]:
        instances = self._repository.list_active_instances(db_type=db_type)
        return build_instance_select_options(instances)

    def list_database_select_options(self, instance_id: int) -> list[dict[str, str]]:
        databases = self._repository.list_active_databases_by_instance(instance_id)
        return build_database_select_options(databases)

    def get_common_instances_options(self, db_type: str | None = None) -> CommonInstancesOptionsResult:
        instances = self._repository.list_active_instances(db_type=db_type)
        items: list[CommonInstanceOptionItem] = []
        for instance in instances:
            name = cast(str, getattr(instance, "name", "") or "")
            instance_db_type = cast(str, getattr(instance, "db_type", "") or "")
            items.append(
                CommonInstanceOptionItem(
                    id=int(getattr(instance, "id", 0) or 0),
                    name=name,
                    db_type=instance_db_type,
                    display_name=f"{name} ({instance_db_type.upper()})",
                ),
            )
        return CommonInstancesOptionsResult(instances=items)

    def get_common_databases_options(self, filters: CommonDatabasesOptionsFilters) -> CommonDatabasesOptionsResult:
        databases, total_count = self._repository.list_databases_by_instance(
            filters.instance_id,
            limit=filters.limit,
            offset=filters.offset,
        )
        items: list[CommonDatabaseOptionItem] = []
        for database in databases:
            items.append(
                CommonDatabaseOptionItem(
                    id=int(getattr(database, "id", 0) or 0),
                    database_name=cast(str, getattr(database, "database_name", "") or ""),
                    is_active=bool(getattr(database, "is_active", False)),
                    first_seen_date=(
                        database.first_seen_date.isoformat() if getattr(database, "first_seen_date", None) else None
                    ),
                    last_seen_date=(
                        database.last_seen_date.isoformat() if getattr(database, "last_seen_date", None) else None
                    ),
                    deleted_at=(database.deleted_at.isoformat() if getattr(database, "deleted_at", None) else None),
                ),
            )
        return CommonDatabasesOptionsResult(
            databases=items,
            total_count=int(total_count),
            limit=int(filters.limit),
            offset=int(filters.offset),
        )

    def get_common_database_types_options(self) -> CommonDatabaseTypesOptionsResult:
        configs = self._repository.list_active_database_type_configs()
        options: list[CommonDatabaseTypeOptionItem] = []
        for config in configs:
            options.append(
                CommonDatabaseTypeOptionItem(
                    value=cast(str, getattr(config, "name", "") or ""),
                    text=cast(str, getattr(config, "display_name", "") or ""),
                    icon=cast("str | None", getattr(config, "icon", None)),
                    color=cast("str | None", getattr(config, "color", None)),
                ),
            )
        return CommonDatabaseTypesOptionsResult(options=options)
