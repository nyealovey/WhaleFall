from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter
from app.utils.time_utils import time_utils


class MySQLCapacityAdapter(BaseCapacityAdapter):
    """MySQL 容量同步适配器。"""

    _SYSTEM_DATABASES = {"information_schema", "performance_schema", "mysql", "sys"}

    def fetch_inventory(self, instance, connection) -> List[dict]:
        result = connection.execute_query("SHOW DATABASES")
        metadata: List[dict] = []

        for row in result or []:
            if not row:
                continue
            name = str(row[0]).strip()
            if not name:
                continue
            metadata.append(
                {
                    "database_name": name,
                    "is_system": name in self._SYSTEM_DATABASES,
                }
            )

        self.logger.info(
            "fetch_mysql_inventory_success",
            instance=instance.name,
            database_count=len(metadata),
        )
        return metadata

    def fetch_capacity(
        self,
        instance,
        connection,
        target_databases: Optional[Sequence[str]] = None,
    ) -> List[dict]:
        normalized_target = self._normalize_targets(target_databases)

        if normalized_target == set():
            self.logger.info(
                "mysql_skip_capacity_no_targets",
                instance=instance.name,
            )
            return []

        self._assert_permission(connection, instance)

        try:
            tablespace_stats = self._collect_tablespace_sizes(connection, instance)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error(
                "mysql_tablespace_collection_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            raise

        data = self._build_stats_from_tablespaces(instance, tablespace_stats)

        if normalized_target is not None:
            filtered = [
                item for item in data if item["database_name"] in normalized_target
            ]
            missing = normalized_target.difference({row["database_name"] for row in filtered})
            if missing:
                self.logger.warning(
                    "mysql_capacity_missing_databases",
                    instance=instance.name,
                    missing=list(sorted(missing)),
                )
            return filtered

        return data

    def _assert_permission(self, connection, instance) -> None:
        test_query = "SELECT COUNT(*) FROM information_schema.SCHEMATA"
        result = connection.execute_query(test_query)
        if not result:
            error_msg = "MySQL 权限测试失败：无法访问 information_schema.SCHEMATA"
            self.logger.error(
                "mysql_permission_check_failed",
                instance=instance.name,
            )
            raise ValueError(error_msg)

        self.logger.info(
            "mysql_schema_access_verified",
            instance=instance.name,
            schema_count=result[0][0] if result and result[0] else 0,
        )

    def _collect_tablespace_sizes(self, connection, instance) -> Dict[str, int]:
        queries: List[Tuple[str, str]] = self._build_tablespace_queries(instance)
        aggregated: Dict[str, int] = {}

        for label, query in queries:
            try:
                result = connection.execute_query(query)
                if result:
                    self.logger.info(
                        "mysql_tablespace_query_success",
                        instance=instance.name,
                        view=label,
                        record_count=len(result),
                    )
                    for row in result:
                        if not row:
                            continue
                        raw_name = str(row[0])
                        if not raw_name:
                            continue
                        db_name = raw_name.split("/", 1)[0] if "/" in raw_name else raw_name
                        total_bytes = row[1] if len(row) > 1 else None
                        if total_bytes is None:
                            continue
                        try:
                            total_bytes_int = int(total_bytes)
                        except (TypeError, ValueError):
                            total_bytes_int = int(float(total_bytes or 0))
                        aggregated[db_name] = aggregated.get(db_name, 0) + max(total_bytes_int, 0)
                    if aggregated:
                        break
                else:
                    self.logger.info(
                        "mysql_tablespace_query_empty",
                        instance=instance.name,
                        view=label,
                    )
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "mysql_tablespace_query_failed",
                    instance=instance.name,
                    view=label,
                    error=str(exc),
                    exc_info=True,
                )

        # 确保所有库都存在
        try:
            databases_result = connection.execute_query("SHOW DATABASES")
            if databases_result:
                for row in databases_result:
                    if not row:
                        continue
                    db_name = str(row[0])
                    if not db_name:
                        continue
                    aggregated.setdefault(db_name, 0)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "mysql_show_databases_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )

        return aggregated

    def _build_stats_from_tablespaces(self, instance, stats: Dict[str, int]) -> List[dict]:
        china_now = time_utils.now_china()
        collected_at = time_utils.now()
        data: List[dict] = []

        for db_name, total_bytes in stats.items():
            try:
                total_bytes_int = int(total_bytes)
            except (TypeError, ValueError):
                total_bytes_int = int(float(total_bytes or 0))

            size_mb = max(total_bytes_int // (1024 * 1024), 0)
            is_system_db = db_name in self._SYSTEM_DATABASES

            data.append(
                {
                    "database_name": db_name,
                    "size_mb": size_mb,
                    "data_size_mb": size_mb,
                    "log_size_mb": None,
                    "collected_date": china_now.date(),
                    "collected_at": collected_at,
                    "is_system": is_system_db,
                }
            )

            self.logger.debug(
                "mysql_database_tablespace_size",
                instance=instance.name,
                database=db_name,
                size_mb=size_mb,
                system_database=is_system_db,
            )

        return data

    def _build_tablespace_queries(self, instance) -> List[Tuple[str, str]]:
        normalized_version = (instance.main_version or "").strip().lower()
        query_innodb_tablespaces = """
            SELECT
                ts.NAME,
                ts.FILE_SIZE
            FROM information_schema.INNODB_TABLESPACES ts
        """
        query_innodb_sys_tablespaces = """
            SELECT
                ts.NAME,
                ts.FILE_SIZE
            FROM information_schema.INNODB_SYS_TABLESPACES ts
        """

        if normalized_version.startswith("8"):
            return [
                ("INNODB_TABLESPACES", query_innodb_tablespaces),
                ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
            ]
        if normalized_version.startswith("5"):
            return [
                ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
                ("INNODB_TABLESPACES", query_innodb_tablespaces),
            ]
        return [
            ("INNODB_TABLESPACES", query_innodb_tablespaces),
            ("INNODB_SYS_TABLESPACES", query_innodb_sys_tablespaces),
        ]
