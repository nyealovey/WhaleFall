"""账户统计相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AccountStatisticsResult:
    total_accounts: int
    active_accounts: int
    locked_accounts: int
    normal_accounts: int
    deleted_accounts: int

    database_instances: int
    total_instances: int
    active_instances: int
    disabled_instances: int
    normal_instances: int
    deleted_instances: int

    db_type_stats: dict[str, dict[str, int]]
    classification_stats: dict[str, dict[str, Any]]
