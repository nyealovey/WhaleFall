"""
鲸落 - 数据库连接测试服务
"""

from typing import Any

from app.models import Instance
from app.services.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_sync_logger


class ConnectionTestService:
    """数据库连接测试服务"""

    def __init__(self) -> None:
        self.test_logger = get_sync_logger()

    def test_connection(self, instance: Instance) -> dict[str, Any]:
        """
        测试数据库连接

        Args:
            instance: 数据库实例

        Returns:
            测试结果
        """
        try:
            # 创建连接
            connection_obj = ConnectionFactory.create_connection(instance)
            if not connection_obj.connect():
                return {"success": False, "error": "无法建立数据库连接"}

            # 获取数据库版本信息
            version_info = self._get_database_version(instance, connection_obj)

            # 更新最后连接时间
            from app import db
            from app.utils.timezone import now

            instance.last_connected = now()
            db.session.commit()

            # 关闭连接
            if hasattr(connection_obj, "disconnect"):
                connection_obj.disconnect()
            elif hasattr(connection_obj, "close"):
                connection_obj.close()

            return {
                "success": True,
                "message": f"连接成功，数据库版本: {version_info}",
                "version": version_info,
            }

        except Exception as e:
            # 即使连接失败，也记录尝试时间
            try:
                from app import db
                from app.utils.timezone import now

                instance.last_connected = now()
                db.session.commit()
            except Exception as update_error:
                self.test_logger.error(f"更新最后连接时间失败: {update_error}")

            # 记录具体的错误类型用于安全分析
            error_type = type(e).__name__
            error_message = str(e)
            
            # 检查是否可能是SQL注入攻击
            suspicious_patterns = [
                "union", "select", "insert", "update", "delete", "drop", "create",
                "alter", "exec", "execute", "script", "javascript", "vbscript"
            ]
            
            is_suspicious = any(pattern in error_message.lower() for pattern in suspicious_patterns)
            
            if is_suspicious:
                self.test_logger.warning(
                    "检测到可疑的数据库错误，可能存在安全威胁",
                    module="connection_test",
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                    error_type=error_type,
                    error_message=error_message,
                    security_alert=True
                )
            else:
                self.test_logger.error(
                    "数据库连接测试失败",
                    module="connection_test",
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                    error_type=error_type,
                    error_message=error_message,
                )

            return {"success": False, "error": f"连接失败: {error_message}"}

    def _get_database_version(self, instance: Instance, connection: Any) -> str:  # noqa: ANN401
        """
        获取数据库版本信息

        Args:
            instance: 数据库实例
            connection: 数据库连接

        Returns:
            版本信息字符串
        """
        try:
            if instance.db_type == "mysql":
                result = connection.execute_query("SELECT VERSION()")
                return result[0][0] if result else "未知版本"
            if instance.db_type == "postgresql":
                result = connection.execute_query("SELECT version()")
                return result[0][0] if result else "未知版本"
            if instance.db_type == "sqlserver":
                result = connection.execute_query("SELECT @@VERSION")
                return result[0][0] if result else "未知版本"
            if instance.db_type == "oracle":
                result = connection.execute_query("SELECT * FROM v$version WHERE rownum = 1")
                return result[0][0] if result else "未知版本"
            return "未知数据库类型"
        except Exception as e:
            # 记录具体的错误类型
            error_type = type(e).__name__
            error_message = str(e)
            
            # 检查是否可能是SQL注入攻击
            suspicious_patterns = [
                "union", "select", "insert", "update", "delete", "drop", "create",
                "alter", "exec", "execute", "script", "javascript", "vbscript"
            ]
            
            is_suspicious = any(pattern in error_message.lower() for pattern in suspicious_patterns)
            
            if is_suspicious:
                self.test_logger.warning(
                    "检测到可疑的版本查询错误，可能存在安全威胁",
                    module="connection_test",
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    error_type=error_type,
                    error_message=error_message,
                    security_alert=True
                )
            else:
                self.test_logger.warning(
                    "获取数据库版本失败",
                    module="connection_test",
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    error_type=error_type,
                    error_message=error_message,
                )
            return "版本获取失败"


# 创建全局实例
connection_test_service = ConnectionTestService()
