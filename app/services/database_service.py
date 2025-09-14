"""
泰摸鱼吧 - 数据库服务
提供数据库连接管理和同步功能
"""

from typing import Any

from app.models.instance import Instance
from app.services.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_db_logger


class DatabaseService:
    """数据库连接管理服务"""

    def __init__(self) -> None:
        self.db_logger = get_db_logger()
        self.connections = {}  # 连接池

    def get_connection(self, instance: Instance) -> Any | None:
        """
        获取数据库连接

        Args:
            instance: 数据库实例

        Returns:
            数据库连接对象或None
        """
        try:
            # 如果已有连接，直接返回
            if instance.id in self.connections:
                return self.connections[instance.id]

            # 创建新连接
            connection_obj = ConnectionFactory.create_connection(instance)
            if connection_obj.connect():
                # 存储增强连接对象而不是原始连接
                self.connections[instance.id] = connection_obj
                self.db_logger.info(
                    "数据库连接成功",
                    module="database",
                    operation="database_connect",
                    instance_id=instance.id,
                    db_type=instance.db_type,
                    host=instance.host,
                )
                return connection_obj
            self.db_logger.error(
                "无法建立数据库连接",
                module="database",
                operation="database_connect",
                instance_id=instance.id,
                db_type=instance.db_type,
                host=instance.host,
            )
            return None

        except Exception as e:
            self.db_logger.error(
                "数据库连接异常",
                module="database",
                operation="database_connect",
                instance_id=instance.id,
                db_type=instance.db_type,
                host=instance.host,
                error=str(e),
            )
            return None

    def close_connection(self, instance: Instance) -> None:
        """
        关闭数据库连接

        Args:
            instance: 数据库实例
        """
        try:
            if instance.id in self.connections:
                conn = self.connections[instance.id]
                if conn:
                    # 如果是增强连接对象，调用disconnect方法
                    if hasattr(conn, "disconnect"):
                        conn.disconnect()
                    # 如果是原始连接对象，调用close方法
                    elif hasattr(conn, "close"):
                        conn.close()
                del self.connections[instance.id]
                self.db_logger.info(
                    "数据库连接关闭",
                    module="database",
                    operation="database_disconnect",
                    instance_id=instance.id,
                    db_type=instance.db_type,
                )
        except Exception as e:
            self.db_logger.error(
                "关闭数据库连接失败",
                module="database",
                operation="database_disconnect",
                instance_id=instance.id,
                db_type=instance.db_type,
                error=str(e),
            )
        finally:
            # 确保连接被清理
            if instance.id in self.connections:
                del self.connections[instance.id]

    def test_connection(self, instance: Instance) -> dict[str, Any]:
        """
        测试数据库连接

        Args:
            instance: 数据库实例

        Returns:
            测试结果
        """
        try:
            conn = self.get_connection(instance)
            if not conn:
                return {"success": False, "error": "无法建立数据库连接"}

            # 获取数据库版本信息
            version_info = self.get_database_version(instance, conn)

            # 关闭连接
            self.close_connection(instance)

            return {
                "success": True,
                "message": f"连接成功，数据库版本: {version_info}",
                "version": version_info,
            }

        except Exception as e:
            self.db_logger.error(
                "数据库连接测试失败",
                module="database",
                operation="test_connection",
                instance_id=instance.id,
                db_type=instance.db_type,
                error=str(e),
            )
            return {"success": False, "error": f"连接测试失败: {str(e)}"}

    def get_database_version(self, instance: Instance, conn: Any) -> str | None:
        """
        获取数据库版本信息

        Args:
            instance: 数据库实例
            conn: 数据库连接

        Returns:
            版本信息字符串
        """
        try:
            if hasattr(conn, "get_version"):
                return conn.get_version()
            return "未知版本"
        except Exception as e:
            self.db_logger.error(
                "获取数据库版本失败",
                module="database",
                operation="get_version",
                instance_id=instance.id,
                db_type=instance.db_type,
                error=str(e),
            )
            return "版本获取失败"

    def sync_accounts(self, instance: Instance) -> dict[str, Any]:
        """
        同步账户信息 - 使用优化同步模型

        Args:
            instance: 数据库实例

        Returns:
            Dict: 同步结果
        """
        try:
            import uuid

            from app.services.sync_data_manager import SyncDataManager
            from app.utils.timezone import now

            self.db_logger.info("开始同步账户", instance_name=instance.name, db_type=instance.db_type)

            # 获取数据库连接
            conn = self.get_connection(instance)
            if not conn:
                self.db_logger.error("无法获取数据库连接", instance_name=instance.name)
                return {"success": False, "error": "无法获取数据库连接"}

            # 获取数据库版本信息
            version_info = self.get_database_version(instance, conn)
            if version_info and version_info != instance.database_version:
                from app import db

                instance.database_version = version_info
                db.session.commit()

            # 使用SyncDataManager进行同步
            session_id = str(uuid.uuid4())
            sync_manager = SyncDataManager()

            # 根据数据库类型执行同步
            if instance.db_type == "mysql":
                result = sync_manager.sync_mysql_accounts(instance, conn, session_id)
            elif instance.db_type == "postgresql":
                result = sync_manager.sync_postgresql_accounts(instance, conn, session_id)
            elif instance.db_type == "sqlserver":
                result = sync_manager.sync_sqlserver_accounts(instance, conn, session_id)
            elif instance.db_type == "oracle":
                result = sync_manager.sync_oracle_accounts(instance, conn, session_id)
            else:
                return {
                    "success": False,
                    "error": f"不支持的数据库类型: {instance.db_type}",
                }

            # 更新实例的最后连接时间
            from app import db

            instance.last_connected_at = now()
            db.session.commit()

            # 关闭连接
            self.close_connection(instance)

            self.db_logger.info(
                "账户同步完成",
                instance_name=instance.name,
                synced_count=result.get("synced_count", 0),
                added_count=result.get("added_count", 0),
                removed_count=result.get("removed_count", 0),
                modified_count=result.get("modified_count", 0),
            )

            return {
                "success": True,
                "message": f"成功同步 {result.get('synced_count', 0)} 个账户",
                "synced_count": result.get("synced_count", 0),
                "added_count": result.get("added_count", 0),
                "removed_count": result.get("removed_count", 0),
                "modified_count": result.get("modified_count", 0),
            }

        except Exception as e:
            self.db_logger.error("账户同步失败", instance_name=instance.name, error=str(e))
            return {"success": False, "error": f"账户同步失败: {str(e)}"}
