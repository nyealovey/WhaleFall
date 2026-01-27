from __future__ import annotations

from contextlib import contextmanager
from typing import Any, cast

import pytest
from sqlalchemy.exc import SQLAlchemyError

import app.services.tags.tag_write_service as tag_write_service_module
from app.services.tags.tag_write_service import TagWriteService


@pytest.mark.unit
def test_tag_write_service_batch_delete_logs_when_delete_fails(monkeypatch) -> None:
    service = TagWriteService()

    class _DummyTag:
        def __init__(self, tag_id: int) -> None:
            self.id = tag_id
            self.instances: list[object] = []
            self.name = f"t{tag_id}"
            self.display_name = f"t{tag_id}"
            self.category = "default"
            self.color = "#000000"
            self.is_active = True

    class _DummyRepo:
        def get_by_id(self, _tag_id: int):
            return _DummyTag(_tag_id)

        def delete(self, _tag: object) -> None:
            raise SQLAlchemyError("boom")

    @contextmanager
    def _dummy_begin_nested():
        yield

    log_calls: list[tuple[str, str, dict[str, object]]] = []

    def _fake_log_with_context(level: str, message: str, **kwargs: object) -> None:
        log_calls.append((level, message, dict(kwargs)))

    monkeypatch.setattr(tag_write_service_module.db.session, "begin_nested", lambda: _dummy_begin_nested())
    monkeypatch.setattr(tag_write_service_module, "log_with_context", _fake_log_with_context)
    cast(Any, service)._repository = _DummyRepo()

    outcome = service.batch_delete([1], operator_id=123)

    assert outcome.has_failure is True
    assert outcome.results == [{"tag_id": 1, "status": "error", "message": "boom"}]

    assert log_calls
    level, message, kwargs = log_calls[0]
    assert level == "warning"
    assert message == "批量删除标签失败"
    assert kwargs["module"] == "tags"
    assert kwargs["action"] == "batch_delete_tags"
    assert kwargs["include_actor"] is True
    assert kwargs["context"] == {"tag_id": 1}
    assert kwargs["extra"] == {"error_message": "boom"}

