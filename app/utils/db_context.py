"""
鲸落 - 数据库连接上下文管理器
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from app.models.instance import Instance
from app.services.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


class DatabaseContextManager:
    """数据库连接上下文管理器"""

    def __init__(self):
        # 使用连接工厂创建连接
        pass

    @contextmanager
    def get_connection(self, instance: Instance) -> Generator[Any | None]:
        """
        获取数据库连接的上下文管理器

        Args:
            instance: 数据库实例

        Yields:
            Optional[Any]: 数据库连接对象
        """
        connection = None
        try:
            connection = ConnectionFactory.create_connection(instance)
            if not connection:
                logger.error("无法获取数据库连接: {instance.name}")
                yield None
                return

            logger.debug("获取数据库连接成功: {instance.name}")
            yield connection

        except Exception:
            logger.error("数据库连接上下文管理器错误: {str(e)}")
            yield None
        finally:
            if connection:
                try:
                    if hasattr(connection, "disconnect"):
                        connection.disconnect()
                    elif hasattr(connection, "close"):
                        connection.close()
                    logger.debug("关闭数据库连接: {instance.name}")
                except Exception as e:
                    logger.warning("关闭数据库连接失败: %s", str(e) if e else "未知错误")

    @contextmanager
    def execute_query(self, instance: Instance, query: str, params: tuple = None) -> Generator[dict]:
        """
        执行查询的上下文管理器

        Args:
            instance: 数据库实例
            query: SQL查询
            params: 查询参数

        Yields:
            dict: 查询结果
        """
        try:
            result = self.db_service.execute_query(instance, query, params)
            yield result
        except Exception as e:
            logger.error("执行查询失败: {str(e)}")
            yield {"success": False, "error": str(e)}

    @contextmanager
    def transaction(self, instance: Instance) -> Generator[Any | None]:
        """
        数据库事务上下文管理器

        Args:
            instance: 数据库实例

        Yields:
            Optional[Any]: 数据库连接对象
        """
        connection = None
        try:
            connection = ConnectionFactory.create_connection(instance)
            if not connection:
                logger.error("无法获取数据库连接进行事务: {instance.name}")
                yield None
                return

            # 开始事务
            if hasattr(connection, "begin"):
                connection.begin()
            elif hasattr(connection, "autocommit"):
                connection.autocommit = False

            logger.debug("开始数据库事务: {instance.name}")
            yield connection

            # 提交事务
            if hasattr(connection, "commit"):
                connection.commit()
            logger.debug("提交数据库事务: {instance.name}")

        except Exception:
            # 回滚事务
            if connection:
                try:
                    if hasattr(connection, "rollback"):
                        connection.rollback()
                    logger.debug("回滚数据库事务: {instance.name}")
                except Exception:
                    logger.error("回滚事务失败: {rollback_error}")

            logger.error("数据库事务错误: {str(e)}")
            yield None
        finally:
            if connection:
                try:
                    # 恢复自动提交
                    if hasattr(connection, "autocommit"):
                        connection.autocommit = True
                    if hasattr(connection, "disconnect"):
                        connection.disconnect()
                    elif hasattr(connection, "close"):
                        connection.close()
                except Exception:
                    logger.warning("清理数据库连接失败: {str(e)}")


# 全局数据库上下文管理器
db_context = DatabaseContextManager()


# 便捷函数
@contextmanager
def get_db_connection(instance: Instance) -> Generator[Any | None]:
    """获取数据库连接的便捷函数"""
    with db_context.get_connection(instance) as conn:
        yield conn


@contextmanager
def execute_db_query(instance: Instance, query: str, params: tuple = None) -> Generator[dict]:
    """执行数据库查询的便捷函数"""
    with db_context.execute_query(instance, query, params) as result:
        yield result


@contextmanager
def db_transaction(instance: Instance) -> Generator[Any | None]:
    """数据库事务的便捷函数"""
    with db_context.transaction(instance) as conn:
        yield conn
