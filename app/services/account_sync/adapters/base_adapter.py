from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Sequence

from app.models.instance import Instance


class BaseAccountAdapter(ABC):
    """账户同步适配器基类，负责抽象远端账户数据抓取。"""

    def fetch_remote_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:  # noqa: ANN401
        """拉取远端账户信息。

        返回的每个账户字典需要包含字段：
        - username: 唯一标识（可含主机）
        - display_name: 可选，展示用
        - is_superuser: 是否超级用户
        - is_active: 是否活跃
        - attributes: dict，附加信息（锁定状态、主机等）
        - permissions: dict，标准化权限快照
        """
        raw_accounts = self._fetch_raw_accounts(instance, connection)
        normalized: List[Dict[str, Any]] = []
        for account in raw_accounts:
            normalized.append(self._normalize_account(instance, account))
        return normalized

    def enrich_permissions(
        self,
        instance: Instance,
        connection: Any,
        accounts: List[Dict[str, Any]],
        *,
        usernames: Sequence[str] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        为账号列表补全权限信息。

        默认实现直接返回原列表，适用于在 ``_fetch_raw_accounts`` 阶段已经填充
        ``permissions`` 的适配器。若需要按需加载权限（例如 SQL Server），请在具体
        适配器中重写该方法。
        """
        return accounts

    @abstractmethod
    def _fetch_raw_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:  # noqa: ANN401
        """具体数据库实现负责查询账户列表。"""

    @abstractmethod
    def _normalize_account(self, instance: Instance, account: Dict[str, Any]) -> Dict[str, Any]:
        """将原始账户数据转换为标准结构。"""
