"""账户同步协调器,封装连接管理、清单/权限双阶段流程."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any, Self

from app.services.accounts_sync.adapters.factory import get_account_adapter
from app.services.accounts_sync.inventory_manager import AccountInventoryManager
from app.services.accounts_sync.permission_manager import AccountPermissionManager, PermissionSyncError
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_sync_logger

if TYPE_CHECKING:
    from types import TracebackType

    from app.models.instance import Instance
    from app.models.instance_account import InstanceAccount
    from app.types import (
        CollectionSummary,
        InventorySummary,
        RemoteAccount,
        RemoteAccountMap,
        SyncConnection,
        SyncStagesSummary,
    )
else:
    Instance = Any
    InstanceAccount = Any
    CollectionSummary = dict[str, Any]
    InventorySummary = dict[str, Any]
    RemoteAccount = dict[str, Any]
    RemoteAccountMap = dict[str, Any]
    SyncConnection = Any
    SyncStagesSummary = dict[str, Any]

MODULE = "accounts_sync"
CONNECTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    ValueError,
    LookupError,
    ConnectionError,
    TimeoutError,
    OSError,
)


class AccountSyncCoordinator(AbstractContextManager["AccountSyncCoordinator"]):
    """账户同步协调器,负责两阶段流程.

    协调账户同步的两个阶段:
    1. 清单阶段(Inventory):同步账户基本信息,标记活跃/非活跃状态
    2. 权限阶段(Collection):同步活跃账户的权限信息

    支持上下文管理器协议,自动管理数据库连接的建立和释放.

    Attributes:
        instance: 数据库实例对象.
        logger: 结构化日志记录器.

    Example:
        >>> with AccountSyncCoordinator(instance) as coordinator:
        ...     result = coordinator.sync_all()

    """

    def __init__(self, instance: Instance) -> None:
        """绑定实例并准备同步依赖."""
        self.instance = instance
        self.logger = get_sync_logger()
        self._adapter = get_account_adapter(instance.db_type)
        self._inventory_manager = AccountInventoryManager()
        self._permission_manager = AccountPermissionManager()
        self._connection: SyncConnection | None = None
        self._cached_accounts: list[RemoteAccount] | None = None
        self._active_accounts_cache: list[InstanceAccount] | None = None
        self._enriched_usernames: set[str] = set()
        self._connection_failed = False
        self._connection_error: str | None = None

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def __enter__(self) -> Self:
        """进入上下文时建立数据库连接.

        Returns:
            AccountSyncCoordinator: 自身引用,便于链式调用.

        Raises:
            RuntimeError: 当连接无法建立时抛出.

        """
        if not self.connect():
            message = self._connection_error or "数据库连接未建立"
            raise RuntimeError(message)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """退出上下文时释放连接资源.

        Args:
            exc_type: 异常类型.
            exc_val: 异常值.
            exc_tb: 异常追踪信息.

        Returns:
            None: 连接关闭后返回 False 等效值,从而不吞掉异常.

        """
        self.disconnect()

    def connect(self) -> bool:
        """建立到数据库实例的连接.

        如果连接已存在且有效,则复用现有连接.
        如果之前连接失败,则直接返回 False 不再重试.

        Returns:
            连接成功返回 True,失败返回 False.

        """
        if self._connection and getattr(self._connection, "is_connected", False):
            self.logger.info(
                "accounts_sync_connection_reuse",
                module=MODULE,
                instance_id=self.instance.id,
                instance_name=self.instance.name,
            )
            return True
        if self._connection_failed:
            return False

        connection = None
        try:
            connection = ConnectionFactory.create_connection(self.instance)
        except CONNECTION_EXCEPTIONS as exc:
            self._connection_failed = True
            self._connection_error = str(exc)
            self.logger.exception(
                "accounts_sync_connection_init_failed",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                db_type=self.instance.db_type,
                error=self._connection_error,
                module=MODULE,
            )

        if not connection:
            self._connection_failed = True
            if not self._connection_error:
                self._connection_error = "不支持的数据库类型"
                self.logger.error(
                    "accounts_sync_connection_unsupported",
                    instance_id=self.instance.id,
                    instance_name=self.instance.name,
                    db_type=self.instance.db_type,
                    module=MODULE,
                )
            return False

        try:
            is_connected = connection.connect()
        except CONNECTION_EXCEPTIONS as exc:
            self._connection_failed = True
            self._connection_error = str(exc)
            self.logger.exception(
                "accounts_sync_connection_exception",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                db_type=self.instance.db_type,
                error=self._connection_error,
                module=MODULE,
            )
            return False

        if is_connected:
            self._connection = connection
            self._connection_failed = False
            self._connection_error = None
            self.logger.info(
                "accounts_sync_connection_success",
                module=MODULE,
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                db_type=self.instance.db_type,
            )
            return True

        self._connection_failed = True
        self._connection_error = "连接返回失败"
        self.logger.error(
            "accounts_sync_connection_failed",
            instance_id=self.instance.id,
            instance_name=self.instance.name,
            db_type=self.instance.db_type,
            module=MODULE,
        )
        return False

    def disconnect(self) -> None:
        """断开数据库连接并清理资源.

        Returns:
            None

        """
        if self._connection:
            try:
                self._connection.disconnect()
            finally:
                self._connection = None
                self.logger.info(
                    "accounts_sync_connection_closed",
                    module=MODULE,
                    instance_id=self.instance.id,
                    instance_name=self.instance.name,
                )

    def _ensure_connection(self) -> None:
        """确保数据库连接有效,如果无效则尝试重新连接.

        Returns:
            None: 连接有效或成功重连后返回.

        Raises:
            RuntimeError: 当连接失败时抛出,包含连接错误信息.

        """
        if (not self._connection or not getattr(self._connection, "is_connected", False)) and not self.connect():
            error_message = self._connection_error or "数据库连接未建立"
            raise RuntimeError(error_message)

    # ------------------------------------------------------------------
    # 同步阶段
    # ------------------------------------------------------------------
    def fetch_remote_accounts(self) -> list[RemoteAccount]:
        """从远程数据库获取账户列表.

        使用缓存机制,同一实例的账户列表只获取一次.
        确保连接有效后,通过适配器获取账户数据.

        Returns:
            账户字典列表,每个字典包含账户的基本信息.

        Raises:
            RuntimeError: 当数据库连接失败时抛出.

        """
        if self._cached_accounts is None:
            self._ensure_connection()
            self.logger.info(
                "accounts_sync_fetch_remote_accounts_start",
                module=MODULE,
                instance_id=self.instance.id,
                instance_name=self.instance.name,
            )
            raw_accounts = self._adapter.fetch_remote_accounts(self.instance, self._connection) or []
            self._cached_accounts = list(raw_accounts)
            self._enriched_usernames.clear()
            self.logger.info(
                "accounts_sync_fetch_remote_accounts_completed",
                module=MODULE,
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                total_accounts=len(self._cached_accounts),
            )
        return self._cached_accounts

    def synchronize_inventory(self) -> InventorySummary:
        """执行清单阶段同步,同步账户基本信息.

        获取远程账户列表,与本地数据库对比,创建新账户、刷新现有账户、
        标记活跃/非活跃状态.同步结果会缓存活跃账户列表供权限阶段使用.

        Returns:
            清单同步结果字典,格式如下:
            {
                'status': 'completed',
                'created': 5,           # 新建账户数
                'refreshed': 10,        # 刷新账户数
                'reactivated': 2,       # 重新激活账户数
                'deactivated': 3,       # 停用账户数
                'processed_records': 20,
                'total_remote': 20,
                'active_accounts': ['user1', 'user2', ...],
                'active_count': 17
            }

        Raises:
            RuntimeError: 当数据库连接失败时抛出.

        """
        remote_accounts = self.fetch_remote_accounts()
        summary, active_accounts = self._inventory_manager.synchronize(self.instance, remote_accounts)
        inventory_summary: InventorySummary = {
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
            "accounts_sync_inventory_completed",
            module=MODULE,
            phase="inventory",
            instance_id=self.instance.id,
            instance_name=self.instance.name,
            **{k: v for k, v in inventory_summary.items() if k != "active_accounts"},
        )
        return inventory_summary

    def synchronize_permissions(self, *, session_id: str | None = None) -> CollectionSummary:
        """执行权限阶段同步,同步活跃账户的权限信息.

        如果清单阶段未执行,会先自动执行清单同步.
        只为活跃账户同步权限信息,跳过非活跃账户.
        按需补全权限信息(enrich_permissions),避免重复获取.

        Args:
            session_id: 可选的同步会话 ID,用于关联日志和错误追踪.

        Returns:
            权限同步结果字典,格式如下:
            {
                'status': 'completed',  # 或 'skipped'
                'created': 15,          # 新建权限记录数
                'updated': 5,           # 更新权限记录数
                'skipped': 2,           # 跳过记录数
                'processed_records': 20,
                'errors': [],           # 错误列表
                'message': '同步完成'
            }

        Raises:
            RuntimeError: 当数据库连接失败时抛出.
            PermissionSyncError: 当权限同步失败时抛出,包含详细错误信息.

        """
        remote_accounts = self.fetch_remote_accounts()
        active_accounts = getattr(self, "_active_accounts_cache", None)
        if active_accounts is None:
            summary, active_accounts = self._inventory_manager.synchronize(self.instance, remote_accounts)
            self._active_accounts_cache = active_accounts
            self.logger.info(
                "accounts_sync_inventory_rehydrated",
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
            collection_summary: CollectionSummary = {
                "status": "skipped",
                "processed_records": 0,
                "created": 0,
                "updated": 0,
                "skipped": len(remote_accounts),
                "message": "未检测到活跃账户,跳过权限同步",
                "errors": [],
            }
            self.logger.info(
                "accounts_sync_collection_skipped_no_active_accounts",
                module=MODULE,
                phase="collection",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                skipped=len(remote_accounts),
            )
            return collection_summary

        # 在进入权限阶段前按需补全权限信息
        active_usernames = [account.username for account in active_accounts if getattr(account, "username", None)]
        enriched_usernames = getattr(self, "_enriched_usernames", set())
        pending_usernames = [
            username for username in active_usernames if username and username not in enriched_usernames
        ]
        if pending_usernames:
            self._ensure_connection()
            self._cached_accounts = self._adapter.enrich_permissions(
                self.instance,
                self._connection,
                self._cached_accounts,
                usernames=pending_usernames,
            )
            enriched_usernames.update(pending_usernames)
            self._enriched_usernames = enriched_usernames

        try:
            summary = self._permission_manager.synchronize(
                self.instance,
                remote_accounts,
                active_accounts,
                session_id=session_id,
            )
        except PermissionSyncError as exc:
            error_summary = exc.summary
            self.logger.exception(
                "accounts_sync_collection_failed",
                module=MODULE,
                phase="collection",
                instance_id=self.instance.id,
                instance_name=self.instance.name,
                errors=error_summary.get("errors"),
                session_id=session_id,
                message=error_summary.get("message"),
            )
            raise

        collection_summary: CollectionSummary = {
            "status": "completed",
            "created": summary.get("created", 0),
            "updated": summary.get("updated", 0),
            "skipped": summary.get("skipped", 0),
            "processed_records": summary.get(
                "processed_records",
                summary.get("created", 0) + summary.get("updated", 0),
            ),
            "errors": summary.get("errors", []),
            "message": summary.get("message"),
        }
        self.logger.info(
            "accounts_sync_collection_completed",
            module=MODULE,
            phase="collection",
            instance_id=self.instance.id,
            instance_name=self.instance.name,
            **collection_summary,
        )
        return collection_summary

    def sync_all(self, *, session_id: str | None = None) -> SyncStagesSummary:
        """执行完整的两阶段同步流程.

        依次执行清单阶段和权限阶段,返回两个阶段的汇总结果.

        Args:
            session_id: 可选的同步会话 ID,用于关联日志和错误追踪.

        Returns:
            包含两个阶段结果的字典,格式如下:
            {
                'inventory': {...},    # synchronize_inventory 的返回值
                'collection': {...}    # synchronize_permissions 的返回值
            }

        Raises:
            RuntimeError: 当数据库连接失败时抛出.
            PermissionSyncError: 当权限同步失败时抛出.

        """
        inventory_summary = self.synchronize_inventory()
        permissions_summary = self.synchronize_permissions(session_id=session_id)
        return {
            "inventory": inventory_summary,
            "collection": permissions_summary,
        }
