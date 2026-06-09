"""MySQL replication 拓扑检测 contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from app.core.types import SyncConnection

REPLICA_STATUS_QUERY = "SHOW REPLICA STATUS"
SLAVE_STATUS_QUERY = "SHOW SLAVE STATUS"
READ_ONLY_QUERY = "SELECT @@global.read_only AS read_only, @@global.super_read_only AS super_read_only"
MYSQL_REPLICA_STATUS_UNSUPPORTED_MARKERS = (
    "1064",
    "syntax error",
    "near 'replica status'",
)


@dataclass(frozen=True, slots=True)
class MySQLTopologyDetection:
    """MySQL 拓扑检测结果."""

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


class MySQLTopologyDetector:
    """检测单个 MySQL 实例的 replication 拓扑状态."""

    def detect(self, connection: SyncConnection) -> MySQLTopologyDetection:
        try:
            rows = self._execute_rows(connection, REPLICA_STATUS_QUERY)
            replica_status_supported = True
        except (RuntimeError, ValueError, LookupError, ConnectionError, TimeoutError, OSError) as exc:
            if self.is_replication_status_permission_error(exc):
                raise
            if not self.is_replica_status_unsupported(exc):
                raise
            rows = []
            replica_status_supported = False

        if rows:
            detected = self.normalize_replica_status(rows[0], new_names=True)
            detected.update(self.detect_read_only_state(connection))
            return MySQLTopologyDetection(detected)
        if replica_status_supported:
            return MySQLTopologyDetection(self.detect_non_replica(connection))

        try:
            rows = self._execute_rows(connection, SLAVE_STATUS_QUERY)
        except (RuntimeError, ValueError, LookupError, ConnectionError, TimeoutError, OSError) as exc:
            if self.is_replication_status_permission_error(exc):
                raise
            rows = []
        if rows:
            detected = self.normalize_replica_status(rows[0], new_names=False)
            detected.update(self.detect_read_only_state(connection))
            return MySQLTopologyDetection(detected)
        return MySQLTopologyDetection(self.detect_non_replica(connection))

    @staticmethod
    def _execute_rows(connection: SyncConnection, query: str) -> list[Any]:
        dict_query = getattr(connection, "execute_dict_query", None)
        if callable(dict_query):
            return cast(list[Any], list(cast(Any, dict_query)(query)))
        return list(connection.execute_query(query))

    @classmethod
    def normalize_replica_status(cls, row: Any, *, new_names: bool) -> dict[str, Any]:
        mapping = cls.row_to_mapping(row)
        source_host = mapping.get("Source_Host" if new_names else "Master_Host")
        source_port = mapping.get("Source_Port" if new_names else "Master_Port")
        io_running = str(mapping.get("Replica_IO_Running" if new_names else "Slave_IO_Running") or "").strip()
        sql_running = str(mapping.get("Replica_SQL_Running" if new_names else "Slave_SQL_Running") or "").strip()
        seconds_behind = mapping.get("Seconds_Behind_Source" if new_names else "Seconds_Behind_Master")
        io_state = mapping.get("Replica_IO_State" if new_names else "Slave_IO_State")
        source_log_file = mapping.get("Source_Log_File" if new_names else "Master_Log_File")
        read_source_log_pos = mapping.get("Read_Source_Log_Pos" if new_names else "Read_Master_Log_Pos")
        relay_source_log_file = mapping.get("Relay_Source_Log_File" if new_names else "Relay_Master_Log_File")
        exec_source_log_pos = mapping.get("Exec_Source_Log_Pos" if new_names else "Exec_Master_Log_Pos")
        last_io_error = cls.optional_str(mapping.get("Last_IO_Error"))
        last_sql_error = cls.optional_str(mapping.get("Last_SQL_Error"))
        last_error = last_sql_error or last_io_error or cls.optional_str(mapping.get("Last_Error"))
        healthy = io_running.lower() == "yes" and sql_running.lower() == "yes"
        return {
            "replication_role": "replica",
            "replication_status": "healthy" if healthy else "unhealthy",
            "source_host": str(source_host).strip() if source_host is not None else None,
            "source_port": cls.optional_int(source_port),
            "io_running": io_running or None,
            "sql_running": sql_running or None,
            "seconds_behind_source": cls.optional_int(seconds_behind),
            "io_state": cls.optional_str(io_state),
            "source_log_file": cls.optional_str(source_log_file),
            "read_source_log_pos": cls.optional_int(read_source_log_pos),
            "relay_source_log_file": cls.optional_str(relay_source_log_file),
            "exec_source_log_pos": cls.optional_int(exec_source_log_pos),
            "sql_delay": cls.optional_int(mapping.get("SQL_Delay")),
            "retrieved_gtid_set": cls.optional_str(mapping.get("Retrieved_Gtid_Set")),
            "executed_gtid_set": cls.optional_str(mapping.get("Executed_Gtid_Set")),
            "last_io_error": last_io_error,
            "last_sql_error": last_sql_error,
            "last_error": last_error,
        }

    @classmethod
    def detect_non_replica(cls, connection: SyncConnection) -> dict[str, Any]:
        state = cls.detect_read_only_state(connection)
        read_only = state["read_only"]
        super_read_only = state["super_read_only"]
        role = "unknown" if read_only or super_read_only else "primary"
        return {
            "replication_role": role,
            "replication_status": "healthy" if role == "primary" else "unknown",
            "read_only": read_only,
            "super_read_only": super_read_only,
        }

    @classmethod
    def detect_read_only_state(cls, connection: SyncConnection) -> dict[str, bool | None]:
        rows = list(connection.execute_query(READ_ONLY_QUERY))
        read_only = None
        super_read_only = None
        if rows:
            row = rows[0]
            if isinstance(row, Mapping):
                read_only = cls.as_bool(row.get("read_only"))
                super_read_only = cls.as_bool(row.get("super_read_only"))
            elif isinstance(row, Sequence) and not isinstance(row, str):
                values = list(row)
                read_only = cls.as_bool(values[0]) if values else None
                super_read_only = cls.as_bool(values[1]) if len(values) > 1 else None
        return {
            "read_only": read_only,
            "super_read_only": super_read_only,
        }

    @staticmethod
    def is_replication_status_permission_error(exc: BaseException) -> bool:
        message = str(exc).lower()
        if "replication client" in message:
            return True
        return "1227" in message and "access denied" in message

    @staticmethod
    def is_replica_status_unsupported(exc: BaseException) -> bool:
        message = str(exc).lower()
        return any(marker in message for marker in MYSQL_REPLICA_STATUS_UNSUPPORTED_MARKERS)

    @staticmethod
    def row_to_mapping(row: Any) -> Mapping[str, Any]:
        if isinstance(row, Mapping):
            return row
        raise ValueError("MySQL replication status row must include column names")

    @staticmethod
    def as_bool(value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        return str(value).strip().lower() in {"1", "on", "true", "yes"}

    @staticmethod
    def optional_int(value: Any) -> int | None:
        if value in {None, ""}:
            return None
        return int(value)

    @staticmethod
    def optional_str(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
