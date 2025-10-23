"""
鲸落 - 账户数据管理器 (重构版)
通过适配器模式统一调度各数据库类型的账户同步逻辑
"""

from typing import Any

from app.models import Instance
from app.services.account_sync_adapters.mysql_sync_adapter import MySQLSyncAdapter
from app.services.account_sync_adapters.oracle_sync_adapter import OracleSyncAdapter
from app.services.account_sync_adapters.postgresql_sync_adapter import PostgreSQLSyncAdapter
from app.services.account_sync_adapters.sqlserver_sync_adapter import SQLServerSyncAdapter
from app.utils.structlog_config import get_sync_logger


class AccountDataManager:
    """
    账户数据管理器 - 重构版
    使用适配器模式管理不同数据库类型的账户同步逻辑
    支持 MySQL、PostgreSQL、SQL Server、Oracle
    """

    def __init__(self) -> None:
        self.sync_logger = get_sync_logger()
        self._adapters = {
            "mysql": MySQLSyncAdapter(),
            "postgresql": PostgreSQLSyncAdapter(),
            "sqlserver": SQLServerSyncAdapter(),
            "oracle": OracleSyncAdapter(),
        }

        self.sync_logger.info(
            "同步数据管理器初始化完成", module="sync_data_manager", supported_databases=list(self._adapters.keys())
        )

    def sync_accounts(self, instance: Instance, connection: Any, session_id: str) -> dict[str, Any]:
        """
        统一的账户同步入口

        Args:
            instance: 数据库实例
            connection: 数据库连接
            session_id: 会话ID

        Returns:
            Dict: 同步结果
        """
        try:
            # 获取对应的数据库适配器
            adapter = self._get_adapter(instance.db_type)
            if not adapter:
                return {
                    "success": False,
                    "error": f"不支持的数据库类型: {instance.db_type}",
                    "synced_count": 0,
                    "added_count": 0,
                    "modified_count": 0,
                    "removed_count": 0,
                }

            self.sync_logger.info(
                "开始执行账户同步",
                module="sync_data_manager",
                instance_name=instance.name,
                db_type=instance.db_type,
                session_id=session_id,
            )

            # 使用适配器执行同步
            result = adapter.sync_accounts(instance, connection, session_id)

            self.sync_logger.info(
                "账户同步执行完成",
                module="sync_data_manager",
                instance_name=instance.name,
                db_type=instance.db_type,
                session_id=session_id,
                success=result.get("success", False),
                synced_count=result.get("synced_count", 0),
            )

            return result

        except Exception as e:
            self.sync_logger.error(
                "账户同步执行失败",
                module="sync_data_manager",
                instance_name=instance.name,
                db_type=instance.db_type,
                session_id=session_id,
                error=str(e),
            )
            return {
                "success": False,
                "error": f"同步执行失败: {str(e)}",
                "synced_count": 0,
                "added_count": 0,
                "modified_count": 0,
                "removed_count": 0,
            }

    def _get_adapter(self, db_type: str) -> Any:  # noqa: ANN401
        """
        获取数据库类型对应的适配器

        Args:
            db_type: 数据库类型

        Returns:
            对应的同步适配器或None
        """
        adapter = self._adapters.get(db_type.lower())
        if not adapter:
            self.sync_logger.warning(
                "未找到数据库类型的适配器: %s",
                db_type,
                module="sync_data_manager",
                available_types=list(self._adapters.keys()),
            )
        return adapter

    def get_supported_db_types(self) -> list[str]:
        """
        获取支持的数据库类型列表

        Returns:
            List[str]: 支持的数据库类型
        """
        return list(self._adapters.keys())

    @staticmethod
    def get_accounts_by_instance(instance_id: int, *, include_deleted: bool = False) -> list[Any]:  # noqa: ANN401
        """获取实例的所有账户 - 兼容性方法"""
        from app.models.current_account_sync_data import CurrentAccountSyncData

        query = CurrentAccountSyncData.query.filter_by(instance_id=instance_id)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.order_by(CurrentAccountSyncData.username.asc()).all()
