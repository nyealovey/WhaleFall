"""账户统计 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import Any

from app.repositories.account_statistics_repository import AccountStatisticsRepository
from app.types.accounts_statistics import AccountStatisticsResult


class AccountsStatisticsReadService:
    """账户统计读取服务."""

    def __init__(self, repository: AccountStatisticsRepository | None = None) -> None:
        """初始化读取服务."""
        self._repository = repository or AccountStatisticsRepository()

    def build_statistics(self) -> AccountStatisticsResult:
        """构建账户统计结果."""
        summary = self._repository.fetch_summary()
        db_type_stats = self._repository.fetch_db_type_stats()
        classification_stats = self._repository.fetch_classification_stats()

        return AccountStatisticsResult(
            total_accounts=summary["total_accounts"],
            active_accounts=summary["active_accounts"],
            locked_accounts=summary["locked_accounts"],
            normal_accounts=summary["normal_accounts"],
            deleted_accounts=summary["deleted_accounts"],
            database_instances=summary.get("total_instances", 0),
            total_instances=summary["total_instances"],
            active_instances=summary["active_instances"],
            disabled_instances=summary["disabled_instances"],
            normal_instances=summary["normal_instances"],
            deleted_instances=summary["deleted_instances"],
            db_type_stats=db_type_stats,
            classification_stats=classification_stats,
        )

    def fetch_summary(self, *, instance_id: int | None, db_type: str | None) -> dict[str, int]:
        """获取账户统计汇总."""
        return self._repository.fetch_summary(instance_id=instance_id, db_type=db_type)

    def fetch_db_type_stats(self) -> dict[str, dict[str, int]]:
        """获取按数据库类型统计."""
        return self._repository.fetch_db_type_stats()

    def fetch_classification_stats(self) -> dict[str, dict[str, Any]]:
        """获取按分类统计."""
        return self._repository.fetch_classification_stats()

    @staticmethod
    def empty_statistics() -> AccountStatisticsResult:
        """构建空统计结果."""
        return AccountStatisticsResult(
            total_accounts=0,
            active_accounts=0,
            locked_accounts=0,
            normal_accounts=0,
            deleted_accounts=0,
            database_instances=0,
            total_instances=0,
            active_instances=0,
            disabled_instances=0,
            normal_instances=0,
            deleted_instances=0,
            db_type_stats={},
            classification_stats={},
        )
