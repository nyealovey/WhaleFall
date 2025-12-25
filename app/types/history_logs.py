"""历史日志相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.constants.system_constants import LogLevel


@dataclass(slots=True)
class LogSearchFilters:
    """日志搜索过滤条件."""

    page: int
    limit: int
    sort_field: str
    sort_order: str
    level: LogLevel | None
    module: str | None
    search_term: str
    start_time: datetime | None
    end_time: datetime | None
    hours: int | None


@dataclass(slots=True)
class HistoryLogListItem:
    """Grid.js 日志列表单行结构."""

    id: int
    timestamp: str | None
    timestamp_display: str
    level: str | None
    module: str
    message: str
    traceback: str | None
    context: Any
