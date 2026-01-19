"""MySQL 表容量采集适配器实现."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from app.services.database_sync.table_size_adapters.base_adapter import BaseTableSizeAdapter

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection

_ROW_COUNT_COLUMN_INDEX: Final[int] = 5


class MySQLTableSizeAdapter(BaseTableSizeAdapter):
    """MySQL 表容量采集适配器.

    通过 information_schema.TABLES 采集指定数据库下各表的容量.
    """

    def fetch_table_sizes(
        self,
        instance: Instance,
        connection: DatabaseConnection,
        database_name: str,
    ) -> list[dict[str, object]]:
        """采集 MySQL 指定 schema 下的各表容量."""
        existence = connection.execute_query(
            "SELECT 1 FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s LIMIT 1",
            (database_name,),
        )
        if not existence:
            msg = f"数据库不存在: {database_name}"
            raise ValueError(msg)

        query = """
            SELECT
                TABLE_SCHEMA AS schema_name,
                TABLE_NAME AS table_name,
                (DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024 AS size_mb,
                DATA_LENGTH / 1024 / 1024 AS data_size_mb,
                INDEX_LENGTH / 1024 / 1024 AS index_size_mb,
                TABLE_ROWS AS row_count
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY
                size_mb DESC,
                TABLE_NAME ASC
        """

        result = connection.execute_query(query, (database_name,))
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
            "mysql_table_sizes_collected",
            instance=instance.name,
            database_name=database_name,
            table_count=len(tables),
        )
        return tables
