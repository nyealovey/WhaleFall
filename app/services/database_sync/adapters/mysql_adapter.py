"""MySQL 容量同步适配器实现."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, ClassVar

from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection


class MySQLCapacityAdapter(BaseCapacityAdapter):
    """MySQL 容量同步适配器.

    实现 MySQL 数据库的库存查询和容量采集功能.
    通过 INNODB_TABLESPACES 或 INNODB_SYS_TABLESPACES 视图采集表空间大小.

    Attributes:
        _SYSTEM_DATABASES: MySQL 系统数据库集合.

    Example:
        >>> adapter = MySQLCapacityAdapter()
        >>> inventory = adapter.fetch_inventory(instance, connection)
        >>> capacity = adapter.fetch_capacity(instance, connection, ['mydb'])

    """

    _SYSTEM_DATABASES: ClassVar[set[str]] = {"information_schema", "performance_schema", "mysql", "sys"}
    MYSQL_CAPACITY_EXCEPTIONS: tuple[type[Exception], ...] = (
        ConnectionAdapterError,
        RuntimeError,
        ValueError,
        TypeError,
        ConnectionError,
        TimeoutError,
        OSError,
    )

    def fetch_inventory(
        self,
        instance: Instance,
        connection: DatabaseConnection,
    ) -> list[dict[str, object]]:
        """列出 MySQL 实例当前的数据库清单.

        Args:
            instance: 实例对象.
            connection: MySQL 数据库连接对象.

        Returns:
            数据库清单列表,每个元素包含:
            - database_name: 数据库名称
            - is_system: 是否为系统数据库

        Example:
            >>> inventory = adapter.fetch_inventory(instance, connection)
            >>> print(inventory[0])
            {'database_name': 'mydb', 'is_system': False}

        """
        result = connection.execute_query("SHOW DATABASES")
        rows = result if result is not None else []
        metadata: list[dict] = []

        for row in rows:
            if not row:
                continue
            name = str(row[0]).strip()
            if not name:
                continue
            metadata.append(
                {
                    "database_name": name,
                    "is_system": name in self._SYSTEM_DATABASES,
                },
            )

        self.logger.info(
            "fetch_mysql_inventory_success",
            instance=instance.name,
            database_count=len(metadata),
            database_names=[entry["database_name"] for entry in metadata],
        )
        return metadata

    def fetch_capacity(
        self,
        instance: Instance,
        connection: DatabaseConnection,
        target_databases: Sequence[str] | None = None,
    ) -> list[dict[str, object]]:
        """采集指定数据库的容量数据.

        Args:
            instance: 实例对象.
            connection: MySQL 连接对象.
            target_databases: 目标数据库名称列表,为空则采集全部.

        Returns:
            list[dict]: 每个数据库的容量统计.

        """
        normalized_target = self._normalize_targets(target_databases)

        if normalized_target == set():
            self.logger.info(
                "mysql_skip_capacity_no_targets",
                instance=instance.name,
            )
            return []

        self._assert_permission(connection, instance)

        try:
            tablespace_stats = self._collect_tablespace_sizes(connection, instance)
        except self.MYSQL_CAPACITY_EXCEPTIONS as exc:  # pragma: no cover - defensive logging
            self.logger.exception(
                "mysql_tablespace_collection_failed",
                instance=instance.name,
                error=str(exc),
            )
            raise

        data = self._build_stats_from_tablespaces(instance, tablespace_stats)

        if normalized_target is not None:
            filtered = [item for item in data if item["database_name"] in normalized_target]
            missing = normalized_target.difference({row["database_name"] for row in filtered})
            if missing:
                self.logger.warning(
                    "mysql_capacity_missing_databases",
                    instance=instance.name,
                    missing=sorted(missing),
                )
            return filtered

        return data

    def _assert_permission(self, connection: DatabaseConnection, instance: Instance) -> None:
        """验证 MySQL 权限.

        检查是否有权限访问 information_schema.SCHEMATA 视图.

        Args:
            connection: MySQL 数据库连接对象.
            instance: 实例对象.

        Returns:
            None

        Raises:
            ValueError: 当权限不足时抛出.

        """
        test_query = "SELECT COUNT(*) FROM information_schema.SCHEMATA"
        result = connection.execute_query(test_query)
        if not result:
            error_msg = "MySQL 权限测试失败:无法访问 information_schema.SCHEMATA"
            self.logger.error(
                "mysql_permission_check_failed",
                instance=instance.name,
            )
            raise ValueError(error_msg)

        self.logger.info(
            "mysql_schema_access_verified",
            instance=instance.name,
            schema_count=result[0][0] if result and result[0] else 0,
        )

    def _collect_tablespace_sizes(
        self,
        connection: DatabaseConnection,
        instance: Instance,
    ) -> dict[str, int]:
        """采集 MySQL 表空间大小.

        从 INNODB_TABLESPACES 或 INNODB_SYS_TABLESPACES 视图中查询表空间大小,
        并按数据库名称聚合.

        Args:
            connection: MySQL 数据库连接对象.
            instance: 实例对象.

        Returns:
            数据库名称到总字节数的映射字典.

        Raises:
            Exception: 当查询失败时抛出.

        """
        queries: list[tuple[str, str]] = self._build_tablespace_queries(instance)
        aggregated: dict[str, int] = {}
        last_error: BaseException | None = None

        for label, query in queries:
            try:
                result = connection.execute_query(query)
            except self.MYSQL_CAPACITY_EXCEPTIONS as exc:
                last_error = exc
                self.logger.warning(
                    "mysql_tablespace_query_failed",
                    instance=instance.name,
                    view=label,
                    error=str(exc),
                    exc_info=True,
                )
                continue

            if not result:
                self.logger.info(
                    "mysql_tablespace_query_empty",
                    instance=instance.name,
                    view=label,
                )
                continue

            self._process_tablespace_rows(result, aggregated, instance, label)
            if aggregated:
                break

        if not aggregated:
            if last_error is not None:
                raise last_error
            return aggregated

        self._ensure_databases_presence(connection, aggregated, instance)
        return aggregated

    def _process_tablespace_rows(
        self,
        rows: Sequence[Sequence[object]] | None,
        aggregated: dict[str, int],
        instance: Instance,
        view: str,
    ) -> None:
        """解析表空间查询结果并聚合到字典."""
        if not rows:
            return

        self.logger.info(
            "mysql_tablespace_query_success",
            instance=instance.name,
            view=view,
            record_count=len(rows),
        )

        for row in rows:
            if not row:
                continue
            raw_name = str(row[0])
            if not raw_name:
                continue
            db_name = raw_name.split("/", 1)[0] if "/" in raw_name else raw_name
            db_name = self._normalize_database_name(db_name)
            total_bytes = row[1] if len(row) > 1 else None
            total_bytes_int = self._to_int(total_bytes)
            if total_bytes_int is None:
                continue
            aggregated[db_name] = aggregated.get(db_name, 0) + max(total_bytes_int, 0)

    def _ensure_databases_presence(
        self,
        connection: DatabaseConnection,
        aggregated: dict[str, int],
        instance: Instance,
    ) -> None:
        """确保所有数据库至少有零值占位."""
        try:
            databases_result = connection.execute_query("SHOW DATABASES")
        except self.MYSQL_CAPACITY_EXCEPTIONS as exc:
            self.logger.warning(
                "mysql_show_databases_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return

        if not databases_result:
            return

        for row in databases_result:
            if not row:
                continue
            db_name = self._normalize_database_name(str(row[0]))
            if not db_name:
                continue
            aggregated.setdefault(db_name, 0)

    def _build_stats_from_tablespaces(
        self,
        instance: Instance,
        stats: dict[str, int],
    ) -> list[dict[str, object]]:
        """将表空间统计转换为标准容量数据.

        Args:
            instance: 实例对象.
            stats: 表空间大小映射.

        Returns:
            list[dict]: 容量记录列表.

        """
        china_now = time_utils.now_china()
        collected_at = time_utils.now()
        data: list[dict] = []

        for db_name, total_bytes in stats.items():
            total_bytes_value = self._to_int(total_bytes)
            total_bytes_int = 0 if total_bytes_value is None else total_bytes_value

            size_mb = 0 if total_bytes_int <= 0 else max(math.ceil(total_bytes_int / (1024 * 1024)), 1)
            is_system_db = db_name in self._SYSTEM_DATABASES

            data.append(
                {
                    "database_name": db_name,
                    "size_mb": size_mb,
                    "data_size_mb": size_mb,
                    "log_size_mb": None,
                    "collected_date": china_now.date(),
                    "collected_at": collected_at,
                    "is_system": is_system_db,
                },
            )

            self.logger.debug(
                "mysql_database_tablespace_size",
                instance=instance.name,
                database=db_name,
                size_mb=size_mb,
                system_database=is_system_db,
            )

        return data

    @staticmethod
    def _normalize_database_name(raw_name: str) -> str:
        """将 MySQL tablespace 名称中的 @XXXX 转回正常字符.

        MySQL 在某些情况下会将特殊字符编码为 @XXXX 格式(十六进制).

        Args:
            raw_name: 原始数据库名称.

        Returns:
            规范化后的数据库名称.

        Example:
            >>> MySQLCapacityAdapter._normalize_database_name('test@002d01')
            'test-01'

        """
        if not raw_name:
            return raw_name

        def _replace(match: re.Match[str]) -> str:
            code = match.group(1)
            try:
                return chr(int(code, 16))
            except ValueError:
                return match.group(0)

        return re.sub(r"@([0-9A-Fa-f]{4})", _replace, raw_name)

    @staticmethod
    def _to_int(value: object) -> int | None:
        """安全转换表空间数值."""
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, (float, str)):
            try:
                return int(float(value))
            except ValueError:
                return None
        return None

    def _build_tablespace_queries(self, instance: Instance) -> list[tuple[str, str]]:
        """构建表空间查询语句列表.

        根据 MySQL 版本选择合适的视图(MySQL 8.x 优先使用 INNODB_TABLESPACES,
        MySQL 5.x 优先使用 INNODB_SYS_TABLESPACES).

        Args:
            instance: 实例对象,包含版本信息.

        Returns:
            查询列表,每个元素为 (视图名称, SQL 查询语句) 元组.
            按优先级排序,会依次尝试直到成功.

        """
        main_version_value = getattr(instance, "main_version", None)
        normalized_version = "" if main_version_value is None else str(main_version_value).strip().lower()
        query_innodb_tablespaces = """
            SELECT
                ts.NAME,
                ts.FILE_SIZE
            FROM information_schema.INNODB_TABLESPACES ts
        """
        query_innodb_sys_tablespaces = """
            SELECT
                ts.NAME,
                ts.FILE_SIZE
            FROM information_schema.INNODB_SYS_TABLESPACES ts
        """

        if normalized_version.startswith("8"):
            return [
                ("INNODB_TABLESPACES", query_innodb_tablespaces),
                ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
            ]
        if normalized_version.startswith("5"):
            return [
                ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
                ("INNODB_TABLESPACES", query_innodb_tablespaces),
            ]
        return [
            ("INNODB_TABLESPACES", query_innodb_tablespaces),
            ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
        ]
