"""
分区统计服务
"""

from __future__ import annotations

from typing import Any

from app.services.partition_management_service import PartitionManagementService


class PartitionStatisticsService(PartitionManagementService):
    """提供分区统计相关的查询能力。"""

    def get_partition_info(self) -> dict[str, Any]:
        total_size_bytes = 0
        total_records = 0
        partitions: list[dict[str, Any]] = []

        for table_key, table_config in self.tables.items():
            table_partitions = self._get_table_partitions(table_key, table_config)
            partitions.extend(table_partitions)
            total_size_bytes += sum(partition.get("size_bytes", 0) for partition in table_partitions)
            total_records += sum(partition.get("record_count", 0) for partition in table_partitions)

        return {
            "partitions": partitions,
            "total_partitions": len(partitions),
            "total_size_bytes": total_size_bytes,
            "total_size": self._format_size(total_size_bytes),
            "total_records": total_records,
            "tables": list(self.tables.keys()),
        }

    def get_partition_statistics(self) -> dict[str, Any]:
        info = self.get_partition_info()
        return {
            "total_records": info["total_records"],
            "total_partitions": info["total_partitions"],
            "total_size": info["total_size"],
            "total_size_bytes": info["total_size_bytes"],
            "partitions": info["partitions"],
            "tables": info["tables"],
        }
