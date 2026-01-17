"""SQL Server 表容量采集适配器实现."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from app.services.database_sync.table_size_adapters.base_adapter import BaseTableSizeAdapter

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection

_ROW_COUNT_COLUMN_INDEX: Final[int] = 5


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
        """采集 SQL Server 当前连接库中的各表容量."""
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
        rows = result if result is not None else []
        tables: list[dict[str, object]] = []

        for row in rows:
            if not row:
                continue
            schema_name = str(row[0]).strip() if row[0] is not None else ""
            table_name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            if not schema_name or not table_name:
                continue

            size_mb_value = self._safe_to_int(row[2])
            size_mb = 0 if size_mb_value is None else size_mb_value

            tables.append(
                {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "size_mb": size_mb,
                    "data_size_mb": self._safe_to_int(row[3]),
                    "index_size_mb": self._safe_to_int(row[4]),
                    "row_count": self._safe_to_int(
                        row[_ROW_COUNT_COLUMN_INDEX] if len(row) > _ROW_COUNT_COLUMN_INDEX else None,
                    ),
                },
            )

        self.logger.info(
            "sqlserver_table_sizes_collected",
            instance=instance.name,
            table_count=len(tables),
        )
        return tables
