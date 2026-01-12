"""实例列表页面 Service.

职责:
- 聚合实例列表页面渲染所需的只读数据
- 组织 repositories/services，不在 routes 中直接拼 Query
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.constants import STATUS_ACTIVE_OPTIONS, DatabaseType
from app.utils.database_type_utils import (
    build_database_type_select_option,
    get_database_type_color,
    get_database_type_display_name,
    get_database_type_icon,
)
from app.models.credential import Credential
from app.repositories.credentials_repository import CredentialsRepository
from app.services.common.filter_options_service import FilterOptionsService


@dataclass(slots=True)
class InstanceListPageContext:
    """实例列表页面上下文."""

    credentials: list[Credential]
    database_type_options: list[dict[str, Any]]
    database_type_map: dict[str, dict[str, str]]
    tag_options: list[dict[str, Any]]
    status_options: list[dict[str, str]]

    search: str
    db_type: str
    status: str
    include_deleted: bool
    selected_tags: list[str]


class InstanceListPageService:
    """实例列表页面读取服务."""

    def __init__(
        self,
        *,
        credentials_repository: CredentialsRepository | None = None,
        filter_options_service: FilterOptionsService | None = None,
    ) -> None:
        """初始化服务并注入依赖."""
        self._credentials_repository = credentials_repository or CredentialsRepository()
        self._filter_options_service = filter_options_service or FilterOptionsService()

    def build_context(
        self,
        *,
        search: str,
        db_type: str,
        status: str,
        include_deleted: bool,
        selected_tags: list[str],
    ) -> InstanceListPageContext:
        """构造实例列表页渲染上下文."""
        credentials = self._credentials_repository.list_active_credentials()
        database_type_options = [build_database_type_select_option(item) for item in DatabaseType.RELATIONAL]
        database_type_map = {
            item: {
                "display_name": get_database_type_display_name(item),
                "icon": get_database_type_icon(item),
                "color": get_database_type_color(item),
            }
            for item in DatabaseType.RELATIONAL
        }
        tag_options = self._filter_options_service.list_active_tag_options()

        return InstanceListPageContext(
            credentials=credentials,
            database_type_options=database_type_options,
            database_type_map=database_type_map,
            tag_options=tag_options,
            status_options=STATUS_ACTIVE_OPTIONS,
            search=search,
            db_type=db_type,
            status=status,
            include_deleted=include_deleted,
            selected_tags=selected_tags,
        )
