"""鲸落 - 数据库连接测试服务."""

from typing import Any

from app import db
from app.models import Instance
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils
from app.utils.version_parser import DatabaseVersionParser


class ConnectionTestService:
    """数据库连接测试服务.

    负责测试数据库实例的连接状态,获取版本信息,并更新实例的连接时间.

    Attributes:
        test_logger: 同步日志记录器.

    Example:
        >>> service = ConnectionTestService()
        >>> result = service.test_connection(instance)
        >>> result['success']
        True

    """

    def __init__(self) -> None:
        """初始化连接测试服务."""
        self.test_logger = get_sync_logger()

    def test_connection(self, instance: Instance) -> dict[str, Any]:
        """测试数据库连接.

        创建数据库连接,获取版本信息,并更新实例的连接状态.

        Args:
            instance: 数据库实例对象.

        Returns:
            测试结果字典,包含以下字段:
            - success: 连接是否成功
            - message/error: 成功消息或错误信息
            - version: 格式化的版本字符串(成功时)
            - database_version: 原始版本字符串(成功时)
            - main_version: 主版本号(成功时)
            - detailed_version: 详细版本号(成功时)

        Example:
            >>> service = ConnectionTestService()
            >>> result = service.test_connection(instance)
            >>> if result['success']:
            ...     print(f"版本: {result['version']}")

        """
        connection_obj: Any | None = None
        try:
            # 创建连接
            connection_obj = ConnectionFactory.create_connection(instance)
            if not connection_obj or not connection_obj.connect():
                self._update_last_connected(instance)
                return {"success": False, "error": "无法建立数据库连接"}

            # 获取数据库版本信息
            version_info = connection_obj.get_version() or "未知版本"

            parsed_version = DatabaseVersionParser.parse_version(instance.db_type.lower(), version_info)
            formatted_version = DatabaseVersionParser.format_version_display(
                instance.db_type.lower(), version_info,
            )

            instance.last_connected = time_utils.now()
            instance.database_version = parsed_version["original"]
            instance.main_version = parsed_version["main_version"]
            instance.detailed_version = parsed_version["detailed_version"]

            db.session.commit()

            return {
                "success": True,
                "message": f"连接成功,数据库版本: {formatted_version}",
                "version": formatted_version,
                "database_version": instance.database_version,
                "main_version": instance.main_version,
                "detailed_version": instance.detailed_version,
            }

        except Exception as e:
            # 即使连接失败,也记录尝试时间
            self._update_last_connected(instance)

            # 记录具体的错误类型用于安全分析
            error_type = type(e).__name__
            error_message = str(e)

            # 检查是否可能是SQL注入攻击
            suspicious_patterns = [
                "union", "select", "insert", "update", "delete", "drop", "create",
                "alter", "exec", "execute", "script", "javascript", "vbscript",
            ]

            is_suspicious = any(pattern in error_message.lower() for pattern in suspicious_patterns)

            if is_suspicious:
                self.test_logger.warning(
                    "检测到可疑的数据库错误,可能存在安全威胁",
                    module="connection_test",
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                    error_type=error_type,
                    error_message=error_message,
                    security_alert=True,
                )
            else:
                self.test_logger.exception(
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
        finally:
            if connection_obj is not None:
                try:
                    connection_obj.disconnect()
                except Exception as close_error:
                    self.test_logger.warning(
                        "关闭数据库连接时发生错误",
                        module="connection_test",
                        instance_id=instance.id,
                        error=str(close_error),
                    )

    def _update_last_connected(self, instance: Instance) -> None:
        """更新最后连接时间.

        更新实例的最后连接时间戳,不影响已有的版本信息.

        Args:
            instance: 数据库实例对象.

        Returns:
            None

        """
        try:
            instance.last_connected = time_utils.now()
            db.session.commit()
        except Exception as update_error:
            db.session.rollback()
            self.test_logger.exception(
                "更新最后连接时间失败",
                module="connection_test",
                instance_id=instance.id,
                error=str(update_error),
            )

    # `_get_database_version` 已移除,版本查询由各适配器自行实现.


# 创建全局实例
connection_test_service = ConnectionTestService()
