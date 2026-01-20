"""SQLAlchemy model keyword-argument typing helpers.

These `TypedDict` definitions exist to make Pyright understand our common
`Model(field=value, ...)` patterns used in services and tests.

Important: keep these payload-only types free of ORM imports to avoid cycles.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TypedDict

from app.core.types.structures import NumericLike


class AccountPermissionOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating AccountPermission ORM rows."""

    id: int
    instance_id: int
    db_type: str
    instance_account_id: int
    username: str
    type_specific: object | None
    permission_snapshot: object | None
    permission_facts: object | None
    last_sync_time: datetime
    last_change_type: str
    last_change_time: datetime


class InstanceAccountOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating InstanceAccount ORM rows."""

    id: int
    instance_id: int
    username: str
    db_type: str
    is_active: bool
    first_seen_at: datetime
    last_seen_at: datetime
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InstanceDatabaseOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating InstanceDatabase ORM rows."""

    id: int
    instance_id: int
    database_name: str
    is_active: bool
    first_seen_date: date
    last_seen_date: date
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PermissionConfigOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating PermissionConfig ORM rows."""

    id: int
    db_type: str
    category: str
    permission_name: str
    description: str | None
    is_active: bool
    sort_order: int
    introduced_in_major: str | None
    created_at: datetime
    updated_at: datetime


class AccountChangeLogOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating AccountChangeLog ORM rows."""

    id: int
    instance_id: int
    db_type: str
    username: str
    change_type: str
    change_time: datetime
    session_id: str | None
    status: str
    message: str | None
    privilege_diff: object | None
    other_diff: object | None


class AccountClassificationOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating AccountClassification ORM rows."""

    id: int
    code: str
    display_name: str
    description: str | None
    risk_level: int
    icon_name: str | None
    priority: int
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClassificationRuleOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating ClassificationRule ORM rows."""

    id: int
    classification_id: int
    db_type: str
    rule_name: str
    rule_expression: str
    rule_group_id: str
    rule_version: int
    superseded_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountClassificationAssignmentOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating AccountClassificationAssignment ORM rows."""

    id: int
    account_id: int
    classification_id: int
    rule_id: int | None
    assigned_by: int | None
    assignment_type: str
    confidence_score: float | None
    notes: str | None
    batch_id: str | None
    is_active: bool
    assigned_at: datetime
    created_at: datetime
    updated_at: datetime


class AccountClassificationDailyRuleMatchStatOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating AccountClassificationDailyRuleMatchStat ORM rows."""

    id: int
    stat_date: date
    rule_id: int
    classification_id: int
    db_type: str
    instance_id: int
    matched_accounts_count: int
    computed_at: datetime
    created_at: datetime
    updated_at: datetime


class AccountClassificationDailyClassificationMatchStatOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating AccountClassificationDailyClassificationMatchStat ORM rows."""

    id: int
    stat_date: date
    classification_id: int
    db_type: str
    instance_id: int
    matched_accounts_distinct_count: int
    computed_at: datetime
    created_at: datetime
    updated_at: datetime


class DatabaseSizeAggregationOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating DatabaseSizeAggregation ORM rows."""

    id: int
    instance_id: int
    database_name: str
    period_type: str
    period_start: date
    period_end: date
    avg_size_mb: int
    max_size_mb: int
    min_size_mb: int
    data_count: int
    avg_data_size_mb: int | None
    max_data_size_mb: int | None
    min_data_size_mb: int | None
    avg_log_size_mb: int | None
    max_log_size_mb: int | None
    min_log_size_mb: int | None
    size_change_mb: int
    size_change_percent: NumericLike
    data_size_change_mb: int | None
    data_size_change_percent: NumericLike | None
    log_size_change_mb: int | None
    log_size_change_percent: NumericLike | None
    growth_rate: NumericLike
    calculated_at: datetime
    created_at: datetime


class InstanceSizeAggregationOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating InstanceSizeAggregation ORM rows."""

    id: int
    instance_id: int
    period_type: str
    period_start: date
    period_end: date
    total_size_mb: int
    avg_size_mb: int
    max_size_mb: int
    min_size_mb: int
    data_count: int
    database_count: int
    avg_database_count: NumericLike | None
    max_database_count: int | None
    min_database_count: int | None
    total_size_change_mb: int | None
    total_size_change_percent: NumericLike | None
    database_count_change: int | None
    database_count_change_percent: NumericLike | None
    growth_rate: NumericLike | None
    trend_direction: str | None
    calculated_at: datetime
    created_at: datetime


class InstanceSizeStatOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating InstanceSizeStat ORM rows."""

    id: int
    instance_id: int
    total_size_mb: int
    database_count: int
    collected_date: date
    collected_at: datetime
    is_deleted: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DatabaseSizeStatOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating DatabaseSizeStat ORM rows."""

    id: int
    instance_id: int
    database_name: str
    size_mb: int
    data_size_mb: int | None
    log_size_mb: int | None
    collected_date: date
    collected_at: datetime
    created_at: datetime
    updated_at: datetime


class DatabaseTableSizeStatOrmFields(TypedDict, total=False):
    """Keyword arguments for creating/updating DatabaseTableSizeStat ORM rows."""

    id: int
    instance_id: int
    database_name: str
    schema_name: str
    table_name: str
    size_mb: int
    data_size_mb: int | None
    index_size_mb: int | None
    row_count: int | None
    collected_at: datetime
    created_at: datetime
    updated_at: datetime
