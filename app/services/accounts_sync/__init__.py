"""账户同步服务模块。.

提供数据库账户的同步功能，包括账户清单管理、权限采集和增量更新。

主要组件：
- AccountSyncService: 账户同步服务（统一入口）
- AccountSyncCoordinator: 账户同步协调器
- AccountInventoryManager: 账户清单管理器
- AccountPermissionManager: 账户权限管理器
- get_accounts_by_instance: 按实例查询账户的辅助函数
"""

from .account_query_service import get_accounts_by_instance
from .accounts_sync_service import AccountSyncService, accounts_sync_service
from .coordinator import AccountSyncCoordinator

__all__ = [
    "AccountSyncCoordinator",
    "AccountSyncService",
    "accounts_sync_service",
    "get_accounts_by_instance",
]
