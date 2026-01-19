"""账户同步适配器基础定义,提供统一的抓取/归一化接口."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.types import RawAccount, RemoteAccount
    from app.models.instance import Instance


class BaseAccountAdapter(ABC):
    """账户同步适配器基类,负责抽象远端账户数据抓取."""

    def fetch_remote_accounts(self, instance: Instance, connection: object) -> list[RemoteAccount]:
        """拉取远端账户信息.

        Args:
            instance: 目标数据库实例.
            connection: 适配器维护的连接对象.

        Returns:
            list[RemoteAccount]: 已标准化的账户列表,包含以下字段:
                - username: 唯一标识(可含主机)
                - display_name: 可选,展示用
                - is_superuser: 是否超级用户
                - is_active: 是否活跃
                - attributes: 附加信息(锁定状态、主机等)
                - permissions: 标准化权限快照

        """
        raw_accounts = self._fetch_raw_accounts(instance, connection)
        return [self._normalize_account(instance, account) for account in raw_accounts]

    def enrich_permissions(
        self,
        instance: Instance,
        connection: object,
        accounts: list[RemoteAccount],
        *,
        usernames: Sequence[str] | None = None,
    ) -> list[RemoteAccount]:
        """为账号列表补全权限信息.

        Args:
            instance: 目标实例.
            connection: 数据库连接.
            accounts: 需要补全权限的账户列表.
            usernames: 可选,仅对指定用户名执行补全.

        Returns:
            list[RemoteAccount]: 包含权限信息的账户列表.

        默认实现直接返回原列表,适用于在 ``_fetch_raw_accounts`` 阶段已经填充
        ``permissions`` 的适配器.若需要按需加载权限(例如 SQL Server),请在具体
        适配器中重写该方法.

        """
        del instance, connection, usernames
        return accounts

    @abstractmethod
    def _fetch_raw_accounts(self, instance: Instance, connection: object) -> list[RawAccount]:
        """具体数据库实现负责查询账户列表.

        Args:
            instance: 数据库实例.
            connection: 已建立的数据库连接.

        Returns:
            list[RawAccount]: 原始账户数据(尚未标准化).

        """

    @abstractmethod
    def _normalize_account(self, instance: Instance, account: RawAccount) -> RemoteAccount:
        """将原始账户数据转换为标准结构.

        Args:
            instance: 数据库实例.
            account: 原始账户记录.

        Returns:
            RemoteAccount: 满足 `fetch_remote_accounts` 约定的账户字典.

        """
