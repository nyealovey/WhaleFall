"""表容量采集协调器,实现连接、采集、落库与清理整体流程."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.constants import DatabaseType
from app.models.database_table_size_stat import DatabaseTableSizeStat
from app.services.connection_adapters.adapters.base import ConnectionAdapterError, DatabaseConnection
from app.services.connection_adapters.adapters.postgresql_adapter import PostgreSQLConnection
from app.services.connection_adapters.adapters.sqlserver_adapter import SQLServerConnection
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.services.database_sync.table_size_adapters.base_adapter import BaseTableSizeAdapter
from app.services.database_sync.table_size_adapters.mysql_adapter import MySQLTableSizeAdapter
from app.services.database_sync.table_size_adapters.oracle_adapter import OracleTableSizeAdapter
from app.services.database_sync.table_size_adapters.postgresql_adapter import PostgreSQLTableSizeAdapter
from app.services.database_sync.table_size_adapters.sqlserver_adapter import SQLServerTableSizeAdapter
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.models.instance import Instance


CONNECTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    LookupError,
    ValueError,
    ConnectionError,
    TimeoutError,
    OSError,
)


@dataclass(slots=True)
class TableSizeRefreshOutcome:
    saved_count: int
    deleted_count: int
    elapsed_ms: int


@dataclass(slots=True)
class _InstanceConnectionTarget:
    id: int
    name: str
    host: str
    port: int
    database_name: str | None
    credential: object | None


class TableSizeCoordinator:
    """按需采集指定 database 的表容量并落库(仅保存最新快照)."""

    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self.logger = get_system_logger()
        self._adapter = self._resolve_adapter(instance.db_type)
        self._connection: DatabaseConnection | None = None

    @staticmethod
    def _resolve_adapter(db_type: str) -> BaseTableSizeAdapter:
        normalized = DatabaseType.normalize(db_type or "")
        mapping: dict[str, type[BaseTableSizeAdapter]] = {
            DatabaseType.MYSQL: MySQLTableSizeAdapter,
            DatabaseType.POSTGRESQL: PostgreSQLTableSizeAdapter,
            DatabaseType.SQLSERVER: SQLServerTableSizeAdapter,
            DatabaseType.ORACLE: OracleTableSizeAdapter,
        }
        adapter_cls = mapping.get(normalized)
        if not adapter_cls:
            msg = f"不支持的数据库类型: {db_type}"
            raise ValueError(msg)
        return adapter_cls()

    def connect(self, database_name: str) -> bool:
        """建立远端连接.

        PostgreSQL/SQL Server 需要连接到目标 database; 其他类型复用实例连接并通过查询过滤 database_name.
        """
        if self._connection and getattr(self._connection, "is_connected", False):
            return True

        db_type = DatabaseType.normalize(self.instance.db_type or "")
        connection = self._create_scoped_connection(db_type, database_name)
        if connection is None:
            return False

        try:
            if connection.connect():
                self._connection = connection
                return True
        except CONNECTION_EXCEPTIONS as exc:
            self.logger.exception(
                "table_size_connection_error",
                instance=self.instance.name,
                db_type=db_type,
                database_name=database_name,
                error=str(exc),
            )

        self._connection = None
        return False

    def disconnect(self) -> None:
        if not self._connection:
            return
        try:
            self._connection.disconnect()
        except CONNECTION_EXCEPTIONS as exc:
            self.logger.warning(
                "table_size_disconnect_error",
                instance=self.instance.name,
                error=str(exc),
            )
        finally:
            self._connection = None

    def refresh_snapshot(self, database_name: str) -> TableSizeRefreshOutcome:
        """采集并刷新本地快照,返回 upsert/cleanup 统计."""
        start = time.perf_counter()

        self._ensure_connection()
        connection = cast(DatabaseConnection, self._connection)

        table_rows = self._adapter.fetch_table_sizes(self.instance, connection, database_name)
        collected_at = time_utils.now()

        saved_count, deleted_count = self._upsert_and_cleanup(database_name, table_rows, collected_at=collected_at)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return TableSizeRefreshOutcome(
            saved_count=saved_count,
            deleted_count=deleted_count,
            elapsed_ms=elapsed_ms,
        )

    def _create_scoped_connection(self, db_type: str, database_name: str) -> DatabaseConnection | None:
        if db_type in (DatabaseType.POSTGRESQL, DatabaseType.SQLSERVER):
            target_instance = _InstanceConnectionTarget(
                id=int(self.instance.id),
                name=str(self.instance.name),
                host=str(self.instance.host),
                port=int(self.instance.port),
                database_name=database_name,
                credential=getattr(self.instance, "credential", None),
            )
            if db_type == DatabaseType.POSTGRESQL:
                return PostgreSQLConnection(cast("Instance", target_instance))
            return SQLServerConnection(cast("Instance", target_instance))

        return ConnectionFactory.create_connection(self.instance)

    def _ensure_connection(self) -> None:
        if not self._connection or not getattr(self._connection, "is_connected", False):
            msg = "数据库连接未建立"
            raise RuntimeError(msg)

    def _upsert_and_cleanup(
        self,
        database_name: str,
        rows: list[dict[str, object]],
        *,
        collected_at: object,
    ) -> tuple[int, int]:
        current_utc = time_utils.now()
        records: list[dict[str, object]] = []

        for item in rows:
            schema_name = str(item.get("schema_name") or "").strip()
            table_name = str(item.get("table_name") or "").strip()
            if not schema_name or not table_name:
                continue

            records.append(
                {
                    "instance_id": self.instance.id,
                    "database_name": database_name,
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "size_mb": self._adapter._safe_to_int(item.get("size_mb")) or 0,
                    "data_size_mb": self._adapter._safe_to_int(item.get("data_size_mb")),
                    "index_size_mb": self._adapter._safe_to_int(item.get("index_size_mb")),
                    "row_count": self._adapter._safe_to_int(item.get("row_count")),
                    "collected_at": collected_at,
                    "created_at": current_utc,
                    "updated_at": current_utc,
                },
            )

        saved_count = len(records)

        if records:
            insert_stmt = self._build_upsert_stmt(records, current_utc=current_utc)
            try:
                with db.session.begin_nested():
                    db.session.execute(insert_stmt)
                    db.session.flush()
            except SQLAlchemyError as exc:
                self.logger.exception(
                    "table_size_upsert_failed",
                    instance=self.instance.name,
                    database_name=database_name,
                    error=str(exc),
                )
                raise

        deleted_count = self._cleanup_removed(database_name, records)
        return saved_count, deleted_count

    def _build_upsert_stmt(self, records: list[dict[str, object]], *, current_utc: object) -> Any:
        dialect = getattr(getattr(db.session, "bind", None), "dialect", None)
        dialect_name = getattr(dialect, "name", "")

        if dialect_name == "sqlite":
            insert_stmt = sqlite_insert(DatabaseTableSizeStat).values(records)
        else:
            insert_stmt = pg_insert(DatabaseTableSizeStat).values(records)

        return insert_stmt.on_conflict_do_update(
            index_elements=[
                DatabaseTableSizeStat.instance_id,
                DatabaseTableSizeStat.database_name,
                DatabaseTableSizeStat.schema_name,
                DatabaseTableSizeStat.table_name,
            ],
            set_={
                "size_mb": insert_stmt.excluded.size_mb,
                "data_size_mb": insert_stmt.excluded.data_size_mb,
                "index_size_mb": insert_stmt.excluded.index_size_mb,
                "row_count": insert_stmt.excluded.row_count,
                "collected_at": insert_stmt.excluded.collected_at,
                "updated_at": current_utc,
            },
        )

    def _cleanup_removed(self, database_name: str, records: list[dict[str, object]]) -> int:
        query = DatabaseTableSizeStat.query.filter(
            DatabaseTableSizeStat.instance_id == self.instance.id,
            DatabaseTableSizeStat.database_name == database_name,
        )

        keys = [(cast(str, item["schema_name"]), cast(str, item["table_name"])) for item in records]
        if keys:
            query = query.filter(
                tuple_(DatabaseTableSizeStat.schema_name, DatabaseTableSizeStat.table_name).notin_(keys),
            )

        try:
            with db.session.begin_nested():
                deleted_count = query.delete(synchronize_session=False)
                db.session.flush()
        except SQLAlchemyError as exc:
            self.logger.exception(
                "table_size_cleanup_failed",
                instance=self.instance.name,
                database_name=database_name,
                error=str(exc),
            )
            raise

        return int(deleted_count or 0)
