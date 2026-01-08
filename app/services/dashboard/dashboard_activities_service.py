"""Dashboard Activities Service.

职责:
- 统一 dashboard activities 的数据来源(当前为空数组占位)
- 不返回 Response、不 commit
"""

from __future__ import annotations


class DashboardActivitiesService:
    """仪表板活动读取服务."""

    def list_activities(self) -> list[dict[str, object]]:
        """返回活动列表(当前占位实现)."""
        return []

