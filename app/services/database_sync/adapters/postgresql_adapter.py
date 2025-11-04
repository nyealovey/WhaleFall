from __future__ import annotations

from typing import List, Optional, Sequence

from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter
from app.utils.time_utils import time_utils


class PostgreSQLCapacityAdapter(BaseCapacityAdapter):
    """PostgreSQL 容量同步适配器。"""

    _SYSTEM_DATABASES = {"postgres"}

    def fetch_inventory(self, instance, connection) -> List[dict]:
        query = """
            SELECT
                datname,
                datistemplate
            FROM pg_database
            WHERE datallowconn = TRUE
        """

        result = connection.execute_query(query)
        metadata: List[dict] = []
        for row in result or []:
            name = str(row[0]).strip() if row and row[0] is not None else ""
            if not name:
                continue
            is_template = bool(row[1] if len(row) > 1 else False)
            is_system = is_template or name in self._SYSTEM_DATABASES
            metadata.append({"database_name": name, "is_system": is_system})

        self.logger.info(
            "fetch_postgresql_inventory_success",
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
                "postgresql_skip_capacity_no_targets",
                instance=instance.name,
            )
            return []

        query = """
            SELECT
                datname AS database_name,
                pg_database_size(datname) / 1024 / 1024 AS size_mb,
                pg_database_size(datname) / 1024 / 1024 AS data_size_mb
            FROM
                pg_database
            WHERE
                datistemplate = false
            ORDER BY
                size_mb DESC
        """

        result = connection.execute_query(query)
        if not result:
            error_msg = "PostgreSQL 未查询到任何数据库大小数据"
            self.logger.error(
                "postgresql_capacity_empty",
                instance=instance.name,
            )
            raise ValueError(error_msg)

        china_now = time_utils.now_china()
        data: List[dict] = []
        for row in result:
            name = row[0]
            if normalized_target is not None and name not in normalized_target:
                continue

            data.append(
                {
                    "database_name": name,
                    "size_mb": int(row[1] or 0),
                    "data_size_mb": int(row[2] or 0),
                    "log_size_mb": None,
                    "collected_date": china_now.date(),
                    "collected_at": time_utils.now(),
                    "is_system": name in self._SYSTEM_DATABASES,
                }
            )

        if normalized_target is not None:
            missing = normalized_target.difference({row["database_name"] for row in data})
            if missing:
                self.logger.warning(
                    "postgresql_capacity_missing",
                    instance=instance.name,
                    missing=list(sorted(missing)),
                )

        self.logger.info(
            "postgresql_capacity_collection_success",
            instance=instance.name,
            database_count=len(data),
        )
        return data
