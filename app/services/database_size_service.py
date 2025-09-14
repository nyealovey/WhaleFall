"""
泰摸鱼吧 - 数据库大小同步服务
统一处理手动同步和定时任务的数据库大小同步逻辑
"""

import logging
from typing import Any

import pymysql

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

from app import db
from app.models import Instance
from app.utils.timezone import now


class DatabaseSizeService:
    """数据库大小同步服务"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def sync_database_size(self, instance: Instance, sync_type: str = "batch") -> dict[str, Any]:
        """
        同步数据库大小信息 - 统一入口

        Args:
            instance: 数据库实例
            sync_type: 同步类型 ('batch' 或 'task')

        Returns:
            Dict: 同步结果
        """
        try:
            # 获取数据库连接
            conn = self._get_connection(instance)
            if not conn:
                return {"success": False, "error": "无法获取数据库连接"}

            # 根据数据库类型获取大小信息
            if instance.db_type == "mysql":
                result = self._get_mysql_size(instance, conn)
            elif instance.db_type == "postgresql":
                result = self._get_postgresql_size(instance, conn)
            elif instance.db_type == "sqlserver":
                result = self._get_sqlserver_size(instance, conn)
            elif instance.db_type == "oracle":
                result = self._get_oracle_size(instance, conn)
            else:
                return {
                    "success": False,
                    "error": f"不支持的数据库类型: {instance.db_type}",
                }

            if result["success"]:
                # 更新实例的大小信息
                instance.database_size = result["database_size"]
                instance.updated_at = now()
                db.session.commit()

            return result

        except Exception as e:
            self.logger.error(f"数据库大小同步失败: {str(e)}")
            return {
                "success": False,
                "error": f"{instance.db_type.upper()}数据库大小同步失败: {str(e)}",
                "database_size": 0,
            }

    def _get_connection(self, instance: Instance) -> "Any | None":
        """获取数据库连接"""
        try:
            if instance.db_type == "mysql":
                return pymysql.connect(
                    host=instance.host,
                    port=instance.port,
                    database=instance.database_name or "mysql",
                    user=instance.credential.username,
                    password=instance.credential.get_plain_password(),
                )
            if instance.db_type == "postgresql":
                if psycopg is None:
                    error_msg = "psycopg模块未安装，无法连接PostgreSQL"
                    raise ImportError(error_msg)
                return psycopg.connect(
                    host=instance.host,
                    port=instance.port,
                    dbname=instance.database_name or "postgres",
                    user=instance.credential.username,
                    password=instance.credential.get_plain_password(),
                )
            if instance.db_type == "sqlserver":
                if pyodbc is None:
                    error_msg = "pyodbc模块未安装，无法连接SQL Server"
                    raise ImportError(error_msg)
                return pyodbc.connect(
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={instance.host},{instance.port};"
                    f"DATABASE={instance.database_name or 'master'};"
                    f"UID={instance.credential.username};"
                    f"PWD={instance.credential.get_plain_password()}"
                )
            if instance.db_type == "oracle":
                if oracledb is None:
                    error_msg = "oracledb模块未安装，无法连接Oracle"
                    raise ImportError(error_msg)

                # 优先使用Thick模式连接（适用于所有Oracle版本，包括11g）
                try:
                    # 初始化Thick模式（需要Oracle Instant Client）
                    oracledb.init_oracle_client()
                    return oracledb.connect(
                        user=instance.credential.username,
                        password=instance.credential.get_plain_password(),
                        dsn=f"{instance.host}:{instance.port}/{instance.database_name or 'ORCL'}",
                    )
                except oracledb.DatabaseError as e:
                    # 如果Thick模式失败，尝试Thin模式（适用于Oracle 12c+）
                    if "DPI-1047" in str(e) or "Oracle Client library" in str(e):
                        # Thick模式失败，尝试Thin模式
                        try:
                            return oracledb.connect(
                                user=instance.credential.username,
                                password=instance.credential.get_plain_password(),
                                dsn=f"{instance.host}:{instance.port}/{instance.database_name or 'ORCL'}",
                            )
                        except oracledb.DatabaseError:
                            # 如果Thin模式也失败，抛出原始错误
                            raise e
                    else:
                        raise
            else:
                return None
        except Exception as e:
            self.logger.error(f"数据库连接失败: {str(e)}")
            return None

    def _get_mysql_size(self, instance: Instance, conn: "Any") -> dict[str, Any]:
        """获取MySQL数据库大小"""
        cursor = conn.cursor()

        try:
            # 查询数据库大小
            cursor.execute(
                """
                SELECT
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
                FROM information_schema.tables
                WHERE table_schema = %s
            """,
                (instance.database_name or "mysql",),
            )

            result = cursor.fetchone()
            size_mb = result[0] if result and result[0] else 0

            cursor.close()
            conn.close()

            return {
                "success": True,
                "message": f"成功获取MySQL数据库大小: {size_mb} MB",
                "database_size": size_mb,
            }

        except Exception as e:
            cursor.close()
            conn.close()
            raise e

    def _get_postgresql_size(self, instance: Instance, conn: "Any") -> dict[str, Any]:
        """获取PostgreSQL数据库大小"""
        cursor = conn.cursor()

        try:
            # 查询数据库大小
            cursor.execute(
                """
                SELECT pg_size_pretty(pg_database_size(%s)) as size,
                       pg_database_size(%s) / 1024 / 1024 as size_mb
            """,
                ("postgres", "postgres"),
            )  # PostgreSQL默认数据库

            result = cursor.fetchone()
            size_mb = result[1] if result and result[1] else 0

            cursor.close()
            conn.close()

            return {
                "success": True,
                "message": f"成功获取PostgreSQL数据库大小: {size_mb:.2f} MB",
                "database_size": round(size_mb, 2),
            }

        except Exception as e:
            cursor.close()
            conn.close()
            raise e

    def _get_sqlserver_size(self, instance: Instance, conn: "Any") -> dict[str, Any]:
        """获取SQL Server数据库大小"""
        cursor = conn.cursor()

        try:
            # 查询数据库大小
            cursor.execute(
                """
                SELECT
                    SUM(size * 8.0 / 1024) AS size_mb
                FROM sys.master_files
                WHERE database_id = DB_ID(?)
            """,
                (instance.database_name or "master",),
            )

            result = cursor.fetchone()
            size_mb = result[0] if result and result[0] else 0

            cursor.close()
            conn.close()

            return {
                "success": True,
                "message": f"成功获取SQL Server数据库大小: {size_mb:.2f} MB",
                "database_size": round(size_mb, 2),
            }

        except Exception as e:
            cursor.close()
            conn.close()
            raise e

    def _get_oracle_size(self, instance: Instance, conn: "Any") -> dict[str, Any]:
        """获取Oracle数据库大小"""
        cursor = conn.cursor()

        try:
            # 查询数据库大小
            cursor.execute(
                """
                SELECT
                    ROUND(SUM(bytes) / 1024 / 1024, 2) AS size_mb
                FROM dba_data_files
                UNION ALL
                SELECT
                    ROUND(SUM(bytes) / 1024 / 1024, 2) AS size_mb
                FROM dba_temp_files
                UNION ALL
                SELECT
                    ROUND(SUM(bytes) / 1024 / 1024, 2) AS size_mb
                FROM v$log
            """
            )

            results = cursor.fetchall()
            total_size_mb = sum(result[0] for result in results if result[0])

            cursor.close()
            conn.close()

            return {
                "success": True,
                "message": f"成功获取Oracle数据库大小: {total_size_mb:.2f} MB",
                "database_size": round(total_size_mb, 2),
            }

        except Exception as e:
            cursor.close()
            conn.close()
            raise e


# 全局实例
database_size_service = DatabaseSizeService()
