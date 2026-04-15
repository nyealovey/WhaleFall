from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.services.instances.instance_statistics_read_service import InstanceStatisticsReadService


@pytest.mark.unit
def test_instance_statistics_read_service_builds_statistics_with_current_instances() -> None:
    class _Repository:
        @staticmethod
        def fetch_summary() -> dict[str, int]:
            return {
                "total_instances": 82,
                "current_instances": 78,
                "active_instances": 78,
                "normal_instances": 78,
                "disabled_instances": 0,
                "deleted_instances": 4,
                "audit_enabled_instances": 14,
                "high_availability_instances": 11,
                "managed_instances": 52,
                "unmanaged_instances": 26,
                "backed_up_instances": 46,
                "backup_stale_instances": 12,
                "not_backed_up_instances": 20,
            }

        @staticmethod
        def fetch_db_type_stats() -> list[Any]:
            return [SimpleNamespace(db_type="sqlserver", count=78)]

        @staticmethod
        def fetch_port_stats(limit: int = 10) -> list[Any]:
            assert limit == 10
            return [SimpleNamespace(port=1433, count=78)]

        @staticmethod
        def fetch_version_stats() -> list[Any]:
            return [SimpleNamespace(db_type="sqlserver", main_version="11.0", count=78)]

    service = InstanceStatisticsReadService(repository=cast(Any, _Repository()))

    result = service.build_statistics()

    assert result.total_instances == 82
    assert result.current_instances == 78
    assert result.active_instances == 78
    assert result.inactive_instances == 0
    assert result.deleted_instances == 4
    assert result.audit_enabled_instances == 14
    assert result.high_availability_instances == 11
    assert result.managed_instances == 52
    assert result.unmanaged_instances == 26
    assert result.backed_up_instances == 46
    assert result.backup_stale_instances == 12
    assert result.not_backed_up_instances == 20
    assert result.backup_status_stats == [
        {"backup_status": "backed_up", "count": 46},
        {"backup_status": "backup_stale", "count": 12},
        {"backup_status": "not_backed_up", "count": 20},
    ]
    assert result.db_types_count == 1


@pytest.mark.unit
def test_instance_statistics_read_service_empty_statistics_includes_current_instances() -> None:
    result = InstanceStatisticsReadService.empty_statistics()

    assert result.total_instances == 0
    assert result.current_instances == 0
    assert result.active_instances == 0
    assert result.inactive_instances == 0
    assert result.deleted_instances == 0
    assert result.audit_enabled_instances == 0
    assert result.high_availability_instances == 0
    assert result.managed_instances == 0
    assert result.unmanaged_instances == 0
    assert result.backed_up_instances == 0
    assert result.backup_stale_instances == 0
    assert result.not_backed_up_instances == 0
    assert result.backup_status_stats == [
        {"backup_status": "backed_up", "count": 0},
        {"backup_status": "backup_stale", "count": 0},
        {"backup_status": "not_backed_up", "count": 0},
    ]
