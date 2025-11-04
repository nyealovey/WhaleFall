from __future__ import annotations

from typing import List, Optional, Sequence

from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter
from app.utils.time_utils import time_utils


class SQLServerCapacityAdapter(BaseCapacityAdapter):
    """SQL Server 容量同步适配器。"""

    def fetch_inventory(self, instance, connection) -> List[dict]:
        query = """
            SELECT
                name,
                CASE WHEN database_id <= 4 THEN 1 ELSE 0 END AS is_system
            FROM sys.databases
            WHERE name IS NOT NULL
        """

        result = connection.execute_query(query)
        metadata: List[dict] = []
        for row in result or []:
            name = str(row[0]).strip() if row and row[0] is not None else ""
            if not name:
                continue
            is_system = bool(row[1] if len(row) > 1 else False)
            metadata.append({"database_name": name, "is_system": is_system})

        self.logger.info(
            "fetch_sqlserver_inventory_success",
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
                "sqlserver_skip_capacity_no_targets",
                instance=instance.name,
            )
            return []

        query = """
            SELECT
                DB_NAME(database_id) AS DatabaseName,
                SUM(CASE WHEN type_desc = 'ROWS' THEN size * 8.0 / 1024 ELSE 0 END) AS DataFileSize_MB
            FROM sys.master_files
            WHERE DB_NAME(database_id) IS NOT NULL
            GROUP BY database_id
            ORDER BY DataFileSize_MB DESC
        """

        result = connection.execute_query(query)
        if not result:
            error_msg = "SQL Server 未查询到任何数据库大小数据"
            self.logger.error(
                "sqlserver_capacity_empty",
                instance=instance.name,
            )
            raise ValueError(error_msg)

        china_now = time_utils.now_china()
        data: List[dict] = []
        for row in result:
            database_name = row[0]
            if normalized_target is not None and database_name not in normalized_target:
                continue

            data_size_mb = int(float(row[1] or 0))
            data.append(
                {
                    "database_name": database_name,
                    "size_mb": data_size_mb,
                    "data_size_mb": data_size_mb,
                    "log_size_mb": None,
                    "collected_date": china_now.date(),
                    "collected_at": time_utils.now(),
                    "is_system": False,
                }
            )

        if normalized_target is not None:
            missing = normalized_target.difference({row["database_name"] for row in data})
            if missing:
                self.logger.warning(
                    "sqlserver_capacity_missing",
                    instance=instance.name,
                    missing=list(sorted(missing)),
                )

        self.logger.info(
            "sqlserver_capacity_collection_success",
            instance=instance.name,
            database_count=len(data),
        )
        return data
