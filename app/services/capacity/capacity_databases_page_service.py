"""容量统计(数据库维度)页面 Service.

职责:
- 组织下拉选项与路由参数解析/纠偏(如 database_name → database_id)
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.constants import DATABASE_TYPES
from app.repositories.capacity_databases_repository import CapacityDatabasesRepository
from app.services.common.filter_options_service import FilterOptionsService


@dataclass(frozen=True, slots=True)
class CapacityDatabasesPageContext:
    """数据库容量页面上下文."""

    database_type_options: list[dict[str, str]]
    instance_options: list[dict[str, str]]
    database_options: list[dict[str, str]]
    db_types: list[str]
    instances: list[str]
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
        """初始化服务并注入依赖."""
        self._repository = repository or CapacityDatabasesRepository()
        self._filter_options_service = filter_options_service or FilterOptionsService()

    def build_context(
        self,
        *,
        db_type: str | list[str],
        instance: str | list[str],
        database_id: str,
        database: str,
    ) -> CapacityDatabasesPageContext:
        """构造页面渲染上下文."""
        database_type_options = self._build_database_type_options()

        normalized_db_types = self._normalize_text_list(db_type)
        normalized_instances = self._normalize_text_list(instance)
        normalized_database_id = database_id.strip()
        normalized_database_name = database.strip()

        instance_options = (
            self._filter_options_service.list_instance_select_options(normalized_db_types) if normalized_db_types else []
        )

        selected_instance_id = self._coerce_single_instance_id(normalized_instances)
        if not normalized_database_id and normalized_database_name and selected_instance_id is not None:
            resolved_id = self._repository.resolve_instance_database_id_by_name(
                database_name=normalized_database_name,
                instance_id=selected_instance_id,
            )
            if resolved_id is not None:
                normalized_database_id = str(resolved_id)

        if selected_instance_id is None:
            normalized_database_id = ""
            normalized_database_name = ""

        if normalized_database_id:
            normalized_database_name = ""

        database_options = (
            self._filter_options_service.list_database_select_options(selected_instance_id)
            if selected_instance_id is not None
            else []
        )

        return CapacityDatabasesPageContext(
            database_type_options=database_type_options,
            instance_options=instance_options,
            database_options=database_options,
            db_types=normalized_db_types,
            instances=normalized_instances,
            database_id=normalized_database_id,
            database=normalized_database_name,
        )

    @staticmethod
    def _build_database_type_options() -> list[dict[str, str]]:
        return [{"value": item["name"], "label": item["display_name"]} for item in DATABASE_TYPES]

    @staticmethod
    def _coerce_int(value: str) -> int | None:
        """Best-effort parse query-string int.

        页面筛选参数允许为空/脏值；无法解析时返回 None 表示“不参与筛选”。
        """
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _coerce_single_instance_id(cls, values: list[str]) -> int | None:
        if len(values) != 1:
            return None
        return cls._coerce_int(values[0])

    @staticmethod
    def _normalize_text_list(value: str | list[str] | None) -> list[str]:
        raw_values: list[Any]
        if value is None:
            raw_values = []
        elif isinstance(value, list):
            raw_values = value
        else:
            raw_values = [value]

        normalized: list[str] = []
        for item in raw_values:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized
