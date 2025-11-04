from __future__ import annotations

from typing import List, Optional, Sequence

from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter
from app.utils.time_utils import time_utils


class OracleCapacityAdapter(BaseCapacityAdapter):
    """Oracle 容量同步适配器。"""

    def fetch_inventory(self, instance, connection) -> List[dict]:
        query = """
            SELECT DISTINCT
                tablespace_name
            FROM
                dba_data_files
            WHERE
                tablespace_name IS NOT NULL
        """

        result = connection.execute_query(query)
        metadata: List[dict] = []
        for row in result or []:
            name = str(row[0]).strip() if row and row[0] is not None else ""
            if not name:
                continue
            metadata.append({"database_name": name, "is_system": False})

        self.logger.info(
            "fetch_oracle_inventory_success",
            instance=instance.name,
            tablespace_count=len(metadata),
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
                "oracle_skip_capacity_no_targets",
                instance=instance.name,
            )
            return []

        query = """
            SELECT
                tablespace_name AS database_name,
                SUM(bytes) / 1024 / 1024 AS size_mb,
                SUM(bytes) / 1024 / 1024 AS data_size_mb
            FROM
                dba_data_files
            GROUP BY
                tablespace_name
            ORDER BY
                size_mb DESC
        """

        result = connection.execute_query(query)
        if not result:
            error_msg = "Oracle 未查询到任何数据库大小数据"
            self.logger.error(
                "oracle_capacity_empty",
                instance=instance.name,
            )
            raise ValueError(error_msg)

        china_now = time_utils.now_china()
        data: List[dict] = []
        for row in result:
            database_name = row[0]
            if normalized_target is not None and database_name not in normalized_target:
                continue

            data.append(
                {
                    "database_name": database_name,
                    "size_mb": int(row[1] or 0),
                    "data_size_mb": int(row[2] or 0),
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
                    "oracle_capacity_missing",
                    instance=instance.name,
                    missing=list(sorted(missing)),
                )

        self.logger.info(
            "oracle_capacity_collection_success",
            instance=instance.name,
            database_count=len(data),
        )
        return data
