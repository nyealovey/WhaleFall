from __future__ import annotations

import pytest

import app.services.connections.instance_connections_write_service as instance_connections_write_service_module
from app.core.exceptions import ValidationError
from app.services.connections.instance_connections_write_service import InstanceConnectionsWriteService


@pytest.mark.unit
def test_instance_connections_write_service_parse_connection_test_payload_uses_parse_payload(monkeypatch) -> None:
    service = InstanceConnectionsWriteService()

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("parse_payload_called")

    monkeypatch.setattr(instance_connections_write_service_module, "parse_payload", _raise, raising=False)

    with pytest.raises(RuntimeError, match="parse_payload_called"):
        service.parse_connection_test_payload({"instance_id": 1})


@pytest.mark.unit
def test_instance_connections_write_service_parse_connection_test_payload_uses_validate_or_raise(monkeypatch) -> None:
    service = InstanceConnectionsWriteService()

    def _passthrough(payload: object, **_kwargs: object) -> object:
        return payload

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("validate_or_raise_called")

    monkeypatch.setattr(instance_connections_write_service_module, "parse_payload", _passthrough, raising=False)
    monkeypatch.setattr(instance_connections_write_service_module, "validate_or_raise", _raise, raising=False)

    with pytest.raises(RuntimeError, match="validate_or_raise_called"):
        service.parse_connection_test_payload({"instance_id": 1})


@pytest.mark.unit
def test_instance_connections_write_service_parse_connection_test_payload_rejects_empty_payload() -> None:
    service = InstanceConnectionsWriteService()

    with pytest.raises(ValidationError, match="请求数据不能为空"):
        service.parse_connection_test_payload({})


@pytest.mark.unit
def test_instance_connections_write_service_parse_batch_test_payload_rejects_too_many_instance_ids() -> None:
    service = InstanceConnectionsWriteService()

    with pytest.raises(ValidationError, match="批量测试数量不能超过50个"):
        service.parse_batch_test_payload({"instance_ids": list(range(1, 52))})
