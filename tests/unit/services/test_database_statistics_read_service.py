from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.services.statistics.database_statistics_read_service import DatabaseStatisticsReadService


@pytest.mark.unit
def test_database_statistics_read_service_builds_statistics(monkeypatch) -> None:
    now = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)
    monkeypatch.setattr("app.services.statistics.database_statistics_read_service.time_utils.now", lambda: now)

    class _Repository:
        @staticmethod
        def fetch_summary() -> dict[str, int]:
            return {
                "total_databases": 8,
                "active_databases": 6,
                "inactive_databases": 1,
                "deleted_databases": 2,
                "total_instances": 3,
            }

        @staticmethod
        def fetch_db_type_stats() -> list[Any]:
            return [
                SimpleNamespace(db_type="mysql", count=4),
                SimpleNamespace(db_type="postgresql", count=2),
            ]

        @staticmethod
        def fetch_instance_stats(limit: int = 10) -> list[Any]:
            assert limit == 10
            return [
                SimpleNamespace(instance_id=1, instance_name="prod-mysql-1", db_type="mysql", count=4),
                SimpleNamespace(instance_id=2, instance_name="prod-pg-1", db_type="postgresql", count=2),
            ]

        @staticmethod
        def fetch_latest_sync_rows() -> list[Any]:
            return [
                SimpleNamespace(collected_at=now - timedelta(hours=1)),
                SimpleNamespace(collected_at=now - timedelta(hours=12)),
                SimpleNamespace(collected_at=now - timedelta(hours=72)),
                SimpleNamespace(collected_at=None),
            ]

        @staticmethod
        def fetch_capacity_rankings(limit: int = 10) -> list[Any]:
            assert limit == 10
            return [
                SimpleNamespace(
                    instance_id=1,
                    instance_name="prod-mysql-1",
                    db_type="mysql",
                    database_name="app_db",
                    size_mb=2048,
                    collected_at=now - timedelta(hours=1),
                ),
                SimpleNamespace(
                    instance_id=2,
                    instance_name="prod-pg-1",
                    db_type="postgresql",
                    database_name="analytics",
                    size_mb=512,
                    collected_at=now - timedelta(hours=2),
                ),
            ]

    service = DatabaseStatisticsReadService(repository=cast(Any, _Repository()))

    result = service.build_statistics()

    assert result.total_databases == 8
    assert result.active_databases == 6
    assert result.inactive_databases == 1
    assert result.deleted_databases == 2
    assert result.total_instances == 3
    assert result.total_size_mb == 2560
    assert result.avg_size_mb == 1280
    assert result.max_size_mb == 2048
    assert [(item.db_type, item.count) for item in result.db_type_stats] == [
        ("mysql", 4),
        ("postgresql", 2),
    ]
    assert [(item.instance_name, item.count) for item in result.instance_stats] == [
        ("prod-mysql-1", 4),
        ("prod-pg-1", 2),
    ]
    assert [(item.value, item.count) for item in result.sync_status_stats] == [
        ("completed", 1),
        ("running", 1),
        ("failed", 1),
        ("pending", 1),
    ]
    assert result.capacity_rankings[0].size_label == "2.00 GB"
    assert result.capacity_rankings[1].size_label == "512 MB"


@pytest.mark.unit
def test_database_statistics_read_service_returns_empty_payload_when_no_rows() -> None:
    class _Repository:
        @staticmethod
        def fetch_summary() -> dict[str, int]:
            return {
                "total_databases": 0,
                "active_databases": 0,
                "inactive_databases": 0,
                "deleted_databases": 0,
                "total_instances": 0,
            }

        @staticmethod
        def fetch_db_type_stats() -> list[Any]:
            return []

        @staticmethod
        def fetch_instance_stats(limit: int = 10) -> list[Any]:
            assert limit == 10
            return []

        @staticmethod
        def fetch_latest_sync_rows() -> list[Any]:
            return []

        @staticmethod
        def fetch_capacity_rankings(limit: int = 10) -> list[Any]:
            assert limit == 10
            return []

    service = DatabaseStatisticsReadService(repository=cast(Any, _Repository()))

    result = service.build_statistics()

    assert result.total_databases == 0
    assert result.total_size_mb == 0
    assert result.avg_size_mb == 0
    assert result.max_size_mb == 0
    assert result.db_type_stats == []
    assert result.instance_stats == []
    assert result.sync_status_stats == []
    assert result.capacity_rankings == []
