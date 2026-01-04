"""SQL Server 表容量采集适配器实现."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.database_sync.table_size_adapters.base_adapter import BaseTableSizeAdapter

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection
else:
    Instance = Any
    DatabaseConnection = Any


class SQLServerTableSizeAdapter(BaseTableSizeAdapter):
    """SQL Server 表容量采集适配器.

    需要连接到目标 database,再通过 sys.dm_db_partition_stats 计算容量.
    """

    def fetch_table_sizes(
        self,
        instance: Instance,
        connection: DatabaseConnection,
        database_name: str,
    ) -> list[dict[str, object]]:
        del database_name

        query = """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                SUM(p.reserved_page_count) * 8.0 / 1024 AS size_mb,
                SUM(p.in_row_data_page_count + p.lob_used_page_count + p.row_overflow_used_page_count)
                    * 8.0 / 1024 AS data_size_mb,
                (
                    SUM(p.used_page_count)
                    - SUM(p.in_row_data_page_count + p.lob_used_page_count + p.row_overflow_used_page_count)
                ) * 8.0 / 1024 AS index_size_mb,
                SUM(p.row_count) AS row_count
            FROM sys.dm_db_partition_stats p
            JOIN sys.tables t ON t.object_id = p.object_id
            JOIN sys.schemas s ON s.schema_id = t.schema_id
            WHERE t.is_ms_shipped = 0
            GROUP BY s.name, t.name
            ORDER BY
                size_mb DESC,
                s.name ASC,
                t.name ASC
        """

        result = connection.execute_query(query)
        tables: list[dict[str, object]] = []

        for row in result or []:
            if not row:
                continue
            schema_name = str(row[0]).strip() if row[0] is not None else ""
            table_name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            if not schema_name or not table_name:
                continue

            tables.append(
                {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "size_mb": self._safe_to_int(row[2]) or 0,
                    "data_size_mb": self._safe_to_int(row[3]),
                    "index_size_mb": self._safe_to_int(row[4]),
                    "row_count": self._safe_to_int(row[5] if len(row) > 5 else None),
                },
            )

        self.logger.info(
            "sqlserver_table_sizes_collected",
            instance=instance.name,
            table_count=len(tables),
        )
        return tables
