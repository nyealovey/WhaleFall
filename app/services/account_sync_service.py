"""
泰摸鱼吧 - 账户同步服务
统一处理手动同步和定时任务的账户同步逻辑
"""

# 可选导入数据库驱动
try:
    import psycopg
except ImportError:
    psycopg = None

try:
    import pyodbc
except ImportError:
    pyodbc = None

try:
    import oracledb
except ImportError:
    oracledb = None

from typing import Any

from app import db
from app.models import Instance
from app.services.sync_data_manager import SyncDataManager
from app.utils.structlog_config import get_sync_logger
from app.utils.timezone import now


class AccountSyncService:
    """账户同步服务 - 统一处理所有账户同步逻辑"""

    def __init__(self) -> None:
        self.sync_logger = get_sync_logger()

    def sync_accounts(self, instance: Instance, sync_type: str = "batch", session_id: str = None) -> dict[str, Any]:
        """
        同步账户信息 - 统一入口

        Args:
            instance: 数据库实例
            sync_type: 同步类型 ('batch' 或 'task')
            session_id: 同步会话ID（可选）

        Returns:
            Dict: 同步结果
        """
        try:
            self.sync_logger.info(
                "开始账户同步",
                module="account_sync",
                instance_name=instance.name,
                db_type=instance.db_type,
                sync_type=sync_type,
                session_id=session_id,
            )

            # 获取数据库连接
            conn = self._get_connection(instance)
            if not conn:
                error_msg = "无法获取数据库连接"
                self.sync_logger.error(
                    "无法获取数据库连接",
                    module="account_sync",
                    instance_name=instance.name,
                    db_type=instance.db_type,
                )
                return {"success": False, "error": error_msg}

            # 使用SyncDataManager进行同步
            if not session_id:
                import uuid

                session_id = str(uuid.uuid4())

            sync_manager = SyncDataManager()

            # 根据数据库类型执行同步
            self.sync_logger.info(
                "开始数据库账户同步",
                module="account_sync",
                instance_name=instance.name,
                db_type=instance.db_type,
            )

            if instance.db_type == "mysql":
                result = sync_manager.sync_mysql_accounts(instance, conn, session_id)
            elif instance.db_type == "postgresql":
                self.sync_logger.info(
                    "调用PostgreSQL账户同步函数",
                    module="account_sync",
                    instance_name=instance.name,
                )
                result = sync_manager.sync_postgresql_accounts(instance, conn, session_id)
                self.sync_logger.info(
                    "PostgreSQL同步完成",
                    module="account_sync",
                    instance_name=instance.name,
                    synced_count=result.get("synced_count", 0),
                )
            elif instance.db_type == "sqlserver":
                result = sync_manager.sync_sqlserver_accounts(instance, conn, session_id)
            elif instance.db_type == "oracle":
                result = sync_manager.sync_oracle_accounts(instance, conn, session_id)
            else:
                error_msg = f"不支持的数据库类型: {instance.db_type}"
                self.sync_logger.warning(
                    "不支持的数据库类型",
                    module="account_sync",
                    instance_name=instance.name,
                    db_type=instance.db_type,
                )
                return {
                    "success": False,
                    "error": error_msg,
                }

            synced_count = result["synced_count"]
            added_count = result["added_count"]
            removed_count = result["removed_count"]
            modified_count = result["modified_count"]

            # 计算变化
            from app.models.current_account_sync_data import CurrentAccountSyncData

            after_count = CurrentAccountSyncData.query.filter_by(
                instance_id=instance.id, db_type=instance.db_type
            ).count()
            net_change = after_count - (before_count := 0)  # 简化计算

            # 创建同步报告记录（定时任务跳过单个实例记录，只创建聚合记录）
            if sync_type == "batch":
                # 移除SyncData导入，使用新的同步会话模型
                # 同步会话记录已通过sync_session_service管理，无需额外创建记录
                pass

            # 更新实例的最后连接时间
            instance.last_connected_at = now()
            db.session.commit()

            self.sync_logger.info(
                "账户同步完成",
                module="account_sync",
                instance_name=instance.name,
                synced_count=synced_count,
                added_count=added_count,
                removed_count=removed_count,
                modified_count=modified_count,
                net_change=net_change,
            )

            return {
                "success": True,
                "message": f"成功同步 {synced_count} 个账户",
                "synced_count": synced_count,
                "added_count": added_count,
                "removed_count": removed_count,
                "modified_count": modified_count,
                "net_change": net_change,
                "session_id": session_id,
            }

        except Exception as e:
            self.sync_logger.error(
                "账户同步失败",
                module="account_sync",
                instance_name=instance.name,
                db_type=instance.db_type,
                error=str(e),
            )
            return {"success": False, "error": f"账户同步失败: {str(e)}"}

    def _get_connection(self, instance: Instance) -> Any | None:
        """
        获取数据库连接

        Args:
            instance: 数据库实例

        Returns:
            数据库连接对象或None
        """
        try:
            from app.services.connection_factory import ConnectionFactory

            connection_obj = ConnectionFactory.create_connection(instance)
            if connection_obj.connect():
                return connection_obj
            return None

        except Exception as e:
            self.sync_logger.error(
                "获取数据库连接失败",
                module="account_sync",
                instance_name=instance.name,
                db_type=instance.db_type,
                error=str(e),
            )
            return None

    def _get_account_snapshot(self, instance: Instance) -> dict[str, Any]:
        """
        获取同步前的账户快照

        Args:
            instance: 数据库实例

        Returns:
            账户快照字典
        """
        try:
            from app.models.current_account_sync_data import CurrentAccountSyncData

            # 获取优化同步数据表的快照
            existing_accounts = CurrentAccountSyncData.query.filter_by(
                instance_id=instance.id, db_type=instance.db_type, is_deleted=False
            ).all()

            snapshot = {}
            for account in existing_accounts:
                key = f"{account.username}"
                snapshot[key] = {
                    "id": account.id,
                    "username": account.username,
                    "is_superuser": account.is_superuser,
                    "last_sync_time": account.last_sync_time,
                    "last_change_time": account.last_change_time,
                }

            self.sync_logger.info(
                "获取账户快照完成",
                module="account_sync",
                instance_name=instance.name,
                snapshot_count=len(snapshot),
            )

            return snapshot

        except Exception as e:
            self.sync_logger.error(
                "获取账户快照失败",
                module="account_sync",
                instance_name=instance.name,
                error=str(e),
            )
            return {}


# 创建服务实例
account_sync_service = AccountSyncService()
