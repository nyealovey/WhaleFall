import pytest

from app.services.history_logs.history_log_display_service import (
    build_module_options,
    display_history_log_message,
    display_history_log_module,
    display_history_log_level,
)


@pytest.mark.unit
def test_history_log_display_labels_known_values() -> None:
    assert display_history_log_level("INFO") == "信息"
    assert display_history_log_level("WARNING") == "告警"
    assert display_history_log_level("ERROR") == "错误"
    assert display_history_log_module("http") == "HTTP 请求"
    assert display_history_log_module("error_handler") == "错误处理"
    assert display_history_log_module("dashboard") == "仪表盘"
    assert display_history_log_message("http_request_completed") == "HTTP 请求完成"
    assert display_history_log_message("dashboard_active_counts") == "仪表盘活跃指标统计完成"


@pytest.mark.unit
def test_history_log_display_translates_common_flask_404_message() -> None:
    raw = "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."

    assert display_history_log_message(raw) == "请求地址不存在"


@pytest.mark.unit
def test_history_log_display_keeps_acronyms_and_safe_unknown_text() -> None:
    assert display_history_log_message("AD sync failed") == "AD 同步失败"
    assert display_history_log_message("SQL connection timeout") == "SQL 连接超时"
    assert display_history_log_message("oracle_adapter_probe_failed") == "Oracle 适配器探测失败"
    assert display_history_log_message("account_inventory_sync_completed") == "账户清单同步完成"
    assert display_history_log_message("database connection failed") == "数据库连接失败"
    assert display_history_log_message("some_unknown_event") == "系统日志事件"


@pytest.mark.unit
def test_history_log_display_builds_module_options() -> None:
    assert build_module_options(["http", "dashboard"]) == [
        {"value": "http", "label": "HTTP 请求"},
        {"value": "dashboard", "label": "仪表盘"},
    ]
