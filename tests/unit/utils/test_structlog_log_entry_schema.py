"""结构化日志最小字段 schema 的门禁测试."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.core.constants.system_constants import LogLevel
from app.models.unified_log import LogEntryParams, UnifiedLog
from app.utils.logging.handlers import _build_log_entry


@pytest.mark.unit
def test_build_log_entry_returns_minimum_fields_for_non_dict_event() -> None:
    """非 dict 事件也必须能映射为最小字段集合."""
    payload = _build_log_entry("hello")

    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"timestamp", "level", "module", "message", "traceback", "context"}

    assert isinstance(payload["timestamp"], datetime)
    assert payload["timestamp"].tzinfo is not None
    assert payload["level"] == LogLevel.INFO
    assert payload["module"] == "app"
    assert payload["message"] == "hello"
    assert payload["traceback"] is None
    assert payload["context"] == {}


@pytest.mark.unit
def test_build_log_entry_extracts_module_from_logger_when_missing() -> None:
    """当 module 缺失时应能从 logger 名提取兜底模块名."""
    payload = _build_log_entry({"level": "INFO", "event": "ok", "logger": "app.utils.cache_utils"})

    assert isinstance(payload, dict)
    assert payload["level"] == LogLevel.INFO
    assert payload["module"] == "cache_utils"
    assert payload["message"] == "ok"


@pytest.mark.unit
def test_build_log_entry_filters_system_fields_into_context() -> None:
    """非系统字段应进入 context，且系统字段不会污染 context."""
    payload = _build_log_entry({"level": "INFO", "module": "scheduler", "event": "loaded", "job_count": 3})

    assert isinstance(payload, dict)
    assert payload["module"] == "scheduler"
    assert payload["message"] == "loaded"
    assert payload["context"].get("job_count") == 3
    assert "module" not in payload["context"]
    assert "event" not in payload["context"]


@pytest.mark.unit
def test_build_log_entry_drops_debug_level() -> None:
    """DEBUG 日志默认不落库."""
    assert _build_log_entry({"level": "DEBUG", "module": "any", "event": "debug"}) is None


@pytest.mark.unit
def test_build_log_entry_defaults_invalid_level_to_info() -> None:
    """非法 level 字符串应兜底为 INFO，避免写入失败."""
    payload = _build_log_entry({"level": "NOT_A_LEVEL", "module": "x", "event": "y"})

    assert isinstance(payload, dict)
    assert payload["level"] == LogLevel.INFO


@pytest.mark.unit
def test_unified_log_entry_strips_nul_bytes_before_persisting() -> None:
    """PostgreSQL text/json 字段不接受 NUL，日志入库边界必须清理。"""
    model = UnifiedLog.create_log_entry(
        LogEntryParams(
            level=LogLevel.ERROR,
            module="ad\x00domain",
            message="AD 域连接测试失败\x00",
            traceback="Traceback...\x00",
            context={
                "error_message": "LDAP 返回了 NUL\x00",
                "nested": {"referral": "ldap://corp.example.com\x00/base"},
                "items": ["ok", "bad\x00value"],
            },
        ),
    )

    assert "\x00" not in model.module
    assert "\x00" not in model.message
    assert model.traceback is not None
    assert "\x00" not in model.traceback
    assert model.context["error_message"] == "LDAP 返回了 NUL"
    assert model.context["nested"]["referral"] == "ldap://corp.example.com/base"
    assert model.context["items"] == ["ok", "badvalue"]
