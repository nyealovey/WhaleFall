"""请求级别日志注入 + wide event 的单元测试门禁."""

from __future__ import annotations

from typing import Any, cast

import pytest

from app import create_app
from app.settings import Settings
from app.utils.logging.context_vars import request_id_var, user_id_var
from app.utils.structlog_config import get_logger, structlog_config


class _FakeWorker:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def enqueue(self, log_entry: dict) -> None:  # pragma: no cover - 类型占位
        self.entries.append(log_entry)


@pytest.mark.unit
def test_request_id_is_propagated_and_injected_into_unified_log_context(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    monkeypatch.setenv("PASSWORD_ENCRYPTION_KEY", "")
    # 门禁：该测试关注“成功请求也有 wide event”，因此显式开启 all 模式。
    monkeypatch.setenv("LOG_HTTP_REQUEST_COMPLETED_MODE", "all")

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True

    fake_worker = _FakeWorker()
    structlog_config.handler.set_worker(cast(Any, fake_worker))

    @app.get("/_test/logging")
    def _test_logging():  # type: ignore[no-untyped-def]
        logger = get_logger("test")
        logger.info("test_log", module="test_module", action="test_action", foo=1)
        return {"ok": True}

    client = app.test_client()

    response = client.get("/_test/logging", headers={"X-Request-ID": "req_test_123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req_test_123"

    # teardown_request 应 reset contextvars（避免泄漏到后续请求/测试）
    assert request_id_var.get() is None
    assert user_id_var.get() is None

    messages = [entry.get("message") for entry in fake_worker.entries]
    assert "test_log" in messages
    assert "http_request_completed" in messages

    test_entry = next(entry for entry in fake_worker.entries if entry.get("message") == "test_log")
    assert isinstance(test_entry.get("context"), dict)
    assert test_entry["context"].get("request_id") == "req_test_123"
    assert test_entry["context"].get("method") == "GET"
    assert test_entry["context"].get("url") == "/_test/logging"

    wide_entry = next(entry for entry in fake_worker.entries if entry.get("message") == "http_request_completed")
    assert wide_entry.get("module") == "http"
    assert wide_entry["context"].get("request_id") == "req_test_123"
    assert wide_entry["context"].get("status_code") == 200
    assert isinstance(wide_entry["context"].get("duration_ms"), int)
    assert isinstance(wide_entry["context"].get("build_hash"), str)
    assert isinstance(wide_entry["context"].get("region"), str)
    assert isinstance(wide_entry["context"].get("runtime_instance_id"), str)


@pytest.mark.unit
def test_http_request_completed_is_emitted_for_errors_by_default(monkeypatch) -> None:
    """默认策略应避免被请求日志淹没，但错误请求仍应有 wide event."""
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    monkeypatch.setenv("PASSWORD_ENCRYPTION_KEY", "")

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True

    fake_worker = _FakeWorker()
    structlog_config.handler.set_worker(cast(Any, fake_worker))

    client = app.test_client()
    response = client.get("/_not_found", headers={"X-Request-ID": "req_error_404"})
    assert response.status_code == 404

    messages = [entry.get("message") for entry in fake_worker.entries]
    assert "http_request_completed" in messages

    wide_entry = next(entry for entry in fake_worker.entries if entry.get("message") == "http_request_completed")
    assert wide_entry.get("module") == "http"
    assert wide_entry["context"].get("request_id") == "req_error_404"
    assert wide_entry["context"].get("status_code") == 404


@pytest.mark.unit
def test_error_envelope_contains_request_id(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)
    monkeypatch.setenv("PASSWORD_ENCRYPTION_KEY", "")

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True

    client = app.test_client()
    response = client.get("/_not_found", headers={"X-Request-ID": "req_404"})

    assert response.status_code == 404
    assert response.headers.get("X-Request-ID") == "req_404"

    payload = response.get_json()
    assert isinstance(payload, dict)
    context = payload.get("context")
    assert isinstance(context, dict)
    assert context.get("request_id") == "req_404"
