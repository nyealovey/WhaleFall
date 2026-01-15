"""实例详情页面 Service.

职责:
- 聚合实例详情页渲染所需的只读数据
- 组织 repositories/services，不在 routes 中直接拼 Query
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import DatabaseType
from app.core.types.instance_accounts import InstanceAccountSummary
from app.core.types.tags import TagSummary
from app.models.credential import Credential
from app.models.instance import Instance
from app.repositories.credentials_repository import CredentialsRepository
from app.repositories.instance_accounts_repository import InstanceAccountsRepository
from app.repositories.instances_repository import InstancesRepository
from app.utils.database_type_utils import get_database_type_display_name


@dataclass(slots=True)
class InstanceDetailPageContext:
    """实例详情页面上下文."""

    instance: Instance
    tags: list[TagSummary]
    account_summary: InstanceAccountSummary
    credentials: list[Credential]
    database_type_options: list[dict[str, str]]


class InstanceDetailPageService:
    """实例详情页面读取服务."""

    def __init__(
        self,
        *,
        instances_repository: InstancesRepository | None = None,
        instance_accounts_repository: InstanceAccountsRepository | None = None,
        credentials_repository: CredentialsRepository | None = None,
    ) -> None:
        """初始化服务并注入依赖."""
        self._instances_repository = instances_repository or InstancesRepository()
        self._instance_accounts_repository = instance_accounts_repository or InstanceAccountsRepository()
        self._credentials_repository = credentials_repository or CredentialsRepository()

    def build_context(self, instance_id: int) -> InstanceDetailPageContext:
        """构造实例详情页渲染上下文."""
        instance = self._instances_repository.get_active_instance(instance_id)
        tags_map = self._instances_repository.fetch_tags_map([instance_id])
        account_summary = self._instance_accounts_repository.fetch_summary(instance_id)
        credentials = self._credentials_repository.list_active_credentials()

        database_type_options = [
            {"value": db_type, "label": get_database_type_display_name(db_type)} for db_type in DatabaseType.RELATIONAL
        ]

        return InstanceDetailPageContext(
            instance=instance,
            tags=tags_map.get(instance_id, []),
            account_summary=account_summary,
            credentials=credentials,
            database_type_options=database_type_options,
        )
