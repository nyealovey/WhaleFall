"""账户变更历史（全量）相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AccountChangeLogsListFilters:
    """账户变更日志列表查询参数."""

    page: int
    limit: int
    sort_field: str
    sort_order: str
    search_term: str
    instance_id: int | None
    db_type: str | None
    change_type: str | None
    status: str | None
    hours: int | None


@dataclass(slots=True)
class AccountChangeLogListItem:
    """账户变更日志列表条目."""

    id: int
    account_id: int | None
    instance_id: int
    instance_name: str | None
    db_type: str
    username: str
    change_type: str
    status: str
    message: str | None
    change_time: str
    session_id: str | None
    privilege_diff_count: int
    other_diff_count: int


@dataclass(slots=True)
class AccountChangeLogStatistics:
    """账户变更日志统计汇总."""

    total_changes: int
    success_count: int
    failed_count: int
    affected_accounts: int
