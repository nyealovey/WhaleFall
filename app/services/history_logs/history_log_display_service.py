"""历史日志展示文本标准化.

职责:
- 为日志中心提供中文展示文本
- 保留原始 level/module/message 供排障和检索
"""

from __future__ import annotations

import re
from typing import TypedDict


class ModuleOption(TypedDict):
    """日志模块筛选选项."""

    value: str
    label: str


LEVEL_LABELS = {
    "DEBUG": "调试",
    "INFO": "信息",
    "WARNING": "告警",
    "ERROR": "错误",
    "CRITICAL": "严重",
}

MODULE_LABELS = {
    "account_classification": "账户分类",
    "account_statistics": "账户统计",
    "accounts": "账户",
    "accounts_sync": "账户同步",
    "aggregation": "聚合统计",
    "aggregation_sync": "聚合同步",
    "app": "应用",
    "auth": "认证",
    "cache": "缓存",
    "capacity": "容量",
    "cluster_status_sync": "群集状态同步",
    "dashboard": "仪表盘",
    "database_sync": "数据库同步",
    "databases": "数据库",
    "error_handler": "错误处理",
    "health": "健康检查",
    "history_logs": "日志中心",
    "http": "HTTP 请求",
    "instances": "实例",
    "log_statistics": "日志统计",
    "partition": "分区",
    "scheduler": "调度任务",
    "scheduler_jobs_read_service": "调度任务读取",
    "settings": "系统设置",
    "sync_session": "同步会话",
    "tags": "标签",
    "users": "用户",
}

MESSAGE_LABELS = {
    "http_request_completed": "HTTP 请求完成",
    "dashboard_base_counts": "仪表盘基础指标统计完成",
    "dashboard_classification_counts": "仪表盘分类统计完成",
    "dashboard_active_counts": "仪表盘活跃指标统计完成",
    "batch_create_instance_failed": "批量创建实例失败",
    "batch_delete_instance_failed": "批量删除实例失败",
    "inventory_sync_completed": "数据库清单同步完成",
    "logging_handler_extract_user_failed": "日志处理器解析用户失败",
    "oracle_adapter_probe_failed": "Oracle 适配器探测失败",
}

ENGLISH_PHRASE_LABELS = {
    "ad sync failed": "AD 同步失败",
    "sql connection timeout": "SQL 连接超时",
}

TOKEN_LABELS = {
    "account": "账户",
    "accounts": "账户",
    "active": "活跃",
    "adapter": "适配器",
    "ad": "AD",
    "api": "API",
    "base": "基础",
    "batch": "批量",
    "cache": "缓存",
    "capacity": "容量",
    "classification": "分类",
    "completed": "完成",
    "connection": "连接",
    "counts": "统计",
    "create": "创建",
    "dashboard": "仪表盘",
    "database": "数据库",
    "delete": "删除",
    "error": "错误",
    "event": "事件",
    "failed": "失败",
    "filtered": "已过滤",
    "handler": "处理",
    "http": "HTTP",
    "instance": "实例",
    "inventory": "清单",
    "log": "日志",
    "logs": "日志",
    "mysql": "MySQL",
    "oracle": "Oracle",
    "postgresql": "PostgreSQL",
    "probe": "探测",
    "request": "请求",
    "scheduler": "调度任务",
    "sql": "SQL",
    "sqlserver": "SQL Server",
    "sync": "同步",
    "timeout": "超时",
    "user": "用户",
    "warning": "告警",
}


def display_history_log_level(level: str | None) -> str:
    """返回日志级别中文展示文本."""
    normalized = str(level or "").strip().upper()
    return LEVEL_LABELS.get(normalized, normalized or "-")


def display_history_log_module(module: str | None) -> str:
    """返回日志模块中文展示文本."""
    normalized = str(module or "").strip()
    if not normalized:
        return "-"
    return MODULE_LABELS.get(normalized.lower(), normalized)


def display_history_log_message(message: str | None) -> str:
    """返回日志消息中文展示文本."""
    text = str(message or "").strip()
    if not text:
        return "-"

    normalized = text.lower()
    if normalized in MESSAGE_LABELS:
        return MESSAGE_LABELS[normalized]
    if normalized in ENGLISH_PHRASE_LABELS:
        return ENGLISH_PHRASE_LABELS[normalized]
    if "the requested url was not found on the server" in normalized:
        return "请求地址不存在"
    translated = _translate_token_message(text)
    if translated:
        return translated
    if _looks_like_english_message(text):
        return "系统日志事件"

    return text


def build_module_options(modules: list[str]) -> list[ModuleOption]:
    """构建日志模块筛选选项."""
    return [{"value": module, "label": display_history_log_module(module)} for module in modules]


def _translate_token_message(text: str) -> str | None:
    tokens = [token for token in re.split(r"[\s_:/.-]+", text.strip()) if token]
    if not tokens:
        return None

    labels: list[str] = []
    for token in tokens:
        label = TOKEN_LABELS.get(token.lower())
        if label is None:
            return None
        labels.append(label)
    return _join_labels(labels)


def _join_labels(labels: list[str]) -> str:
    rendered = ""
    previous = ""
    for label in labels:
        if not rendered:
            rendered = label
        elif _is_latin_label(previous) or _is_latin_label(label):
            rendered = f"{rendered} {label}"
        else:
            rendered = f"{rendered}{label}"
        previous = label
    return rendered


def _is_latin_label(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value))


def _looks_like_english_message(text: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", text):
        return False
    return bool(re.search(r"[A-Za-z]", text))
