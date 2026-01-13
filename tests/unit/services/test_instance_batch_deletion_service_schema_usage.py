import pytest

import app.services.instances.batch_service as batch_service_module
from app.services.instances.batch_service import InstanceBatchDeletionService


@pytest.mark.unit
def test_instance_batch_deletion_service_uses_parse_payload(monkeypatch) -> None:
    service = InstanceBatchDeletionService()

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("parse_payload_called")

    monkeypatch.setattr(batch_service_module, "parse_payload", _raise, raising=False)

    with pytest.raises(RuntimeError, match="parse_payload_called"):
        service.delete_instances_from_payload({"instance_ids": [1]})


@pytest.mark.unit
def test_instance_batch_deletion_service_uses_validate_or_raise(monkeypatch) -> None:
    service = InstanceBatchDeletionService()

    def _passthrough(payload: object, **_kwargs: object) -> object:
        return payload

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("validate_or_raise_called")

    monkeypatch.setattr(batch_service_module, "parse_payload", _passthrough, raising=False)
    monkeypatch.setattr(batch_service_module, "validate_or_raise", _raise, raising=False)

    with pytest.raises(RuntimeError, match="validate_or_raise_called"):
        service.delete_instances_from_payload({"instance_ids": [1]})

