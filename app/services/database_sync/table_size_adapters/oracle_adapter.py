"""Oracle 表容量采集适配器实现."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.database_sync.table_size_adapters.base_adapter import BaseTableSizeAdapter

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection
else:
    Instance = Any
    DatabaseConnection = Any


class OracleTableSizeAdapter(BaseTableSizeAdapter):
    """Oracle 表容量采集适配器.

    约定: database_name 对应 tablespace_name.
    使用 dba_segments 聚合 TABLE 段大小,不采集索引大小与行数(可选字段返回 None).
    """

    def fetch_table_sizes(
        self,
        instance: Instance,
        connection: DatabaseConnection,
        database_name: str,
    ) -> list[dict[str, object]]:
        existence = connection.execute_query(
            "SELECT 1 FROM dba_tablespaces WHERE tablespace_name = :tablespace_name",
            {"tablespace_name": database_name},
        )
        if not existence:
            msg = f"Tablespace 不存在: {database_name}"
            raise ValueError(msg)

        query = """
            SELECT
                owner AS schema_name,
                segment_name AS table_name,
                SUM(bytes) / 1024 / 1024 AS size_mb
            FROM dba_segments
            WHERE tablespace_name = :tablespace_name
              AND segment_type IN ('TABLE', 'TABLE PARTITION', 'TABLE SUBPARTITION')
            GROUP BY owner, segment_name
            ORDER BY
                size_mb DESC,
                owner ASC,
                segment_name ASC
        """

        result = connection.execute_query(
            query,
            {
                "tablespace_name": database_name,
            },
        )
        tables: list[dict[str, object]] = []

        for row in result or []:
            if not row:
                continue
            schema_name = str(row[0]).strip() if row[0] is not None else ""
            table_name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            if not schema_name or not table_name:
                continue

            size_mb = self._safe_to_int(row[2]) or 0
            tables.append(
                {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "size_mb": size_mb,
                    "data_size_mb": size_mb,
                    "index_size_mb": None,
                    "row_count": None,
                },
            )

        self.logger.info(
            "oracle_table_sizes_collected",
            instance=instance.name,
            tablespace=database_name,
            table_count=len(tables),
        )
        return tables
