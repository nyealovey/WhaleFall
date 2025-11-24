"""
分区统计服务
"""

from __future__ import annotations

from typing import Any

from app.services.partition_management_service import PartitionManagementService


class PartitionStatisticsService(PartitionManagementService):
    """提供分区统计相关的查询能力。

    继承自 PartitionManagementService，提供分区信息查询和统计功能。
    """

    def get_partition_info(self) -> dict[str, Any]:
        """获取所有分区的详细信息。

        查询所有表的分区信息，包括分区名称、大小、记录数等。

        Returns:
            包含分区详细信息的字典，格式如下：
            {
                'partitions': [...],          # 分区列表
                'total_partitions': 10,       # 分区总数
                'total_size_bytes': 1024000,  # 总大小（字节）
                'total_size': '1.0 MB',       # 总大小（格式化）
                'total_records': 50000,       # 总记录数
                'tables': ['stats', 'aggregations']  # 表名列表
            }
        """
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
        """获取分区统计信息。

        获取分区的汇总统计信息，包括总记录数、总分区数、总大小等。

        Returns:
            包含分区统计信息的字典，格式与 get_partition_info 返回值相同。
        """
        info = self.get_partition_info()
        return {
            "total_records": info["total_records"],
            "total_partitions": info["total_partitions"],
            "total_size": info["total_size"],
            "total_size_bytes": info["total_size_bytes"],
            "partitions": info["partitions"],
            "tables": info["tables"],
        }
