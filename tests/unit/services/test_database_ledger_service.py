import datetime
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CACHE_REDIS_URL", "redis://localhost:6379/0")

from app.constants import SyncStatus
from app.services.ledgers.database_ledger_service import DatabaseLedgerService


@pytest.mark.unit
def test_format_size_handles_megabytes() -> None:
    service = DatabaseLedgerService()
    assert service._format_size(None) == "未采集"
    assert service._format_size(512) == "512 MB"
    assert service._format_size(2048) == "2.00 GB"


@pytest.mark.unit
def test_resolve_sync_status_recent(monkeypatch) -> None:
    service = DatabaseLedgerService()
    now = datetime.datetime(2025, 11, 27, 12, 0, tzinfo=datetime.UTC)
    monkeypatch.setattr("app.services.ledgers.database_ledger_service.time_utils.now", lambda: now)
    status = service._resolve_sync_status(now - datetime.timedelta(hours=2))
    assert status["value"] == SyncStatus.COMPLETED


@pytest.mark.unit
def test_resolve_sync_status_timeout(monkeypatch) -> None:
    service = DatabaseLedgerService()
    now = datetime.datetime(2025, 11, 27, 12, 0, tzinfo=datetime.UTC)
    monkeypatch.setattr("app.services.ledgers.database_ledger_service.time_utils.now", lambda: now)
    status = service._resolve_sync_status(now - datetime.timedelta(days=3))
    assert status["value"] == SyncStatus.FAILED
