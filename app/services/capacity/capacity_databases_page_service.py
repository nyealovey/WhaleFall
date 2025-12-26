"""容量统计(数据库维度)页面 Service.

职责:
- 组织下拉选项与路由参数解析/纠偏(如 database_name → database_id)
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass

from app.constants import DATABASE_TYPES
from app.repositories.capacity_databases_repository import CapacityDatabasesRepository
from app.services.common.filter_options_service import FilterOptionsService
from app.services.database_type_service import DatabaseTypeService


@dataclass(frozen=True, slots=True)
class CapacityDatabasesPageContext:
    database_type_options: list[dict[str, str]]
    instance_options: list[dict[str, str]]
    database_options: list[dict[str, str]]
    db_type: str
    instance: str
    database_id: str
    database: str


class CapacityDatabasesPageService:
    """数据库容量页面读取服务."""

    def __init__(
        self,
        *,
        repository: CapacityDatabasesRepository | None = None,
        filter_options_service: FilterOptionsService | None = None,
    ) -> None:
        self._repository = repository or CapacityDatabasesRepository()
        self._filter_options_service = filter_options_service or FilterOptionsService()

    def build_context(
        self,
        *,
        db_type: str,
        instance: str,
        database_id: str,
        database: str,
    ) -> CapacityDatabasesPageContext:
        database_type_options = self._build_database_type_options()

        normalized_db_type = (db_type or "").strip()
        normalized_instance = (instance or "").strip()
        normalized_database_id = (database_id or "").strip()
        normalized_database_name = (database or "").strip()

        if not normalized_database_id and normalized_database_name:
            instance_id_int = self._coerce_int(normalized_instance)
            resolved_id = self._repository.resolve_instance_database_id_by_name(
                database_name=normalized_database_name,
                instance_id=instance_id_int,
            )
            if resolved_id is not None:
                normalized_database_id = str(resolved_id)

        if normalized_database_id:
            normalized_database_name = ""

        instance_options = (
            self._filter_options_service.list_instance_select_options(normalized_db_type or None)
            if normalized_db_type
            else []
        )

        instance_id_int = self._coerce_int(normalized_instance)
        database_options = (
            self._filter_options_service.list_database_select_options(instance_id_int) if instance_id_int else []
        )

        return CapacityDatabasesPageContext(
            database_type_options=database_type_options,
            instance_options=instance_options,
            database_options=database_options,
            db_type=normalized_db_type,
            instance=normalized_instance,
            database_id=normalized_database_id,
            database=normalized_database_name,
        )

    @staticmethod
    def _build_database_type_options() -> list[dict[str, str]]:
        database_type_configs = DatabaseTypeService.get_active_types()
        if database_type_configs:
            return [{"value": config.name, "label": config.display_name} for config in database_type_configs]
        return [{"value": item["name"], "label": item["display_name"]} for item in DATABASE_TYPES]

    @staticmethod
    def _coerce_int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

