import pytest

from app.services.partition.partition_read_service import PartitionReadService
from app.services.partition_management_service import PartitionManagementService
from app.services.statistics.partition_statistics_service import PartitionStatisticsService
from app.types.listing import PaginatedResult
from app.types.partition import (
    PartitionCoreMetricsResult,
    PartitionEntry,
    PartitionInfoSnapshot,
    PartitionStatusSnapshot,
)


@pytest.mark.unit
def test_api_v1_partition_requires_auth(client) -> None:
    response = client.get("/api/v1/partition/info")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    create_response = client.post("/api/v1/partition/create", json={"date": "2099-12-27"}, headers=headers)
    assert create_response.status_code == 401
    payload = create_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_partition_endpoints_contract(auth_client, monkeypatch) -> None:  # noqa: PLR0915
    def _dummy_info(self):
        del self
        return PartitionInfoSnapshot(
            partitions=[
                PartitionEntry(
                    name="p202512",
                    table="t",
                    table_type="stats",
                    display_name="p202512",
                    size="1 MB",
                    size_bytes=1024 * 1024,
                    record_count=1,
                    date="2025-12-01",
                    status="healthy",
                ),
            ],
            total_partitions=1,
            total_size_bytes=1024 * 1024,
            total_size="1 MB",
            total_records=1,
            tables=["stats"],
            status="healthy",
            missing_partitions=[],
        )

    def _dummy_status(self):
        del self
        return PartitionStatusSnapshot(
            status="healthy",
            total_partitions=1,
            total_size="1 MB",
            total_records=1,
            missing_partitions=[],
            partitions=[],
        )

    def _dummy_list_partitions(self, **kwargs):
        del self, kwargs
        return PaginatedResult(
            items=[
                PartitionEntry(
                    name="p202512",
                    table="t",
                    table_type="stats",
                    display_name="p202512",
                    size="1 MB",
                    size_bytes=1024 * 1024,
                    record_count=1,
                    date="2025-12-01",
                    status="healthy",
                ),
            ],
            total=1,
            page=1,
            pages=1,
            limit=20,
        )

    def _dummy_core_metrics(self, *, period_type, days):
        del self, period_type, days
        return PartitionCoreMetricsResult(
            labels=["2099-12-27"],
            datasets=[{"label": "x", "data": [1]}],
            dataPointCount=1,
            timeRange="7d",
            yAxisLabel="count",
            chartTitle="core",
            periodType="daily",
        )

    def _dummy_create(self, partition_date):
        del self, partition_date
        return {"created": True}

    def _dummy_cleanup(self, *, retention_months):
        del self, retention_months
        return {"cleaned": True}

    def _dummy_statistics(self):
        del self
        return {"total_partitions": 1}

    monkeypatch.setattr(PartitionReadService, "get_partition_info_snapshot", _dummy_info)
    monkeypatch.setattr(PartitionReadService, "get_partition_status_snapshot", _dummy_status)
    monkeypatch.setattr(PartitionReadService, "list_partitions", _dummy_list_partitions)
    monkeypatch.setattr(PartitionReadService, "build_core_metrics", _dummy_core_metrics)
    monkeypatch.setattr(PartitionManagementService, "create_partition", _dummy_create)
    monkeypatch.setattr(PartitionManagementService, "cleanup_old_partitions", _dummy_cleanup)
    monkeypatch.setattr(PartitionStatisticsService, "get_partition_statistics", _dummy_statistics)

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    info_response = auth_client.get("/api/v1/partition/info")
    assert info_response.status_code == 200
    payload = info_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    status_response = auth_client.get("/api/v1/partition/status")
    assert status_response.status_code == 200
    payload = status_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    list_response = auth_client.get("/api/v1/partition/partitions")
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())

    statistics_response = auth_client.get("/api/v1/partition/statistics")
    assert statistics_response.status_code == 200
    payload = statistics_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    core_metrics_response = auth_client.get("/api/v1/partition/aggregations/core-metrics")
    assert core_metrics_response.status_code == 200
    payload = core_metrics_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    create_response = auth_client.post("/api/v1/partition/create", json={"date": "2099-12-27"}, headers=headers)
    assert create_response.status_code == 200
    payload = create_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    cleanup_response = auth_client.post("/api/v1/partition/cleanup", json={"retention_months": 12}, headers=headers)
    assert cleanup_response.status_code == 200
    payload = cleanup_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
