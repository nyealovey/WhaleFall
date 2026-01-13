from __future__ import annotations

from datetime import datetime, timezone

import pytest

import app.services.partition_management_service as partition_management_service_module
from app.core.exceptions import ValidationError
from app.services.partition_management_service import PartitionManagementService


@pytest.mark.unit
def test_partition_management_service_create_partition_from_payload_uses_parse_payload(monkeypatch) -> None:
    service = PartitionManagementService()

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("parse_payload_called")

    monkeypatch.setattr(partition_management_service_module, "parse_payload", _raise, raising=False)

    with pytest.raises(RuntimeError, match="parse_payload_called"):
        service.create_partition_from_payload({"date": "2026-01-01"})


@pytest.mark.unit
def test_partition_management_service_create_partition_from_payload_uses_validate_or_raise(monkeypatch) -> None:
    service = PartitionManagementService()

    def _passthrough(payload: object, **_kwargs: object) -> object:
        return payload

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("validate_or_raise_called")

    monkeypatch.setattr(partition_management_service_module, "parse_payload", _passthrough, raising=False)
    monkeypatch.setattr(partition_management_service_module, "validate_or_raise", _raise, raising=False)

    with pytest.raises(RuntimeError, match="validate_or_raise_called"):
        service.create_partition_from_payload({"date": "2026-01-01"})


@pytest.mark.unit
def test_partition_management_service_create_partition_from_payload_rejects_past_month(monkeypatch) -> None:
    service = PartitionManagementService()

    monkeypatch.setattr(
        partition_management_service_module.time_utils,
        "now_china",
        lambda: datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
        raising=False,
    )

    with pytest.raises(ValidationError, match="只能创建当前或未来月份的分区"):
        service.create_partition_from_payload({"date": "2025-12-01"})

