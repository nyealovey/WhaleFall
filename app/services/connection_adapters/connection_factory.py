#!/usr/bin/env python3

"""
数据库连接工厂
提供统一的数据库连接创建和管理功能
"""

from abc import ABC, abstractmethod
from typing import Any

from app.models.instance import Instance
from app.constants import TaskStatus
from app.services.database_type_service import DatabaseTypeService
from app.utils.structlog_config import get_db_logger, log_error
from app.utils.version_parser import DatabaseVersionParser


def _get_default_schema(db_type: str) -> str:
    """不依赖 utils 层，直接解析数据库类型对应的默认 schema。"""
    config = DatabaseTypeService.get_type_by_name(db_type)
    return config.default_schema if config and config.default_schema else ""


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
    def execute_query(self, query: str, params: tuple | None = None) -> Any:  # noqa: ANN401
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
                database=self.instance.database_name or _get_default_schema("mysql"),
                user=(self.instance.credential.username if self.instance.credential else ""),
                password=password,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=20,  # 20秒连接超时
                read_timeout=300,  # 5分钟读取超时
                write_timeout=300,  # 5分钟写入超时
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

    def execute_query(self, query: str, params: tuple | None = None) -> Any:  # noqa: ANN401
        """执行MySQL查询"""
        if not self.is_connected and not self.connect():
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
                return DatabaseVersionParser.format_version_display("mysql", raw_version)
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
                dbname=self.instance.database_name or _get_default_schema("postgresql") or "postgres",
                user=(self.instance.credential.username if self.instance.credential else ""),
                password=password,
                connect_timeout=20,  # 20秒连接超时
                options="-c statement_timeout=300000",  # 5分钟查询超时（毫秒）
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

    def execute_query(self, query: str, params: tuple | None = None) -> Any:  # noqa: ANN401
        """执行PostgreSQL查询"""
        if not self.is_connected and not self.connect():
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
                return DatabaseVersionParser.format_version_display("postgresql", raw_version)
            return None
        except Exception:
            return None


class SQLServerConnection(DatabaseConnection):
    """SQL Server数据库连接 - 支持2008-2022版本"""

    def __init__(self, instance: Any) -> None:  # noqa: ANN401
        super().__init__(instance)
        self.driver_type = None  # 记录使用的驱动类型

    def connect(self) -> bool:
        """建立SQL Server连接 - 仅使用pymssql驱动"""
        # 获取连接信息
        password = self.instance.credential.get_plain_password() if self.instance.credential else ""
        username = self.instance.credential.username if self.instance.credential else ""

        database_name = self.instance.database_name or _get_default_schema("sqlserver") or "master"

        # 只使用pymssql连接
        try:
            return self._try_pymssql_connection(username, password, database_name)
        except Exception as e:
            # 记录真实的连接错误，而不是误导性的"驱动不可用"
            self.db_logger.error(
                "SQL Server连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="SQL Server",
                host=self.instance.host,
                port=self.instance.port,
                database=database_name,
                username=username,
                error=str(e),
                error_type=type(e).__name__
            )
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
                timeout=300,  # 查询超时5分钟
                login_timeout=20,  # 连接/登录超时20秒
                # 支持SQL Server 2008+
                tds_version="7.2",  # 支持SQL Server 2008+
            )
            self.is_connected = True
            self.driver_type = "pymssql"
            return True

        except ImportError:
            self.db_logger.error(
                "pymssql模块未安装",
                module="connection",
                instance_id=self.instance.id,
                db_type="SQL Server"
            )
            return False
        except Exception as e:
            # 捕获所有其他连接异常，防止中断批量同步
            error_message = str(e)
            
            # 使用诊断工具分析错误
            from app.utils.sqlserver_connection_utils import sqlserver_connection_utils
            diagnosis = sqlserver_connection_utils.diagnose_connection_error(
                error_message, self.instance.host, self.instance.port
            )
            
            self.db_logger.error(
                "SQL Server连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="SQL Server",
                host=self.instance.host,
                port=self.instance.port,
                database=database_name,
                username=username,
                error=error_message,
                error_type=type(e).__name__,
                diagnosis=diagnosis
            )
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

    def execute_query(self, query: str, params: tuple | None = None) -> Any:  # noqa: ANN401
        """执行SQL Server查询"""
        if not self.is_connected and not self.connect():
            error_msg = "无法建立数据库连接"
            raise Exception(error_msg)

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            # 检查是否有结果集
            try:
                return cursor.fetchall()
            except Exception:
                # 如果没有结果集（如USE语句），返回空列表
                return []
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        """获取SQL Server版本"""
        try:
            # 使用pymssql的execute_query方法
            result = self.execute_query("SELECT @@VERSION")
            raw_version = result[0][0] if result else None

            if raw_version:
                return DatabaseVersionParser.format_version_display("sqlserver", raw_version)
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
            username = self.instance.credential.username if self.instance.credential else ""
            
            # Oracle 用户名处理：默认转换为大写
            # 如果用户名包含引号，则保持原样（大小写敏感）
            if username and not username.startswith('"'):
                username_for_connection = username.upper()
                if username != username_for_connection:
                    self.db_logger.debug(
                        "Oracle用户名转换为大写",
                        module="connection",
                        instance_id=self.instance.id,
                        original_username=username,
                        converted_username=username_for_connection,
                    )
            else:
                username_for_connection = username

            # 构建连接字符串
            database_name = self.instance.database_name or _get_default_schema("oracle") or "ORCL"

            # 使用 makedsn 构建 DSN（更可靠）
            try:
                # 优先尝试服务名格式
                dsn = oracledb.makedsn(
                    host=self.instance.host,
                    port=self.instance.port,
                    service_name=database_name
                )
            except Exception:
                # 如果失败，尝试 SID 格式
                dsn = oracledb.makedsn(
                    host=self.instance.host,
                    port=self.instance.port,
                    sid=database_name
                )

            self.db_logger.info(
                "尝试连接Oracle数据库",
                module="connection",
                instance_id=self.instance.id,
                host=self.instance.host,
                port=self.instance.port,
                username=username_for_connection,
                database_name=database_name,
            )

            # 初始化Thick模式，优先读取环境变量指向的客户端目录
            try:
                import os

                candidate_paths: list[str] = []

                env_lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
                if env_lib_dir:
                    candidate_paths.append(env_lib_dir)

                oracle_home = os.getenv("ORACLE_HOME")
                if oracle_home:
                    candidate_paths.append(os.path.join(oracle_home, "lib"))

                current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                candidate_paths.append(os.path.join(current_dir, "oracle_client", "lib"))

                lib_dir = next((path for path in candidate_paths if path and os.path.isdir(path)), None)

                if lib_dir:
                    oracledb.init_oracle_client(lib_dir=lib_dir)
                else:
                    oracledb.init_oracle_client()
                    
            except Exception as init_error:
                # 如果已经初始化过，忽略错误
                if "already been initialized" not in str(init_error).lower():
                    self.db_logger.warning(
                        "Oracle客户端初始化警告",
                        module="connection",
                        instance_id=self.instance.id,
                        error=str(init_error),
                    )

            # 建立连接
            self.connection = oracledb.connect(
                user=username_for_connection,
                password=password,
                dsn=dsn,
            )
            
            self.is_connected = True
            
            self.db_logger.info(
                "Oracle连接成功",
                module="connection",
                instance_id=self.instance.id,
                username=username_for_connection,
            )
            
            return True

        except Exception as e:
            error_message = str(e)
            self.db_logger.error(
                "Oracle连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="Oracle",
                host=self.instance.host,
                port=self.instance.port,
                username=username_for_connection if 'username_for_connection' in locals() else username if 'username' in locals() else "unknown",
                error=error_message,
                error_type=type(e).__name__,
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

    def execute_query(self, query: str, params: tuple | dict | None = None) -> Any:  # noqa: ANN401
        """执行Oracle查询"""
        if not self.is_connected and not self.connect():
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
                return DatabaseVersionParser.format_version_display("oracle", raw_version)
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
