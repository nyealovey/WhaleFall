"""鲸落 - 数据库连接测试服务."""

from __future__ import annotations

from uuid import uuid4

from typing import Any

from flask import current_app, has_app_context, has_request_context
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.constants.system_constants import ErrorMessages
from app.models import Instance
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils
from app.utils.version_parser import DatabaseVersionParser

CONNECTION_TEST_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    SQLAlchemyError,
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
    AttributeError,
)


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

    @staticmethod
    def _should_expose_details() -> bool:
        """判断是否允许对外返回诊断详情.

        Returns:
            True 表示允许在结果中追加 details 字段,False 表示仅返回用户可见文案与 error_id.

        """
        if not has_app_context():
            return False
        if bool(getattr(current_app, "debug", False)):
            return True
        if not has_request_context():
            return False
        if not getattr(current_user, "is_authenticated", False):
            return False
        is_admin = getattr(current_user, "is_admin", None)
        return bool(callable(is_admin) and is_admin())

    def test_connection(self, instance: Instance) -> dict[str, Any]:
        """测试数据库连接.

        创建数据库连接,获取版本信息,并更新实例的连接状态.

        Args:
            instance: 数据库实例对象.

        Returns:
            测试结果字典,包含以下字段:
            - success: 连接是否成功
            - message: 结果摘要消息(必填,用于对外展示)
            - error_code: 失败时的错误码(可选,用于对接 UI 或埋点)
            - error_id: 失败时的错误追踪标识(可选,用于定位日志)
            - details: 诊断信息(可选,仅在 debug 或管理员可见)
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
        result: dict[str, Any]
        try:
            # 创建连接
            connection_obj = ConnectionFactory.create_connection(instance)
            if not connection_obj or not connection_obj.connect():
                self._update_last_connected(instance)
                error_id = uuid4().hex
                self.test_logger.warning(
                    "数据库连接测试失败: 无法建立连接",
                    module="connection_test",
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                    error_id=error_id,
                    error_code="CONNECTION_FAILED",
                )
                result = {
                    "success": False,
                    "message": ErrorMessages.DATABASE_CONNECTION_ERROR,
                    "error_code": "CONNECTION_FAILED",
                    "error_id": error_id,
                }
            else:
                # 获取数据库版本信息
                version_info = connection_obj.get_version() or "未知版本"

                parsed_version = DatabaseVersionParser.parse_version(instance.db_type.lower(), version_info)
                formatted_version = DatabaseVersionParser.format_version_display(
                    instance.db_type.lower(),
                    version_info,
                )

                instance.last_connected = time_utils.now()
                instance.database_version = parsed_version["original"]
                instance.main_version = parsed_version["main_version"]
                instance.detailed_version = parsed_version["detailed_version"]

                db.session.commit()

                result = {
                    "success": True,
                    "message": f"连接成功,数据库版本: {formatted_version}",
                    "version": formatted_version,
                    "database_version": instance.database_version,
                    "main_version": instance.main_version,
                    "detailed_version": instance.detailed_version,
                }

        except CONNECTION_TEST_EXCEPTIONS as exc:
            # 即使连接失败,也记录尝试时间
            self._update_last_connected(instance)

            # 记录具体的错误类型用于安全分析
            error_type = type(exc).__name__
            error_message = str(exc)
            error_id = uuid4().hex

            # 检查是否可能是SQL注入攻击
            suspicious_patterns = [
                "union",
                "select",
                "insert",
                "update",
                "delete",
                "drop",
                "create",
                "alter",
                "exec",
                "execute",
                "script",
                "javascript",
                "vbscript",
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
                    error_id=error_id,
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
                    error_id=error_id,
                )

            result = {
                "success": False,
                "message": ErrorMessages.DATABASE_CONNECTION_ERROR,
                "error_code": "CONNECTION_TEST_FAILED",
                "error_id": error_id,
            }
            if self._should_expose_details():
                result["details"] = {"error_type": error_type}
        finally:
            if connection_obj is not None:
                try:
                    connection_obj.disconnect()
                except CONNECTION_TEST_EXCEPTIONS as close_error:
                    self.test_logger.warning(
                        "关闭数据库连接时发生错误",
                        module="connection_test",
                        instance_id=instance.id,
                        error=str(close_error),
                    )
        return result

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
        except SQLAlchemyError as update_error:
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
