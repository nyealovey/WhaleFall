import pytest

import app.services.partition_management_service as partition_management_service_module
from app.services.partition_management_service import PartitionManagementService


@pytest.mark.unit
def test_partition_management_service_cleanup_old_partitions_from_payload_uses_parse_payload(monkeypatch) -> None:
    service = PartitionManagementService()

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("parse_payload_called")

    monkeypatch.setattr(partition_management_service_module, "parse_payload", _raise, raising=False)

    with pytest.raises(RuntimeError, match="parse_payload_called"):
        service.cleanup_old_partitions_from_payload({"retention_months": 12})


@pytest.mark.unit
def test_partition_management_service_cleanup_old_partitions_from_payload_uses_validate_or_raise(monkeypatch) -> None:
    service = PartitionManagementService()

    def _passthrough(payload: object, **_kwargs: object) -> object:
        return payload

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("validate_or_raise_called")

    monkeypatch.setattr(partition_management_service_module, "parse_payload", _passthrough, raising=False)
    monkeypatch.setattr(partition_management_service_module, "validate_or_raise", _raise, raising=False)

    with pytest.raises(RuntimeError, match="validate_or_raise_called"):
        service.cleanup_old_partitions_from_payload({"retention_months": 12})

