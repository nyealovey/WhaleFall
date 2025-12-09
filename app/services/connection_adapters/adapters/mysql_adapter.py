"""MySQL 数据库连接适配器."""

from __future__ import annotations

from typing import Any

from .base import ConnectionAdapterError, DatabaseConnection, get_default_schema


class MySQLConnection(DatabaseConnection):
    """MySQL 数据库连接."""

    def connect(self) -> bool:
        """建立 MySQL 连接并缓存连接对象.

        Returns:
            bool: 连接成功返回 True,失败返回 False.

        """
        try:
            import pymysql

            password = self.instance.credential.get_plain_password() if self.instance.credential else ""

            self.connection = pymysql.connect(
                host=self.instance.host,
                port=self.instance.port,
                database=self.instance.database_name or get_default_schema("mysql"),
                user=(self.instance.credential.username if self.instance.credential else ""),
                password=password,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=20,
                read_timeout=300,
                write_timeout=300,
                sql_mode="TRADITIONAL",
            )
            self.is_connected = True
            return True
        except Exception as exc:
            self.db_logger.exception(
                "MySQL连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="MySQL",
                error=str(exc),
            )
            return False

    def disconnect(self) -> None:
        """关闭当前连接并复位状态标识.

        Returns:
            None

        """
        if self.connection:
            try:
                self.connection.close()
            except Exception as exc:
                self.db_logger.exception(
                    "MySQL断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="MySQL",
                    error=str(exc),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, Any]:
        """快速测试数据库连通性并返回版本信息."""
        try:
            if not self.connect():
                return {"success": False, "error": "无法建立连接"}

            version = self.get_version()
            return {
                "success": True,
                "message": f"MySQL连接成功 (主机: {self.instance.host}:{self.instance.port}, 版本: {version or '未知'})",
                "database_version": version,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        finally:
            self.disconnect()

    def execute_query(self, query: str, params: tuple | None = None) -> Any:
        """执行 SQL 查询并返回全部结果.

        Args:
            query: 待执行的 SQL 语句.
            params: 绑定参数元组.

        Returns:
            Any: pymysql `fetchall` 的结果.

        """
        if not self.is_connected and not self.connect():
            msg = "无法建立数据库连接"
            raise ConnectionAdapterError(msg)

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        """查询数据库版本.

        Returns:
            str | None: 成功时返回版本字符串,否则 None.

        """
        try:
            result = self.execute_query("SELECT VERSION()")
            if result:
                return result[0][0]
            return None
        except Exception:
            return None
