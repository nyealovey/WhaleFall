"""账户统计页面 Service.

职责:
- 聚合账户统计页面渲染所需的只读数据
- 将 routes 中直接 query 下沉到 service 层
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.instance import Instance
from app.models.sync_session import SyncSession
from app.services.statistics.account_statistics_service import build_aggregated_statistics, empty_statistics


@dataclass(slots=True)
class AccountsStatisticsPageContext:
    """账户统计页面上下文."""

    stats: dict[str, Any]
    recent_syncs: list[SyncSession]
    recent_accounts: list[object]
    instances: list[Instance]


class AccountsStatisticsPageService:
    """账户统计页面读取服务."""

    @staticmethod
    def _fetch_active_instances() -> list[Instance]:
        """加载所有活跃实例."""
        return Instance.query.filter_by(is_active=True).all()

    @staticmethod
    def _fetch_recent_syncs(limit: int = 10) -> list[SyncSession]:
        """查询最近的同步会话."""
        return SyncSession.query.order_by(SyncSession.created_at.desc()).limit(limit).all()

    def build_context(self) -> AccountsStatisticsPageContext:
        """构造渲染模板所需的上下文."""
        stats = build_aggregated_statistics()
        return AccountsStatisticsPageContext(
            stats=stats,
            recent_syncs=self._fetch_recent_syncs(),
            recent_accounts=list(stats.get("recent_accounts", [])),
            instances=self._fetch_active_instances(),
        )

    def build_fallback_context(self) -> AccountsStatisticsPageContext:
        """构造失败时的兜底上下文."""
        return AccountsStatisticsPageContext(
            stats=empty_statistics(),
            recent_syncs=[],
            recent_accounts=[],
            instances=self._fetch_active_instances(),
        )

