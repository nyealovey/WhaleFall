from __future__ import annotations

import json
from typing import Any

import pytest
from flask import Flask

from app.services.veeam.provider import HttpVeeamProvider


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
def test_http_veeam_provider_fetch_restore_point_records_skips_timeout_and_preserves_progress() -> None:
    captured_urls: list[str] = []
    payloads = [
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
        }
    ]

    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (timeout, context)
        captured_urls.append(request.full_url)
        if request.full_url.endswith("/backup-object-2/restorePoints"):
            raise TimeoutError("The read operation timed out")
        return _FakeResponse(payloads[len(captured_urls) - 1])

    provider = HttpVeeamProvider(opener=_fake_opener)
    session = type(
        "ProviderSession",
        (),
        {
            "base_url": "https://veeam.example.com:9419",
            "access_token": "token-1",
            "api_version": "1.3-rev1",
            "verify_ssl": True,
        },
    )()
    match_result = type(
        "MatchResult",
        (),
        {
            "matched_backup_objects": [
                type(
                    "MatchedBackupObject",
                    (),
                    {
                        "backup_object_id": "backup-object-1",
                        "machine_name": "db01.domain.com",
                        "backup_item": {"id": "backup-object-1", "name": "db01.domain.com"},
                    },
                )(),
                type(
                    "MatchedBackupObject",
                    (),
                    {
                        "backup_object_id": "backup-object-2",
                        "machine_name": "db02.domain.com",
                        "backup_item": {"id": "backup-object-2", "name": "db02.domain.com"},
                    },
                )(),
            ],
            "backups_received_total": 2,
            "backups_matched_total": 2,
            "backups_unmatched_total": 0,
            "backups_missing_machine_name": 0,
            "matched_backup_ids_sample": ["backup-object-1", "backup-object-2"],
            "unmatched_backup_ids_sample": [],
            "unmatched_machine_names_sample": [],
            "missing_machine_name_backup_ids_sample": [],
            "missing_machine_name_backup_names_sample": [],
        },
    )()

    result = provider.fetch_restore_point_records(session=session, match_result=match_result)

    assert result.received_total == 1
    assert len(result.records) == 1
    assert result.restore_points_backup_objects_total == 2
    assert result.restore_points_backup_objects_completed == 1
    assert result.timed_out_backup_objects_total == 1
    assert result.timed_out_backup_ids_sample == ["backup-object-2"]
    assert result.timed_out_machine_names_sample == ["db02.domain.com"]
    assert captured_urls == [
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-1/restorePoints",
        "https://veeam.example.com:9419/api/v1/backupObjects/backup-object-2/restorePoints",
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
