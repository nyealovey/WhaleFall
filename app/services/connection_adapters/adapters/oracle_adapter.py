"""Oracle 数据库连接适配器."""

from __future__ import annotations

from pathlib import Path


try:  # pragma: no cover - 运行环境可能未安装 oracledb
    import oracledb  # type: ignore
except ImportError:  # pragma: no cover
    oracledb = None  # type: ignore[assignment]

from .base import (
    ConnectionAdapterError,
    DatabaseConnection,
)

if oracledb:
    ORACLE_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (oracledb.Error,)
else:  # pragma: no cover - optional dependency
    ORACLE_DRIVER_EXCEPTIONS = ()

ORACLE_CONNECTION_EXCEPTIONS: tuple[type[BaseException], ...] = (ConnectionAdapterError, RuntimeError, ValueError, TypeError, ConnectionError, TimeoutError, OSError, *ORACLE_DRIVER_EXCEPTIONS)


class OracleConnection(DatabaseConnection):
    """Oracle 数据库连接."""

    def connect(self) -> bool:
        """建立 Oracle 连接并在必要时初始化客户端.

        Returns:
            bool: 连接成功返回 True,失败返回 False.

        """
        username_for_connection = None
        try:
            import os

            import oracledb

            password = self.instance.credential.get_plain_password() if self.instance.credential else ""
            username = self.instance.credential.username if self.instance.credential else ""
            username_for_connection = username.split("/")[0] if "/" in username else username
            host = self.instance.host
            port = self.instance.port
            service_name = self.instance.database_name or "ORCL"
            dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))(CONNECT_DATA=(SERVICE_NAME={service_name})))"

            if not hasattr(oracledb, "is_thin") or not oracledb.is_thin():
                try:
                    candidate_paths: list[Path] = []
                    env_lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
                    if env_lib_dir:
                        candidate_paths.append(Path(env_lib_dir))

                    oracle_home = os.getenv("ORACLE_HOME")
                    if oracle_home:
                        candidate_paths.append(Path(oracle_home) / "lib")

                    current_dir = Path(__file__).resolve().parents[2]
                    candidate_paths.append(current_dir / "oracle_client" / "lib")

                    lib_dir = next((path for path in candidate_paths if path and path.is_dir()), None)
                    if lib_dir:
                        oracledb.init_oracle_client(lib_dir=str(lib_dir))
                    else:
                        oracledb.init_oracle_client()
                except ORACLE_CONNECTION_EXCEPTIONS as init_error:
                    if "already been initialized" not in str(init_error).lower():
                        self.db_logger.warning(
                            "Oracle客户端初始化警告",
                            module="connection",
                            instance_id=self.instance.id,
                            error=str(init_error),
                        )

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
        except ORACLE_CONNECTION_EXCEPTIONS as exc:
            self.db_logger.exception(
                "Oracle连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="Oracle",
                host=self.instance.host,
                port=self.instance.port,
                username=username_for_connection if username_for_connection else "unknown",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return False

    def disconnect(self) -> None:
        """断开 Oracle 连接并清理句柄.

        Returns:
            None

        """
        if self.connection:
            try:
                self.connection.close()
            except ORACLE_CONNECTION_EXCEPTIONS as exc:
                self.db_logger.exception(
                    "Oracle断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="Oracle",
                    exception=str(exc),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, Any]:
        """测试 Oracle 连接并返回版本信息."""
        try:
            if not self.connect():
                return {"success": False, "error": "无法建立连接"}

            version = self.get_version()
            return {
                "success": True,
                "message": f"Oracle连接成功 (主机: {self.instance.host}:{self.instance.port}, 版本: {version or '未知'})",
                "database_version": version,
            }
        except ORACLE_CONNECTION_EXCEPTIONS as exc:
            return {"success": False, "error": str(exc)}
        finally:
            self.disconnect()

    def execute_query(self, query: str, params: tuple | dict | None = None) -> Any:
        """执行 SQL 查询并返回全部行.

        Args:
            query: SQL 语句.
            params: 查询参数,可为 tuple 或 dict.

        Returns:
            Any: 游标 `fetchall` 的结果.

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
        """获取 Oracle 版本字符串.

        Returns:
            str | None: 版本号,获取失败返回 None.

        """
        try:
            result = self.execute_query("SELECT * FROM v$version WHERE rownum = 1")
            if result:
                return result[0][0]
            return None
        except ORACLE_CONNECTION_EXCEPTIONS:
            return None
