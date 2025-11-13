"""MySQL 数据库连接适配器。"""

from __future__ import annotations

from typing import Any

from .base import DatabaseConnection, get_default_schema


class MySQLConnection(DatabaseConnection):
    """MySQL 数据库连接。"""

    def connect(self) -> bool:
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
        except Exception as exc:  # noqa: BLE001
            self.db_logger.error(
                "MySQL连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="MySQL",
                error=str(exc),
            )
            return False

    def disconnect(self) -> None:
        if self.connection:
            try:
                self.connection.close()
            except Exception as exc:  # noqa: BLE001
                self.db_logger.error(
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
        try:
            if not self.connect():
                return {"success": False, "error": "无法建立连接"}

            version = self.get_version()
            return {
                "success": True,
                "message": f"MySQL连接成功 (主机: {self.instance.host}:{self.instance.port}, 版本: {version or '未知'})",
                "database_version": version,
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}
        finally:
            self.disconnect()

    def execute_query(self, query: str, params: tuple | None = None) -> Any:  # noqa: ANN401
        if not self.is_connected and not self.connect():
            raise Exception("无法建立数据库连接")

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        try:
            result = self.execute_query("SELECT VERSION()")
            if result:
                return result[0][0]
            return None
        except Exception:  # noqa: BLE001
            return None
