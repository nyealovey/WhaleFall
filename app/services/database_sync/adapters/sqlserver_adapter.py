"""SQL Server 容量同步适配器实现。"""

from __future__ import annotations

from typing import List, Optional
from collections.abc import Sequence

from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter
from app.utils.time_utils import time_utils


class SQLServerCapacityAdapter(BaseCapacityAdapter):
    """SQL Server 容量同步适配器。

    实现 SQL Server 数据库的库存查询和容量采集功能。
    通过 sys.databases 和 sys.master_files 视图采集数据库大小。

    Example:
        >>> adapter = SQLServerCapacityAdapter()
        >>> inventory = adapter.fetch_inventory(instance, connection)
        >>> capacity = adapter.fetch_capacity(instance, connection, ['mydb'])

    """

    def fetch_inventory(self, instance, connection) -> list[dict]:
        """列出 SQL Server 实例当前的数据库清单。

        Args:
            instance: 实例对象。
            connection: SQL Server 数据库连接对象。

        Returns:
            数据库清单列表，每个元素包含：
            - database_name: 数据库名称
            - is_system: 是否为系统数据库（database_id <= 4）

        Example:
            >>> inventory = adapter.fetch_inventory(instance, connection)
            >>> print(inventory[0])
            {'database_name': 'mydb', 'is_system': False}

        """
        query = """
            SELECT
                name,
                CASE WHEN database_id <= 4 THEN 1 ELSE 0 END AS is_system
            FROM sys.databases
            WHERE name IS NOT NULL
        """

        result = connection.execute_query(query)
        metadata: list[dict] = []
        for row in result or []:
            name = str(row[0]).strip() if row and row[0] is not None else ""
            if not name:
                continue
            is_system = bool(row[1] if len(row) > 1 else False)
            metadata.append({"database_name": name, "is_system": is_system})

        self.logger.info(
            "fetch_sqlserver_inventory_success",
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
        """采集 SQL Server 数据库容量数据。

        从 sys.master_files 视图中查询数据文件大小，并按数据库名称聚合。

        Args:
            instance: 实例对象。
            connection: SQL Server 数据库连接对象。
            target_databases: 可选的目标数据库名称列表。
                如果为 None，采集所有数据库；
                如果为空列表，跳过采集。

        Returns:
            容量数据列表，每个元素包含：
            - database_name: 数据库名称
            - size_mb: 总大小（MB，仅包含数据文件）
            - data_size_mb: 数据文件大小（MB）
            - log_size_mb: 日志大小（SQL Server 中为 None）
            - collected_date: 采集日期（中国时区）
            - collected_at: 采集时间（UTC）
            - is_system: 是否为系统数据库（统一为 False）

        Raises:
            ValueError: 当查询结果为空时抛出。

        Example:
            >>> capacity = adapter.fetch_capacity(instance, connection, ['mydb'])
            >>> print(capacity[0])
            {
                'database_name': 'mydb',
                'size_mb': 100,
                'data_size_mb': 100,
                'log_size_mb': None,
                'collected_date': date(2025, 11, 25),
                'collected_at': datetime(...),
                'is_system': False
            }

        """
        normalized_target = self._normalize_targets(target_databases)
        if normalized_target == set():
            self.logger.info(
                "sqlserver_skip_capacity_no_targets",
                instance=instance.name,
            )
            return []

        query = """
            SELECT
                DB_NAME(database_id) AS DatabaseName,
                SUM(CASE WHEN type_desc = 'ROWS' THEN size * 8.0 / 1024 ELSE 0 END) AS DataFileSize_MB
            FROM sys.master_files
            WHERE DB_NAME(database_id) IS NOT NULL
            GROUP BY database_id
            ORDER BY DataFileSize_MB DESC
        """

        result = connection.execute_query(query)
        if not result:
            error_msg = "SQL Server 未查询到任何数据库大小数据"
            self.logger.error(
                "sqlserver_capacity_empty",
                instance=instance.name,
            )
            raise ValueError(error_msg)

        china_now = time_utils.now_china()
        data: list[dict] = []
        for row in result:
            database_name = row[0]
            if normalized_target is not None and database_name not in normalized_target:
                continue

            data_size_mb = int(float(row[1] or 0))
            data.append(
                {
                    "database_name": database_name,
                    "size_mb": data_size_mb,
                    "data_size_mb": data_size_mb,
                    "log_size_mb": None,
                    "collected_date": china_now.date(),
                    "collected_at": time_utils.now(),
                    "is_system": False,
                }
            )

        if normalized_target is not None:
            missing = normalized_target.difference({row["database_name"] for row in data})
            if missing:
                self.logger.warning(
                    "sqlserver_capacity_missing",
                    instance=instance.name,
                    missing=list(sorted(missing)),
                )

        self.logger.info(
            "sqlserver_capacity_collection_success",
            instance=instance.name,
            database_count=len(data),
        )
        return data
