"""Oracle 表容量采集适配器实现."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final

import oracledb  # type: ignore[import-not-found]

from app.services.database_sync.table_size_adapters.base_adapter import BaseTableSizeAdapter

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection, QueryResult
else:
    Instance = Any
    DatabaseConnection = Any
    QueryResult = Any

_SIZE_VALUE_COLUMN_INDEX: Final[int] = 2


class OracleTableSizeAdapter(BaseTableSizeAdapter):
    """Oracle 表容量采集适配器.

    约定: database_name 对应 tablespace_name.
    优先使用 dba_segments 聚合 TABLE 段大小,若 synonym 缺失则尝试 sys.dba_segments,权限不足降级 user_segments.
    不采集索引大小与行数(可选字段返回 None).
    """

    _ORACLE_MISSING_OBJECT_CODES: tuple[str, ...] = ("ORA-00942", "ORA-01031")

    @classmethod
    def _is_missing_view_or_privilege(cls, exc: BaseException) -> bool:
        message = str(exc).upper()
        return any(code in message for code in cls._ORACLE_MISSING_OBJECT_CODES)

    def _check_tablespace_exists(
        self,
        *,
        instance: Instance,
        connection: DatabaseConnection,
        tablespace_name: str,
    ) -> bool | None:
        checks = (
            ("dba_tablespaces", "SELECT 1 FROM dba_tablespaces WHERE tablespace_name = :tablespace_name"),
            ("sys.dba_tablespaces", "SELECT 1 FROM sys.dba_tablespaces WHERE tablespace_name = :tablespace_name"),
            ("user_tablespaces", "SELECT 1 FROM user_tablespaces WHERE tablespace_name = :tablespace_name"),
        )

        for view_name, query in checks:
            try:
                existence = connection.execute_query(query, {"tablespace_name": tablespace_name})
            except oracledb.Error as exc:
                if self._is_missing_view_or_privilege(exc):
                    self.logger.info(
                        "oracle_tablespace_check_fallback",
                        instance=instance.name,
                        tablespace=tablespace_name,
                        view=view_name,
                        error=str(exc),
                    )
                    continue
                raise

            if existence:
                return True

            if view_name.startswith("user_"):
                return None

            return False

        return None

    def _resolve_current_schema(
        self,
        *,
        instance: Instance,
        connection: DatabaseConnection,
    ) -> str:
        try:
            result = connection.execute_query("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM dual")
        except Exception as exc:
            self.logger.warning(
                "oracle_current_schema_resolve_fallback",
                module="database_sync",
                action="oracle_table_size.resolve_current_schema",
                instance=getattr(instance, "name", None),
                fallback=True,
                fallback_reason="oracle_current_schema_query_failed",
                exception_type=exc.__class__.__name__,
            )
            result = []

        schema_name = str(result[0][0]).strip() if result and result[0] and result[0][0] is not None else ""
        if schema_name:
            return schema_name

        username = getattr(getattr(instance, "credential", None), "username", "") or ""
        if isinstance(username, str):
            return username.split("/", 1)[0].strip()
        return ""

    @staticmethod
    def _extract_table_size_row(
        row: Sequence[object] | None,
        *,
        view_used: str,
        current_schema: str | None,
    ) -> tuple[str, str, object | None] | None:
        if not row:
            return None

        if view_used == "user_segments":
            schema_name = (current_schema or "").strip()
            table_name = str(row[0]).strip() if row[0] is not None else ""
            size_value = row[1] if len(row) > 1 else None
        else:
            schema_name = str(row[0]).strip() if row[0] is not None else ""
            table_name = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            size_value = row[_SIZE_VALUE_COLUMN_INDEX] if len(row) > _SIZE_VALUE_COLUMN_INDEX else None

        if not schema_name or not table_name:
            return None

        return schema_name, table_name, size_value

    def fetch_table_sizes(
        self,
        instance: Instance,
        connection: DatabaseConnection,
        database_name: str,
    ) -> list[dict[str, object]]:
        """采集 Oracle 指定 tablespace 下的各表容量."""
        tablespace_exists = self._check_tablespace_exists(
            instance=instance,
            connection=connection,
            tablespace_name=database_name,
        )
        if tablespace_exists is False:
            raise ValueError(f"Tablespace 不存在: {database_name}")

        query_template = """
            SELECT
                owner AS schema_name,
                segment_name AS table_name,
                SUM(bytes) / 1024 / 1024 AS size_mb
            FROM {segments_view}
            WHERE tablespace_name = :tablespace_name
              AND segment_type IN ('TABLE', 'TABLE PARTITION', 'TABLE SUBPARTITION')
            GROUP BY owner, segment_name
            ORDER BY
                size_mb DESC,
                owner ASC,
                segment_name ASC
        """

        result: QueryResult | None = None
        view_used: str | None = None
        for view_name in ("dba_segments", "sys.dba_segments"):
            query = query_template.format(segments_view=view_name)
            try:
                result = connection.execute_query(query, {"tablespace_name": database_name})
            except oracledb.Error as exc:
                if self._is_missing_view_or_privilege(exc):
                    self.logger.info(
                        "oracle_segments_query_fallback",
                        instance=instance.name,
                        tablespace=database_name,
                        view=view_name,
                        error=str(exc),
                    )
                    continue
                raise
            view_used = view_name
            break

        current_schema: str | None = None
        if view_used is None:
            try:
                user_query = """
                    SELECT
                        segment_name AS table_name,
                        SUM(bytes) / 1024 / 1024 AS size_mb
                    FROM user_segments
                    WHERE tablespace_name = :tablespace_name
                      AND segment_type IN ('TABLE', 'TABLE PARTITION', 'TABLE SUBPARTITION')
                    GROUP BY segment_name
                    ORDER BY
                        size_mb DESC,
                        segment_name ASC
                """
                result = connection.execute_query(user_query, {"tablespace_name": database_name})
                view_used = "user_segments"
                current_schema = self._resolve_current_schema(instance=instance, connection=connection)
            except oracledb.Error as exc:
                if self._is_missing_view_or_privilege(exc):
                    raise ValueError(
                        "Oracle 当前账号缺少读取表段信息的权限,请授予 dba_segments/sys.dba_segments 访问权限",
                    ) from exc
                raise

        tables: list[dict[str, object]] = []

        for row in result or []:
            parsed_row = self._extract_table_size_row(
                row=row,
                view_used=view_used or "",
                current_schema=current_schema,
            )
            if parsed_row is None:
                continue
            schema_name, table_name, size_value = parsed_row

            size_mb = self._safe_to_int(size_value) or 0
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

        if not tables and tablespace_exists is None:
            raise ValueError(f"未采集到任何表容量数据: 可能 tablespace 不存在或权限不足: {database_name}")

        self.logger.info(
            "oracle_table_sizes_collected",
            instance=instance.name,
            tablespace=database_name,
            view=view_used,
            table_count=len(tables),
        )
        return tables
