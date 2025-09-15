#!/usr/bin/env python3

"""
数据库连接工厂
提供统一的数据库连接创建和管理功能
"""

from abc import ABC, abstractmethod
from typing import Any

from app.models.instance import Instance
from app.utils.database_type_utils import DatabaseTypeUtils
from app.utils.structlog_config import get_db_logger, log_error
from app.utils.version_parser import DatabaseVersionParser


class DatabaseConnection(ABC):
    """数据库连接抽象基类"""

    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self.db_logger = get_db_logger()
        self.connection = None
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """建立数据库连接"""

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据库连接"""

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """测试数据库连接"""

    @abstractmethod
    def execute_query(self, query: str, params: tuple | None = None) -> Any:
        """执行查询"""

    @abstractmethod
    def get_version(self) -> str | None:
        """获取数据库版本"""


class MySQLConnection(DatabaseConnection):
    """MySQL数据库连接"""

    def connect(self) -> bool:
        """建立MySQL连接"""
        try:
            import pymysql

            # 获取连接信息
            password = self.instance.credential.get_plain_password() if self.instance.credential else ""

            self.connection = pymysql.connect(
                host=self.instance.host,
                port=self.instance.port,
                database=self.instance.database_name
                or DatabaseTypeUtils.get_database_type_config("mysql").default_schema
                or "",
                user=(self.instance.credential.username if self.instance.credential else ""),
                password=password,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=30,
                read_timeout=60,
                write_timeout=60,
                sql_mode="TRADITIONAL",
            )
            self.is_connected = True
            return True

        except Exception as e:
            self.db_logger.error(
                "MySQL连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="MySQL",
                error=str(e),
            )
            return False

    def disconnect(self) -> None:
        """断开MySQL连接"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                self.db_logger.error(
                    "MySQL断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="MySQL",
                    error=str(e),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, Any]:
        """测试MySQL连接"""
        try:
            if not self.connect():
                return {"success": False, "error": "无法建立连接"}

            version = self.get_version()
            return {
                "success": True,
                "message": f"MySQL连接成功 (主机: {self.instance.host}:{self.instance.port}, 版本: {version or '未知'})",
                "database_version": version,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.disconnect()

    def execute_query(self, query: str, params: tuple | None = None) -> Any:
        """执行MySQL查询"""
        if not self.is_connected:
            if not self.connect():
                error_msg = "无法建立数据库连接"
                raise Exception(error_msg)

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        """获取MySQL版本"""
        try:
            result = self.execute_query("SELECT VERSION()")
            if result:
                raw_version = result[0][0]
                parsed = DatabaseVersionParser.parse_version('mysql', raw_version)
                return DatabaseVersionParser.format_version_display('mysql', raw_version)
            return None
        except Exception:
            return None


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL数据库连接"""

    def connect(self) -> bool:
        """建立PostgreSQL连接"""
        try:
            import psycopg

            # 获取连接信息
            password = self.instance.credential.get_plain_password() if self.instance.credential else ""

            self.connection = psycopg.connect(
                host=self.instance.host,
                port=self.instance.port,
                dbname=self.instance.database_name
                or DatabaseTypeUtils.get_database_type_config("postgresql").default_schema
                or "postgres",
                user=(self.instance.credential.username if self.instance.credential else ""),
                password=password,
                connect_timeout=30,
            )
            self.is_connected = True
            return True

        except Exception as e:
            self.db_logger.error(
                "PostgreSQL连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="PostgreSQL",
                exception=str(e),
            )
            return False

    def disconnect(self) -> None:
        """断开PostgreSQL连接"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                self.db_logger.error(
                    "PostgreSQL断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="PostgreSQL",
                    exception=str(e),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, Any]:
        """测试PostgreSQL连接"""
        try:
            if not self.connect():
                return {"success": False, "error": "无法建立连接"}

            version = self.get_version()
            return {
                "success": True,
                "message": f"PostgreSQL连接成功 (主机: {self.instance.host}:{self.instance.port}, 版本: {version or '未知'})",
                "database_version": version,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.disconnect()

    def execute_query(self, query: str, params: tuple | None = None) -> Any:
        """执行PostgreSQL查询"""
        if not self.is_connected:
            if not self.connect():
                error_msg = "无法建立数据库连接"
                raise Exception(error_msg)

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        """获取PostgreSQL版本"""
        try:
            result = self.execute_query("SELECT version()")
            if result:
                raw_version = result[0][0]
                return DatabaseVersionParser.format_version_display('postgresql', raw_version)
            return None
        except Exception:
            return None


class SQLServerConnection(DatabaseConnection):
    """SQL Server数据库连接 - 支持2005-2022版本"""

    def __init__(self, instance):
        super().__init__(instance)
        self.driver_type = None  # 记录使用的驱动类型

    def connect(self) -> bool:
        """建立SQL Server连接 - 尝试多种驱动和版本兼容性"""
        # 获取连接信息
        password = self.instance.credential.get_plain_password() if self.instance.credential else ""
        username = self.instance.credential.username if self.instance.credential else ""

        database_name = (
            self.instance.database_name
            or DatabaseTypeUtils.get_database_type_config("sqlserver").default_schema
            or "master"
        )

        # 尝试不同的连接方式
        connection_methods = [
            self._try_pyodbc_connection,
            self._try_pymssql_connection,
            self._try_pyodbc_legacy_connection,
        ]

        for method in connection_methods:
            try:
                if method(username, password, database_name):
                    return True
            except Exception as e:
                self.db_logger.warning(
                    f"SQL Server连接方法失败: {method.__name__}",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="SQL Server",
                    exception=str(e),
                )
                continue

        # 所有方法都失败
        self.db_logger.error(
            "SQL Server连接失败 - 所有驱动方法都不可用",
            module="connection",
            instance_id=self.instance.id,
            db_type="SQL Server",
        )
        return False

    def _try_pyodbc_connection(self, username: str, password: str, database_name: str) -> bool:
        """尝试使用pyodbc连接 (推荐用于现代SQL Server版本)"""
        try:
            import pyodbc

            # 构建连接字符串 - 支持多种版本
            connection_strings = [
                # SQL Server 2012+ (推荐)
                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.instance.host},{self.instance.port};DATABASE={database_name};UID={username};PWD={password};TrustServerCertificate=yes;",
                # SQL Server 2008-2019
                f"DRIVER={{ODBC Driver 13 for SQL Server}};SERVER={self.instance.host},{self.instance.port};DATABASE={database_name};UID={username};PWD={password};TrustServerCertificate=yes;",
                # SQL Server 2005-2012 (传统)
                f"DRIVER={{SQL Server}};SERVER={self.instance.host},{self.instance.port};DATABASE={database_name};UID={username};PWD={password};",
                # 使用命名管道 (本地连接)
                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.instance.host};DATABASE={database_name};UID={username};PWD={password};Trusted_Connection=no;",
            ]

            for conn_str in connection_strings:
                try:
                    self.connection = pyodbc.connect(conn_str, timeout=30)
                    self.is_connected = True
                    self.driver_type = "pyodbc"
                    return True
                except Exception:
                    continue

            return False

        except ImportError:
            return False

    def _try_pymssql_connection(self, username: str, password: str, database_name: str) -> bool:
        """尝试使用pymssql连接 (适用于Linux/Unix环境)"""
        try:
            import pymssql

            self.connection = pymssql.connect(
                server=self.instance.host,
                port=self.instance.port,
                user=username,
                password=password,
                database=database_name,
                timeout=30,
                # 添加版本兼容性参数
                tds_version="7.4",  # 支持SQL Server 2005+
            )
            self.is_connected = True
            self.driver_type = "pymssql"
            return True

        except ImportError:
            return False

    def _try_pyodbc_legacy_connection(self, username: str, password: str, database_name: str) -> bool:
        """尝试使用传统pyodbc连接 (兼容老版本)"""
        try:
            import pyodbc

            # 传统连接字符串，兼容SQL Server 2005-2008
            legacy_conn_str = (
                f"DRIVER={{SQL Server}};"
                f"SERVER={self.instance.host},{self.instance.port};"
                f"DATABASE={database_name};"
                f"UID={username};"
                f"PWD={password};"
                f"Connection Timeout=30;"
            )

            self.connection = pyodbc.connect(legacy_conn_str)
            self.is_connected = True
            self.driver_type = "pyodbc_legacy"
            return True

        except ImportError:
            return False

    def disconnect(self) -> None:
        """断开SQL Server连接"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                self.db_logger.error(
                    "SQL Server断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="SQL Server",
                    exception=str(e),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, Any]:
        """测试SQL Server连接"""
        try:
            if not self.connect():
                return {"success": False, "error": "无法建立连接"}

            version = self.get_version()
            driver_info = f" (驱动: {self.driver_type})" if self.driver_type else ""
            return {
                "success": True,
                "message": f"SQL Server连接成功 (主机: {self.instance.host}:{self.instance.port}, 版本: {version or '未知'}{driver_info})",
                "database_version": version,
                "driver_type": self.driver_type,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.disconnect()

    def execute_query(self, query: str, params: tuple | None = None) -> Any:
        """执行SQL Server查询"""
        if not self.is_connected:
            if not self.connect():
                error_msg = "无法建立数据库连接"
                raise Exception(error_msg)

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        """获取SQL Server版本"""
        try:
            raw_version = None
            if self.driver_type == "pyodbc":
                # pyodbc使用cursor
                cursor = self.connection.cursor()
                cursor.execute("SELECT @@VERSION")
                result = cursor.fetchone()
                cursor.close()
                raw_version = result[0] if result else None
            else:
                # pymssql使用execute_query
                result = self.execute_query("SELECT @@VERSION")
                raw_version = result[0][0] if result else None
            
            if raw_version:
                return DatabaseVersionParser.format_version_display('sqlserver', raw_version)
            return None
        except Exception:
            return None


class OracleConnection(DatabaseConnection):
    """Oracle数据库连接"""

    def connect(self) -> bool:
        """建立Oracle连接"""
        try:
            import oracledb

            # 获取连接信息
            password = self.instance.credential.get_plain_password() if self.instance.credential else ""

            # 构建连接字符串
            database_name = (
                self.instance.database_name
                or DatabaseTypeUtils.get_database_type_config("oracle").default_schema
                or "ORCL"
            )

            # 优先使用服务名格式，因为大多数现代Oracle配置都使用服务名
            if "." in database_name:
                # Service Name格式: host:port/service_name
                dsn = f"{self.instance.host}:{self.instance.port}/{database_name}"
            else:
                # 对于简单名称，优先尝试服务名格式，如果失败再尝试SID格式
                dsn = f"{self.instance.host}:{self.instance.port}/{database_name}"

            # 直接使用Thick模式连接（用户已安装Oracle客户端）
            try:
                # 初始化Thick模式（指定Oracle Instant Client路径）
                import os

                current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                oracle_client_path = os.path.join(current_dir, "oracle_client", "lib")
                oracledb.init_oracle_client(lib_dir=oracle_client_path)
                self.connection = oracledb.connect(
                    user=(self.instance.credential.username if self.instance.credential else ""),
                    password=password,
                    dsn=dsn,
                )
            except Exception as e:
                # 如果服务名格式失败，尝试SID格式
                if not dsn.endswith(f":{database_name}") and "." not in database_name:
                    try:
                        sid_dsn = f"{self.instance.host}:{self.instance.port}:{database_name}"
                        self.connection = oracledb.connect(
                            user=(self.instance.credential.username if self.instance.credential else ""),
                            password=password,
                            dsn=sid_dsn,
                        )
                    except Exception:
                        # 如果SID格式也失败，抛出原始错误
                        raise e
                else:
                    raise e

            self.is_connected = True
            return True

        except Exception as e:
            self.db_logger.error(
                "Oracle连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="Oracle",
                error=str(e),
            )
            return False

    def disconnect(self) -> None:
        """断开Oracle连接"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                self.db_logger.error(
                    "Oracle断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="Oracle",
                    exception=str(e),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, Any]:
        """测试Oracle连接"""
        try:
            if not self.connect():
                return {"success": False, "error": "无法建立连接"}

            version = self.get_version()
            return {
                "success": True,
                "message": f"Oracle连接成功 (主机: {self.instance.host}:{self.instance.port}, 版本: {version or '未知'})",
                "database_version": version,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.disconnect()

    def execute_query(self, query: str, params: tuple | dict | None = None) -> Any:
        """执行Oracle查询"""
        if not self.is_connected:
            if not self.connect():
                error_msg = "无法建立数据库连接"
                raise Exception(error_msg)

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        """获取Oracle版本"""
        try:
            result = self.execute_query("SELECT * FROM v$version WHERE rownum = 1")
            if result:
                raw_version = result[0][0]
                return DatabaseVersionParser.format_version_display('oracle', raw_version)
            return None
        except Exception:
            return None


class ConnectionFactory:
    """数据库连接工厂"""

    # 数据库类型到连接类的映射
    CONNECTION_CLASSES = {
        "mysql": MySQLConnection,
        "postgresql": PostgreSQLConnection,
        "sqlserver": SQLServerConnection,
        "oracle": OracleConnection,
    }

    @staticmethod
    def create_connection(instance: Instance) -> DatabaseConnection | None:
        """
        创建数据库连接

        Args:
            instance: 数据库实例

        Returns:
            数据库连接对象，如果类型不支持则返回None
        """
        db_type = instance.db_type.lower()

        if db_type not in ConnectionFactory.CONNECTION_CLASSES:
            log_error(
                "不支持的数据库类型",
                module="connection",
                instance_id=instance.id,
                db_type=db_type,
            )
            return None

        connection_class = ConnectionFactory.CONNECTION_CLASSES[db_type]
        return connection_class(instance)

    @staticmethod
    def test_connection(instance: Instance) -> dict[str, Any]:
        """
        测试数据库连接

        Args:
            instance: 数据库实例

        Returns:
            测试结果字典
        """
        connection = ConnectionFactory.create_connection(instance)
        if not connection:
            return {
                "success": False,
                "error": f"不支持的数据库类型: {instance.db_type}",
            }

        return connection.test_connection()

    @staticmethod
    def get_supported_types() -> list:
        """
        获取支持的数据库类型列表

        Returns:
            支持的数据库类型列表
        """
        return list(ConnectionFactory.CONNECTION_CLASSES.keys())

    @staticmethod
    def is_type_supported(db_type: str) -> bool:
        """
        检查数据库类型是否支持

        Args:
            db_type: 数据库类型名称

        Returns:
            是否支持该数据库类型
        """
        return db_type.lower() in ConnectionFactory.CONNECTION_CLASSES
