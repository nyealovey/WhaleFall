"""PostgreSQL 容量同步适配器实现。"""

from __future__ import annotations

from collections.abc import Sequence

from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter
from app.utils.time_utils import time_utils


class PostgreSQLCapacityAdapter(BaseCapacityAdapter):
    """PostgreSQL 容量同步适配器。

    实现 PostgreSQL 数据库的库存查询和容量采集功能。
    通过 pg_database 视图和 pg_database_size 函数采集数据库大小。

    Attributes:
        _SYSTEM_DATABASES: PostgreSQL 系统数据库集合。

    Example:
        >>> adapter = PostgreSQLCapacityAdapter()
        >>> inventory = adapter.fetch_inventory(instance, connection)
        >>> capacity = adapter.fetch_capacity(instance, connection, ['mydb'])

    """

    _SYSTEM_DATABASES = {"postgres"}

    def fetch_inventory(self, instance, connection) -> list[dict]:
        """列出 PostgreSQL 实例当前的数据库清单。

        Args:
            instance: 实例对象。
            connection: PostgreSQL 数据库连接对象。

        Returns:
            数据库清单列表，每个元素包含：
            - database_name: 数据库名称
            - is_system: 是否为系统数据库或模板数据库

        Example:
            >>> inventory = adapter.fetch_inventory(instance, connection)
            >>> print(inventory[0])
            {'database_name': 'mydb', 'is_system': False}

        """
        query = """
            SELECT
                datname,
                datistemplate
            FROM pg_database
            WHERE datallowconn = TRUE
        """

        result = connection.execute_query(query)
        metadata: list[dict] = []
        for row in result or []:
            name = str(row[0]).strip() if row and row[0] is not None else ""
            if not name:
                continue
            is_template = bool(row[1] if len(row) > 1 else False)
            is_system = is_template or name in self._SYSTEM_DATABASES
            metadata.append({"database_name": name, "is_system": is_system})

        self.logger.info(
            "fetch_postgresql_inventory_success",
            instance=instance.name,
            database_count=len(metadata),
        )
        return metadata

    def fetch_capacity(
        self,
        instance,
        connection,
        target_databases: Sequence[str] | None = None,
    ) -> list[dict]:
        """采集 PostgreSQL 数据库容量数据。

        使用 pg_database_size 函数查询数据库大小。

        Args:
            instance: 实例对象。
            connection: PostgreSQL 数据库连接对象。
            target_databases: 可选的目标数据库名称列表。
                如果为 None，采集所有非模板数据库；
                如果为空列表，跳过采集。

        Returns:
            容量数据列表，每个元素包含：
            - database_name: 数据库名称
            - size_mb: 总大小（MB）
            - data_size_mb: 数据大小（MB）
            - log_size_mb: 日志大小（PostgreSQL 中为 None）
            - collected_date: 采集日期（中国时区）
            - collected_at: 采集时间（UTC）
            - is_system: 是否为系统数据库

        Raises:
            ValueError: 当查询结果为空时抛出。

        Example:
            >>> capacity = adapter.fetch_capacity(instance, connection, ['mydb'])
            >>> print(capacity[0])
            {
                'database_name': 'mydb',
                'size_mb': 50,
                'data_size_mb': 50,
                'log_size_mb': None,
                'collected_date': date(2025, 11, 25),
                'collected_at': datetime(...),
                'is_system': False
            }

        """
        normalized_target = self._normalize_targets(target_databases)
        if normalized_target == set():
            self.logger.info(
                "postgresql_skip_capacity_no_targets",
                instance=instance.name,
            )
            return []

        query = """
            SELECT
                datname AS database_name,
                pg_database_size(datname) / 1024 / 1024 AS size_mb,
                pg_database_size(datname) / 1024 / 1024 AS data_size_mb
            FROM
                pg_database
            WHERE
                datistemplate = false
            ORDER BY
                size_mb DESC
        """

        result = connection.execute_query(query)
        if not result:
            error_msg = "PostgreSQL 未查询到任何数据库大小数据"
            self.logger.error(
                "postgresql_capacity_empty",
                instance=instance.name,
            )
            raise ValueError(error_msg)

        china_now = time_utils.now_china()
        data: list[dict] = []
        for row in result:
            name = row[0]
            if normalized_target is not None and name not in normalized_target:
                continue

            data.append(
                {
                    "database_name": name,
                    "size_mb": int(row[1] or 0),
                    "data_size_mb": int(row[2] or 0),
                    "log_size_mb": None,
                    "collected_date": china_now.date(),
                    "collected_at": time_utils.now(),
                    "is_system": name in self._SYSTEM_DATABASES,
                }
            )

        if normalized_target is not None:
            missing = normalized_target.difference({row["database_name"] for row in data})
            if missing:
                self.logger.warning(
                    "postgresql_capacity_missing",
                    instance=instance.name,
                    missing=sorted(missing),
                )

        self.logger.info(
            "postgresql_capacity_collection_success",
            instance=instance.name,
            database_count=len(data),
        )
        return data
