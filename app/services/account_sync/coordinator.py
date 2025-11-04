from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Dict, Iterable, List, Optional

from app.models.instance import Instance
from app.services.account_sync.adapters.factory import get_account_adapter
from app.services.account_sync.inventory_manager import AccountInventoryManager
from app.services.account_sync.permission_manager import AccountPermissionManager
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_sync_logger


MODULE = "account_sync"


class AccountSyncCoordinator(AbstractContextManager["AccountSyncCoordinator"]):
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

    def __enter__(self) -> "AccountSyncCoordinator":
        if not self.connect():
            message = self._connection_error or "数据库连接未建立"
            raise RuntimeError(message)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN401
        self.disconnect()

    def connect(self) -> bool:
        if self._connection and getattr(self._connection, "is_connected", False):
            self.logger.info(
                "account_sync_connection_reuse",
                module=MODULE,
                instance_id=self.instance.id,
                instance_name=self.instance.name,
            )
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
                module=MODULE,
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
                module=MODULE,
            )
            return False

        try:
            if connection.connect():
                self._connection = connection
                self._connection_failed = False
                self._connection_error = None
                self.logger.info(
                    "account_sync_connection_success",
                    module=MODULE,
                    instance_id=self.instance.id,
                    instance_name=self.instance.name,
                    db_type=self.instance.db_type,
                )
                return True
            self._connection_failed = True
            self._connection_error = "连接返回失败"
            self.logger.error(
                "account_sync_connection_failed",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                db_type=self.instance.db_type,
                module=MODULE,
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
                module=MODULE,
                exc_info=True,
            )
            return False

    def disconnect(self) -> None:
        if self._connection:
            try:
                self._connection.disconnect()
            finally:
                self._connection = None
                self.logger.info(
                    "account_sync_connection_closed",
                    module=MODULE,
                    instance_id=self.instance.id,
                    instance_name=self.instance.name,
                )

    # ------------------------------------------------------------------
    # 同步阶段
    # ------------------------------------------------------------------
    def fetch_remote_accounts(self) -> List[dict]:
        if self._cached_accounts is None:
            if not self._connection or not getattr(self._connection, "is_connected", False):
                if not self.connect():
                    error_message = self._connection_error or "数据库连接未建立"
                    raise RuntimeError(error_message)
            self.logger.info(
                "account_sync_fetch_remote_accounts_start",
                module=MODULE,
                instance_id=self.instance.id,
                instance_name=self.instance.name,
            )
            raw_accounts = self._adapter.fetch_remote_accounts(self.instance, self._connection) or []
            self._cached_accounts = list(raw_accounts)
            self.logger.info(
                "account_sync_fetch_remote_accounts_completed",
                module=MODULE,
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                total_accounts=len(self._cached_accounts),
            )
        return self._cached_accounts

    def synchronize_inventory(self) -> Dict:
        remote_accounts = self.fetch_remote_accounts()
        summary, active_accounts = self._inventory_manager.synchronize(self.instance, remote_accounts)
        inventory_summary = {
            "status": "completed",
            "created": summary.get("created", 0),
            "refreshed": summary.get("refreshed", 0),
            "reactivated": summary.get("reactivated", 0),
            "deactivated": summary.get("deactivated", 0),
            "processed_records": summary.get("processed_records", 0),
             "total_remote": summary.get("total_remote", len(remote_accounts)),
            "active_accounts": [account.username for account in active_accounts],
            "active_count": summary.get("active_count", len(active_accounts)),
        }
        self._active_accounts_cache = active_accounts
        self.logger.info(
            "account_sync_inventory_completed",
            module=MODULE,
            phase="inventory",
            instance_id=self.instance.id,
            instance_name=self.instance.name,
            **{k: v for k, v in inventory_summary.items() if k != "active_accounts"},
        )
        return inventory_summary

    def synchronize_permissions(self, *, session_id: str | None = None) -> Dict:
        remote_accounts = self.fetch_remote_accounts()
        active_accounts = getattr(self, "_active_accounts_cache", None)
        if active_accounts is None:
            summary, active_accounts = self._inventory_manager.synchronize(self.instance, remote_accounts)
            self._active_accounts_cache = active_accounts
            self.logger.info(
                "account_sync_inventory_rehydrated",
                module=MODULE,
                phase="inventory",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                created=summary.get("created", 0),
                refreshed=summary.get("refreshed", 0),
                reactivated=summary.get("reactivated", 0),
                deactivated=summary.get("deactivated", 0),
            )

        if not active_accounts:
            collection_summary = {
                "status": "skipped",
                "processed_records": 0,
                "created": 0,
                "updated": 0,
                "skipped": len(remote_accounts),
                "message": "未检测到活跃账户，跳过权限同步",
            }
            self.logger.info(
                "account_sync_collection_skipped_no_active_accounts",
                module=MODULE,
                phase="collection",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                skipped=len(remote_accounts),
            )
            return collection_summary

        summary, _ = self._permission_manager.synchronize(
            self.instance,
            remote_accounts,
            active_accounts,
            session_id=session_id,
        )
        collection_summary = {
            "status": "completed",
            "created": summary.get("created", 0),
            "updated": summary.get("updated", 0),
            "skipped": summary.get("skipped", 0),
            "processed_records": summary.get("processed_records", summary.get("created", 0) + summary.get("updated", 0)),
        }
        self.logger.info(
            "account_sync_collection_completed",
            module=MODULE,
            phase="collection",
            instance_id=self.instance.id,
            instance_name=self.instance.name,
            **collection_summary,
        )
        return collection_summary

    def sync_all(self, *, session_id: str | None = None) -> Dict:
        inventory_summary = self.synchronize_inventory()
        permissions_summary = self.synchronize_permissions(session_id=session_id)
        return {
            "inventory": inventory_summary,
            "collection": permissions_summary,
        }
