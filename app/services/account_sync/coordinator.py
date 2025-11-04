from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from app.models.instance import Instance
from app.services.account_sync.adapters.factory import get_account_adapter
from app.services.account_sync.inventory_manager import AccountInventoryManager
from app.services.account_sync.permission_manager import AccountPermissionManager
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_sync_logger


class AccountSyncCoordinator:
    """账户同步协调器，负责两阶段流程。"""

    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self.logger = get_sync_logger()
        self._adapter = get_account_adapter(instance.db_type)
        self._inventory_manager = AccountInventoryManager()
        self._permission_manager = AccountPermissionManager()
        self._connection = None
        self._cached_accounts: Optional[List[dict]] = None
        self._active_accounts_cache = None
        self._connection_failed = False
        self._connection_error: Optional[str] = None

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        if self._connection and getattr(self._connection, "is_connected", False):
            return True
        if self._connection_failed:
            return False

        try:
            connection = ConnectionFactory.create_connection(self.instance)
        except Exception as exc:  # noqa: BLE001
            self._connection_failed = True
            self._connection_error = str(exc)
            self.logger.error(
                "account_sync_connection_init_failed",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                db_type=self.instance.db_type,
                error=self._connection_error,
                exc_info=True,
            )
            return False

        if not connection:
            self._connection_failed = True
            self._connection_error = "不支持的数据库类型"
            self.logger.error(
                "account_sync_connection_unsupported",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                db_type=self.instance.db_type,
            )
            return False

        try:
            if connection.connect():
                self._connection = connection
                self._connection_failed = False
                self._connection_error = None
                return True
            self._connection_failed = True
            self._connection_error = "连接返回失败"
            self.logger.error(
                "account_sync_connection_failed",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                db_type=self.instance.db_type,
            )
            return False
        except Exception as exc:  # noqa: BLE001
            self._connection_failed = True
            self._connection_error = str(exc)
            self.logger.error(
                "account_sync_connection_exception",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                db_type=self.instance.db_type,
                error=self._connection_error,
                exc_info=True,
            )
            return False

    def disconnect(self) -> None:
        if self._connection:
            try:
                self._connection.disconnect()
            finally:
                self._connection = None

    # ------------------------------------------------------------------
    # 同步阶段
    # ------------------------------------------------------------------
    def fetch_remote_accounts(self) -> List[dict]:
        if self._cached_accounts is None:
            if not self._connection or not getattr(self._connection, "is_connected", False):
                if not self.connect():
                    error_message = self._connection_error or "数据库连接未建立"
                    raise RuntimeError(error_message)
            self._cached_accounts = self._adapter.fetch_remote_accounts(self.instance, self._connection)
        return self._cached_accounts

    def synchronize_inventory(self) -> Dict:
        remote_accounts = self.fetch_remote_accounts()
        summary, active_accounts = self._inventory_manager.synchronize(self.instance, remote_accounts)
        self._active_accounts_cache = active_accounts
        return summary

    def synchronize_permissions(self, *, session_id: str | None = None) -> Dict:
        remote_accounts = self.fetch_remote_accounts()
        active_accounts = getattr(self, "_active_accounts_cache", None)
        if active_accounts is None:
            _, active_accounts = self._inventory_manager.synchronize(self.instance, remote_accounts)
        summary, _ = self._permission_manager.synchronize(
            self.instance,
            remote_accounts,
            active_accounts,
            session_id=session_id,
        )
        return summary

    def sync_all(self, *, session_id: str | None = None) -> Dict:
        inventory_summary = self.synchronize_inventory()
        permissions_summary = self.synchronize_permissions(session_id=session_id)
        return {
            "inventory": inventory_summary,
            "permissions": permissions_summary,
        }
