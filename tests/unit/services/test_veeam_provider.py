from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from flask import Flask

from app.services.veeam.provider import HttpVeeamProvider
from app.services.veeam.provider import VeeamMachineBackupRecord


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.unit
def test_http_veeam_provider_requests_backups_first_then_restore_points_across_next_links() -> None:
    captured_requests: list[dict[str, Any]] = []
    payloads = [
        {"access_token": "token-1"},
        {
            "items": [
                {
                    "id": "backup-object-1",
                    "platformName": "WindowsPhysical",
                    "name": "db01.domain.com",
                    "restorePointsCount": 2,
                }
            ],
            "next": "https://veeam.example.com:9419/api/v1/backupObjects?page=2",
        },
        {
            "items": [
                {
                    "id": "backup-object-2",
                    "platformName": "WindowsPhysical",
                    "name": "db02.domain.com",
                    "restorePointsCount": 1,
                }
            ],
            "next": None,
        },
        {
            "items": [
                {
                    "machineName": "db01.domain.com",
                    "creationTime": "2026-03-25T01:00:00Z",
                    "restorePointName": "rp-1",
                    "id": "rp-1",
                    "backupId": "backup-1",
                    "backupFileId": "file-1",
                },
                {
                    "machineName": "db01.domain.com",
                    "creationTime": "2026-03-25T02:00:00Z",
                    "restorePointName": "rp-2",
                    "id": "rp-2",
                    "backupId": "backup-1",
                    "backupFileId": "file-2",
                }
            ],
            "next": None,
        },
        {
            "items": [
                {
                    "machineName": "db02.domain.com",
                    "creationTime": "2026-03-25T03:00:00Z",
                    "restorePointName": "rp-3",
                    "id": "rp-3",
                    "backupId": "backup-2",
                    "backupFileId": "file-3",
                }
            ],
            "next": None,
        },
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        captured_requests.append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "headers": {key.lower(): value for key, value in request.header_items()},
                "timeout": timeout,
                "context": context,
            }
        )
        return _FakeResponse(payloads[len(captured_requests) - 1])

    provider = HttpVeeamProvider(timeout_seconds=12, verify_ssl=True, opener=_fake_opener)

    result = provider.list_machine_backups(
        server_host="veeam.example.com",
        server_port=9419,
        username="DOMAIN\\user",
        password="secret",
        api_version="1.3-rev1",
        match_machine_names={"db01.domain.com", "db02.domain.com"},
    )

    assert result.received_total == 3
    assert result.snapshots_written_total == 3
    assert result.skipped_invalid == 0
    assert [record.machine_name for record in result.records] == ["db01.domain.com", "db01.domain.com", "db02.domain.com"]

    assert len(captured_requests) == 5
    assert captured_requests[0]["url"] == "https://veeam.example.com:9419/api/oauth2/token"
    assert captured_requests[1]["url"] == "https://veeam.example.com:9419/api/v1/backupObjects?limit=2000"
    assert captured_requests[2]["url"] == "https://veeam.example.com:9419/api/v1/backupObjects?page=2"
    assert captured_requests[3]["url"] == "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-1/restorePoints"
    assert captured_requests[4]["url"] == "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-2/restorePoints"


@pytest.mark.unit
def test_http_veeam_provider_uses_backup_page_metadata_when_next_link_missing() -> None:
    captured_urls: list[str] = []
    payloads = [
        {"access_token": "token-1"},
        {
            "items": [
                {
                    "id": "backup-object-1",
                    "platformName": "WindowsPhysical",
                    "name": "db01.domain.com",
                }
            ],
            "page": 1,
            "pageSize": 1,
            "total": 2,
        },
        {
            "items": [
                {
                    "id": "backup-object-2",
                    "platformName": "WindowsPhysical",
                    "name": "db02.domain.com",
                }
            ],
            "page": 2,
            "pageSize": 1,
            "total": 2,
        },
        {
            "items": [
                {
                    "machineName": "db01.domain.com",
                    "creationTime": "2026-03-25T01:00:00Z",
                    "id": "rp-1",
                    "backupId": "backup-1",
                }
            ],
            "next": None,
        },
        {
            "items": [
                {
                    "machineName": "db02.domain.com",
                    "creationTime": "2026-03-25T02:00:00Z",
                    "id": "rp-2",
                    "backupId": "backup-2",
                }
            ],
            "next": None,
        },
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        return _FakeResponse(payloads[len(captured_urls) - 1])

    provider = HttpVeeamProvider(opener=_fake_opener)

    result = provider.list_machine_backups(
        server_host="veeam.example.com",
        server_port=9419,
        username="DOMAIN\\user",
        password="secret",
        api_version="1.3-rev1",
        match_machine_names={"db01.domain.com", "db02.domain.com"},
    )

    assert result.received_total == 2
    assert [record.machine_name for record in result.records] == ["db01.domain.com", "db02.domain.com"]
    assert captured_urls == [
        "https://veeam.example.com:9419/api/oauth2/token",
        "https://veeam.example.com:9419/api/v1/backupObjects?limit=2000",
        "https://veeam.example.com:9419/api/v1/backupObjects?page=2&pageSize=1",
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-1/restorePoints",
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-2/restorePoints",
    ]


@pytest.mark.unit
def test_http_veeam_provider_uses_skip_limit_pagination_metadata_for_backups() -> None:
    captured_urls: list[str] = []
    payloads = [
        {"access_token": "token-1"},
        {
            "items": [
                {
                    "id": "backup-object-1",
                    "platformName": "WindowsPhysical",
                    "name": "db01.domain.com",
                }
            ],
            "skip": 0,
            "limit": 1,
            "total": 2,
        },
        {
            "items": [
                {
                    "id": "backup-object-2",
                    "platformName": "WindowsPhysical",
                    "name": "db02.domain.com",
                }
            ],
            "skip": 1,
            "limit": 1,
            "total": 2,
        },
        {
            "items": [
                {
                    "machineName": "db01.domain.com",
                    "creationTime": "2026-03-25T01:00:00Z",
                    "id": "rp-1",
                    "backupId": "backup-1",
                }
            ],
            "next": None,
        },
        {
            "items": [
                {
                    "machineName": "db02.domain.com",
                    "creationTime": "2026-03-25T02:00:00Z",
                    "id": "rp-2",
                    "backupId": "backup-2",
                }
            ],
            "next": None,
        },
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        return _FakeResponse(payloads[len(captured_urls) - 1])

    provider = HttpVeeamProvider(opener=_fake_opener)

    result = provider.list_machine_backups(
        server_host="veeam.example.com",
        server_port=9419,
        username="DOMAIN\\user",
        password="secret",
        api_version="1.3-rev1",
        match_machine_names={"db01.domain.com", "db02.domain.com"},
    )

    assert result.received_total == 2
    assert [record.machine_name for record in result.records] == ["db01.domain.com", "db02.domain.com"]
    assert captured_urls == [
        "https://veeam.example.com:9419/api/oauth2/token",
        "https://veeam.example.com:9419/api/v1/backupObjects?limit=2000",
        "https://veeam.example.com:9419/api/v1/backupObjects?skip=1&limit=1",
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-1/restorePoints",
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-2/restorePoints",
    ]


@pytest.mark.unit
def test_http_veeam_provider_requests_backup_objects_with_large_default_limit() -> None:
    captured_urls: list[str] = []
    payloads = [
        {"access_token": "token-1"},
        {
            "items": [
                {
                    "id": "backup-object-1",
                    "platformName": "HyperV",
                    "name": "中间件2",
                    "type": "VM",
                    "platformId": "00000000-0000-0000-0000-000000000000",
                    "restorePointsCount": 33,
                },
                {
                    "id": "backup-object-2",
                    "platformName": "HyperV",
                    "name": "中间件3",
                    "type": "VM",
                    "platformId": "00000000-0000-0000-0000-000000000000",
                    "restorePointsCount": 33,
                },
            ],
            "pagination": {
                "total": 1825,
                "count": 1825,
                "skip": 0,
                "limit": 2000,
            },
        },
        {
            "items": [
                {
                    "machineName": "中间件2",
                    "creationTime": "2026-03-25T01:00:00Z",
                    "id": "rp-1",
                    "backupId": "backup-1",
                }
            ],
            "next": None,
        },
        {
            "items": [
                {
                    "machineName": "中间件3",
                    "creationTime": "2026-03-25T02:00:00Z",
                    "id": "rp-2",
                    "backupId": "backup-2",
                }
            ],
            "next": None,
        },
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        return _FakeResponse(payloads[len(captured_urls) - 1])

    provider = HttpVeeamProvider(opener=_fake_opener)

    result = provider.list_machine_backups(
        server_host="veeam.example.com",
        server_port=9419,
        username="DOMAIN\\user",
        password="secret",
        api_version="1.3-rev1",
        match_machine_names={"中间件2", "中间件3"},
    )

    assert result.received_total == 2
    assert [record.machine_name for record in result.records] == ["中间件2", "中间件3"]
    assert captured_urls == [
        "https://veeam.example.com:9419/api/oauth2/token",
        "https://veeam.example.com:9419/api/v1/backupObjects?limit=2000",
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-1/restorePoints",
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-2/restorePoints",
    ]


@pytest.mark.unit
def test_http_veeam_provider_reads_backup_objects_limit_from_flask_config() -> None:
    captured_urls: list[str] = []
    payloads = [
        {"access_token": "token-1"},
        {"items": [], "pagination": {"total": 0, "count": 0, "skip": 0, "limit": 1500}},
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        return _FakeResponse(payloads[len(captured_urls) - 1])

    app = Flask(__name__)
    app.config["VEEAM_BACKUP_OBJECTS_LIMIT"] = 1500

    with app.app_context():
        provider = HttpVeeamProvider(opener=_fake_opener)
        result = provider.list_machine_backups(
            server_host="veeam.example.com",
            server_port=9419,
            username="DOMAIN\\user",
            password="secret",
            api_version="1.3-rev1",
            match_machine_names={"中间件2"},
        )

    assert result.received_total == 0
    assert captured_urls == [
        "https://veeam.example.com:9419/api/oauth2/token",
        "https://veeam.example.com:9419/api/v1/backupObjects?limit=1500",
    ]


@pytest.mark.unit
def test_http_veeam_provider_skips_unmatched_backups_before_fetching_restore_points() -> None:
    captured_urls: list[str] = []
    payloads = [
        {"access_token": "token-1"},
        {
            "items": [
                {
                    "id": "backup-object-1",
                    "platformName": "WindowsPhysical",
                    "name": "db01.domain.com",
                },
                {
                    "id": "backup-object-2",
                    "platformName": "WindowsPhysical",
                    "name": "unmatched.domain.com",
                },
            ],
            "next": None,
        },
        {
            "items": [
                {
                    "machineName": "db01.domain.com",
                    "creationTime": "2026-03-25T01:00:00Z",
                    "id": "rp-1",
                    "backupId": "backup-1",
                }
            ],
            "next": None,
        },
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        return _FakeResponse(payloads[len(captured_urls) - 1])

    provider = HttpVeeamProvider(opener=_fake_opener)

    result = provider.list_machine_backups(
        server_host="veeam.example.com",
        server_port=9419,
        username="DOMAIN\\user",
        password="secret",
        api_version="1.3-rev1",
        match_machine_names={"db01.domain.com"},
    )

    assert result.received_total == 1
    assert [record.machine_name for record in result.records] == ["db01.domain.com"]
    assert captured_urls == [
        "https://veeam.example.com:9419/api/oauth2/token",
        "https://veeam.example.com:9419/api/v1/backupObjects?limit=2000",
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-1/restorePoints",
    ]


@pytest.mark.unit
def test_http_veeam_provider_enriches_job_name_and_sizes_from_backup_details() -> None:
    captured_urls: list[str] = []
    payloads = [
        {"access_token": "token-1"},
        {"data": {"name": "daily-job", "restorePointCount": 3}},
        {
            "data": [
                {"id": "file-a", "restorePointIds": ["rp-1", "rp-2"], "backupSize": 256},
                {"id": "file-b", "restorePointIds": ["rp-2"], "backupSize": 128},
                {"id": "file-c", "restorePointIds": ["rp-x"], "backupSize": 999},
            ]
        },
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        return _FakeResponse(payloads[len(captured_urls) - 1])

    provider = HttpVeeamProvider(opener=_fake_opener)

    result = provider.enrich_machine_backups(
        server_host="veeam.example.com",
        server_port=9419,
        username="DOMAIN\\user",
        password="secret",
        api_version="1.3-rev1",
        records=[
            VeeamMachineBackupRecord(
                machine_name="db01.domain.com",
                backup_at=provider._resolve_backup_at({"creationTime": "2026-03-25T02:00:00Z"}) or datetime.now(UTC),
                backup_id="backup-1",
                backup_file_id="file-1",
                restore_point_name="rp-2",
                source_record_id="rp-2",
                raw_payload={
                    "id": "rp-2",
                    "restore_point_ids": ["rp-1", "rp-2"],
                    "restore_point_times": ["2026-03-25T02:00:00Z", "2026-03-25T01:00:00Z"],
                },
            )
        ],
    )

    assert len(result) == 1
    assert result[0].job_name == "daily-job"
    assert result[0].restore_point_size_bytes is None
    assert result[0].backup_chain_size_bytes == 384
    assert result[0].restore_point_count == 3
    assert captured_urls == [
        "https://veeam.example.com:9419/api/oauth2/token",
        "https://veeam.example.com:9419/api/v1/backups/backup-1",
        "https://veeam.example.com:9419/api/v1/backups/backup-1/backupFiles",
    ]


@pytest.mark.unit
def test_http_veeam_provider_enrichment_tolerates_missing_detail_endpoints() -> None:
    captured_urls: list[str] = []
    payloads = [
        {"access_token": "token-1"},
        {"unexpected": "shape"},
        {"unexpected": "shape"},
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        return _FakeResponse(payloads[len(captured_urls) - 1])

    provider = HttpVeeamProvider(opener=_fake_opener)

    result = provider.enrich_machine_backups(
        server_host="veeam.example.com",
        server_port=9419,
        username="DOMAIN\\user",
        password="secret",
        api_version="1.3-rev1",
        records=[
            VeeamMachineBackupRecord(
                machine_name="db01.domain.com",
                backup_at=provider._resolve_backup_at({"creationTime": "2026-03-25T02:00:00Z"}) or datetime.now(UTC),
                backup_id="backup-1",
                backup_file_id="file-1",
                restore_point_name="rp-2",
                source_record_id="rp-2",
                raw_payload={"id": "rp-2", "restore_point_ids": ["rp-2"]},
            )
        ],
    )

    assert len(result) == 1
    assert result[0].job_name is None
    assert result[0].restore_point_size_bytes is None
    assert result[0].backup_chain_size_bytes is None
    assert result[0].restore_point_count is None
    assert captured_urls == [
        "https://veeam.example.com:9419/api/oauth2/token",
        "https://veeam.example.com:9419/api/v1/backups/backup-1",
        "https://veeam.example.com:9419/api/v1/backups/backup-1/backupFiles",
    ]


@pytest.mark.unit
def test_http_veeam_provider_surfaces_timeout_with_url_and_timeout_seconds() -> None:
    captured_urls: list[str] = []

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        if "/api/v1/backupObjects" in request.full_url:
            raise TimeoutError("The read operation timed out")
        return _FakeResponse({"access_token": "token-1"})

    provider = HttpVeeamProvider(timeout_seconds=15, opener=_fake_opener)

    with pytest.raises(RuntimeError, match="Veeam API 请求超时") as exc_info:
        provider.list_machine_backups(
            server_host="veeam.example.com",
            server_port=9419,
            username="DOMAIN\\user",
            password="secret",
            api_version="1.3-rev1",
            match_machine_names={"db01.domain.com"},
        )

    message = str(exc_info.value)
    assert "timeout=15s" in message
    assert "url=https://veeam.example.com:9419/api/v1/backupObjects?limit=2000" in message
    assert captured_urls == [
        "https://veeam.example.com:9419/api/oauth2/token",
        "https://veeam.example.com:9419/api/v1/backupObjects?limit=2000",
    ]
