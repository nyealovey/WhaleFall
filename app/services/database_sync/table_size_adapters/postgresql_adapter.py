"""PostgreSQL 表容量采集适配器实现."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from app.services.database_sync.table_size_adapters.base_adapter import BaseTableSizeAdapter

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection

_ROW_COUNT_COLUMN_INDEX: Final[int] = 5


class PostgreSQLTableSizeAdapter(BaseTableSizeAdapter):
    """PostgreSQL 表容量采集适配器.

    需要连接到目标 database,再通过 pg_* 函数计算各表容量.
    """

    def fetch_table_sizes(
        self,
        instance: Instance,
        connection: DatabaseConnection,
        database_name: str,
    ) -> list[dict[str, object]]:
        """采集 PostgreSQL 当前连接库中的各表容量."""
        del database_name

        query = """
            SELECT
                n.nspname AS schema_name,
                c.relname AS table_name,
                pg_total_relation_size(c.oid) / 1024 / 1024 AS size_mb,
                pg_relation_size(c.oid) / 1024 / 1024 AS data_size_mb,
                pg_indexes_size(c.oid) / 1024 / 1024 AS index_size_mb,
                c.reltuples::bigint AS row_count
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r', 'p')
              AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY
                size_mb DESC,
                n.nspname ASC,
                c.relname ASC
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
            "postgresql_table_sizes_collected",
            instance=instance.name,
            table_count=len(tables),
        )
        return tables
