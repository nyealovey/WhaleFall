from __future__ import annotations

import json
from typing import Any

import pytest

from app.services.jumpserver.provider import HttpJumpServerProvider


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
def test_http_jumpserver_provider_requests_assets_with_signature_headers_and_paginates() -> None:
    captured_requests: list[dict[str, Any]] = []
    payloads = [
        {
            "count": 3,
            "next": "https://demo.jumpserver.org/api/v1/assets/assets/?limit=2&offset=2",
            "results": [
                {
                    "id": "asset-mysql",
                    "name": "mysql-prod-1",
                    "address": "10.0.0.10",
                    "port": 3306,
                    "platform": {"name": "MySQL"},
                },
                {
                    "id": "asset-redis",
                    "name": "redis-cache-1",
                    "address": "10.0.0.20",
                    "port": 6379,
                    "platform": {"name": "Redis"},
                },
            ],
        },
        {
            "count": 3,
            "next": None,
            "results": [
                {
                    "id": "asset-pg",
                    "name": "pg-prod-1",
                    "ip": "10.0.0.30",
                    "protocol_port": 5432,
                    "platform": {"name": "PostgreSQL"},
                }
            ],
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

    provider = HttpJumpServerProvider(
        org_id="00000000-0000-0000-0000-000000000002",
        timeout_seconds=12,
        verify_ssl=True,
        opener=_fake_opener,
    )

    result = provider.list_database_assets(
        base_url="https://demo.jumpserver.org",
        access_key_id="ak-id",
        access_key_secret="ak-secret",
    )

    assert result.received_total == 3
    assert result.supported_total == 2
    assert result.skipped_unsupported == 1
    assert result.skipped_invalid == 0
    assert [asset.external_id for asset in result.assets] == ["asset-mysql", "asset-pg"]
    assert result.assets[0].db_type == "mysql"
    assert result.assets[1].db_type == "postgresql"

    assert len(captured_requests) == 2
    assert captured_requests[0]["method"] == "GET"
    assert captured_requests[0]["url"] == "https://demo.jumpserver.org/api/v1/assets/assets/?limit=200&offset=0"
    assert captured_requests[0]["headers"]["accept"] == "application/json"
    assert captured_requests[0]["headers"]["x-jms-org"] == "00000000-0000-0000-0000-000000000002"
    assert "authorization" in captured_requests[0]["headers"]
    assert 'Signature keyId="ak-id"' in captured_requests[0]["headers"]["authorization"]
    assert 'headers="(request-target) accept date"' in captured_requests[0]["headers"]["authorization"]
    assert captured_requests[0]["timeout"] == 12
    assert captured_requests[0]["context"] is not None
    assert captured_requests[1]["url"] == "https://demo.jumpserver.org/api/v1/assets/assets/?limit=2&offset=2"


@pytest.mark.unit
def test_http_jumpserver_provider_skips_assets_missing_required_fields() -> None:
    def _fake_opener(request, *, timeout: int, context) -> _FakeResponse:
        _ = (request, timeout, context)
        return _FakeResponse(
            [
                {
                    "id": "asset-mysql",
                    "name": "mysql-prod-1",
                    "address": "10.0.0.10",
                    "port": 3306,
                    "platform": {"name": "MySQL"},
                },
                {
                    "id": "asset-no-host",
                    "name": "mysql-prod-2",
                    "port": 3306,
                    "platform": {"name": "MySQL"},
                },
                {
                    "id": "asset-no-name",
                    "address": "10.0.0.11",
                    "port": 3306,
                    "platform": {"name": "MySQL"},
                },
            ]
        )

    provider = HttpJumpServerProvider(opener=_fake_opener)

    result = provider.list_database_assets(
        base_url="https://demo.jumpserver.org",
        access_key_id="ak-id",
        access_key_secret="ak-secret",
    )

    assert [asset.external_id for asset in result.assets] == ["asset-mysql"]
    assert result.received_total == 3
    assert result.supported_total == 1
    assert result.skipped_invalid == 2
