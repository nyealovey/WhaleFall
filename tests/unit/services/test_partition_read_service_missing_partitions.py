from datetime import UTC, datetime

import pytest

from app.services.partition.partition_read_service import PartitionReadService
from app.tasks.partition_management_tasks import get_partition_management_status
from app.core.types.partition import PartitionEntry


@pytest.mark.unit
def test_partition_read_service_only_checks_current_and_next_month(monkeypatch) -> None:
    fixed_now = datetime(2025, 1, 15, tzinfo=UTC)

    import app.services.partition.partition_read_service as partition_read_module

    monkeypatch.setattr(partition_read_module.time_utils, "now", lambda: fixed_now)

    partitions = [
        PartitionEntry(
            name="database_size_stats_2025_01",
            table="database_size_stats",
            table_type="stats",
            display_name="数据库统计表",
            size="0 B",
            size_bytes=0,
            record_count=0,
            date="2025/01/01",
            status="current",
        ),
    ]

    missing, status = PartitionReadService._resolve_missing_partitions(partitions)
    assert missing == ["database_size_stats_2025_02"]
    assert status == "warning"


@pytest.mark.unit
def test_partition_tasks_status_only_checks_current_and_next_month(monkeypatch) -> None:
    fixed_now = datetime(2025, 1, 15, tzinfo=UTC)

    import app.tasks.partition_management_tasks as partition_tasks_module
    from app.services.statistics.partition_statistics_service import PartitionStatisticsService

    monkeypatch.setattr(partition_tasks_module.time_utils, "now", lambda: fixed_now)

    def _dummy_info(self):  # noqa: ANN001
        return {"partitions": [{"name": "database_size_stats_2025_01"}]}

    def _dummy_stats(self):  # noqa: ANN001
        return {"total_partitions": 1, "total_size": "0 B", "total_records": 0}

    monkeypatch.setattr(PartitionStatisticsService, "get_partition_info", _dummy_info)
    monkeypatch.setattr(PartitionStatisticsService, "get_partition_statistics", _dummy_stats)

    result = get_partition_management_status()
    assert result["missing_partitions"] == ["database_size_stats_2025_02"]
    assert result["status"] == "warning"

