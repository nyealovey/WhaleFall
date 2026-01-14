from datetime import UTC, datetime

import pytest

from app.services.partition.partition_read_service import PartitionReadService
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
