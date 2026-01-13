import pytest

import app.services.tags.tag_write_service as tag_write_service_module
from app.services.tags.tag_write_service import TagWriteService


@pytest.mark.unit
def test_tag_write_service_batch_delete_from_payload_uses_parse_payload(monkeypatch) -> None:
    service = TagWriteService()

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("parse_payload_called")

    monkeypatch.setattr(tag_write_service_module, "parse_payload", _raise, raising=False)

    with pytest.raises(RuntimeError, match="parse_payload_called"):
        service.batch_delete_from_payload({"tag_ids": [1]})


@pytest.mark.unit
def test_tag_write_service_batch_delete_from_payload_uses_validate_or_raise(monkeypatch) -> None:
    service = TagWriteService()

    def _passthrough(payload: object, **_kwargs: object) -> object:
        return payload

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("validate_or_raise_called")

    monkeypatch.setattr(tag_write_service_module, "parse_payload", _passthrough, raising=False)
    monkeypatch.setattr(tag_write_service_module, "validate_or_raise", _raise, raising=False)

    with pytest.raises(RuntimeError, match="validate_or_raise_called"):
        service.batch_delete_from_payload({"tag_ids": [1]})

