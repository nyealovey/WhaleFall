"""各内置任务的 TaskRun.summary_json 构建器.

约定:
- 所有 builder 返回 `TaskRunSummaryFactory.base(...)` 生成的 v1 envelope(dict)
- 任务的聚合字段放到 ext.data，通用展示字段放到 common.metrics/common.scope
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.schemas.task_run_summary import TaskRunSummaryFactory

_CHINA_TZ = "Asia/Shanghai"


def _flags(*, skipped: bool, skip_reason: str | None) -> dict[str, Any]:
    return {"skipped": skipped, "skip_reason": skip_reason}


def _metric(
    *,
    key: str,
    label: str,
    value: int | float | str | bool | None,
    unit: str | None = None,
    tone: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"key": key, "label": label, "value": value}
    if unit is not None:
        payload["unit"] = unit
    if tone is not None:
        payload["tone"] = tone
    return payload


def build_sync_accounts_summary(
    *,
    task_key: str,
    inputs: dict[str, Any] | None,
    instances_total: int,
    instances_successful: int,
    instances_failed: int,
    accounts_synced: int,
    accounts_created: int,
    accounts_updated: int,
    accounts_deactivated: int,
    session_id: str | None,
    skipped: bool = False,
    skip_reason: str | None = None,
) -> dict[str, Any]:
    """构建 sync_accounts 的最终 summary_json(v1)."""
    metrics = [
        _metric(key="instances_total", label="实例总数", value=instances_total, unit="个", tone="info"),
        _metric(key="instances_successful", label="成功实例", value=instances_successful, unit="个", tone="success"),
        _metric(key="instances_failed", label="失败实例", value=instances_failed, unit="个", tone="danger"),
        _metric(key="accounts_synced", label="同步账户", value=accounts_synced, unit="个", tone="info"),
        _metric(key="accounts_created", label="新增账户", value=accounts_created, unit="个", tone="info"),
        _metric(key="accounts_updated", label="更新账户", value=accounts_updated, unit="个", tone="info"),
        _metric(key="accounts_deactivated", label="停用账户", value=accounts_deactivated, unit="个", tone="info"),
    ]
    ext_data = {
        "instances": {"total": instances_total, "successful": instances_successful, "failed": instances_failed},
        "accounts": {
            "synced": accounts_synced,
            "created": accounts_created,
            "updated": accounts_updated,
            "deactivated": accounts_deactivated,
        },
        "session_id": session_id,
    }
    return TaskRunSummaryFactory.base(
        task_key=task_key,
        inputs=inputs or {},
        metrics=metrics,
        flags=_flags(skipped=skipped, skip_reason=skip_reason),
        ext_data=ext_data,
    )


def build_sync_databases_summary(
    *,
    task_key: str,
    inputs: dict[str, Any] | None,
    instances_total: int,
    instances_successful: int,
    instances_failed: int,
    total_size_mb: int | float,
    session_id: str | None,
    skipped: bool = False,
    skip_reason: str | None = None,
) -> dict[str, Any]:
    """构建 sync_databases 的最终 summary_json(v1)."""
    metrics = [
        _metric(key="instances_total", label="实例总数", value=instances_total, unit="个", tone="info"),
        _metric(key="instances_successful", label="成功实例", value=instances_successful, unit="个", tone="success"),
        _metric(key="instances_failed", label="失败实例", value=instances_failed, unit="个", tone="danger"),
        _metric(key="total_size_mb", label="总容量", value=total_size_mb, unit="MB", tone="info"),
    ]
    ext_data = {
        "instances": {"total": instances_total, "successful": instances_successful, "failed": instances_failed},
        "total_size_mb": total_size_mb,
        "session_id": session_id,
    }
    return TaskRunSummaryFactory.base(
        task_key=task_key,
        inputs=inputs or {},
        metrics=metrics,
        flags=_flags(skipped=skipped, skip_reason=skip_reason),
        ext_data=ext_data,
    )


def build_calculate_database_aggregations_summary(
    *,
    task_key: str,
    inputs: dict[str, Any] | None,
    periods_executed: list[str] | None,
    instances_total: int,
    instances_successful: int,
    instances_failed: int,
    record_instance: int,
    record_database: int,
    session_id: str | None,
    skipped: bool = False,
    skip_reason: str | None = None,
) -> dict[str, Any]:
    """构建 calculate_database_aggregations 的最终 summary_json(v1)."""
    record_total = record_instance + record_database
    metrics = [
        _metric(key="instances_total", label="实例总数", value=instances_total, unit="个", tone="info"),
        _metric(key="instances_successful", label="成功实例", value=instances_successful, unit="个", tone="success"),
        _metric(key="instances_failed", label="失败实例", value=instances_failed, unit="个", tone="danger"),
        _metric(key="records_total", label="聚合记录总数", value=record_total, unit="条", tone="info"),
    ]
    ext_data = {
        "periods_executed": list(periods_executed or []),
        "instances": {"total": instances_total, "successful": instances_successful, "failed": instances_failed},
        "records": {"instance": record_instance, "database": record_database, "total": record_total},
        "session_id": session_id,
    }
    return TaskRunSummaryFactory.base(
        task_key=task_key,
        inputs=inputs or {},
        metrics=metrics,
        flags=_flags(skipped=skipped, skip_reason=skip_reason),
        ext_data=ext_data,
    )


def build_calculate_account_classification_summary(
    *,
    task_key: str,
    inputs: dict[str, Any] | None,
    stat_date: date,
    computed_at: datetime | None,
    rules_count: int,
    accounts_count: int,
    rule_match_rows: int,
    classification_match_rows: int,
    skipped: bool = False,
    skip_reason: str | None = None,
) -> dict[str, Any]:
    """构建 calculate_account_classification 的最终 summary_json(v1)."""
    scope = {"time": {"type": "date", "timezone": _CHINA_TZ, "date": stat_date}, "target": {}}
    metrics = [
        _metric(key="rules_count", label="规则数", value=rules_count, unit="条", tone="info"),
        _metric(key="accounts_count", label="账户数", value=accounts_count, unit="个", tone="info"),
        _metric(key="rule_match_rows", label="规则匹配行数", value=rule_match_rows, unit="行", tone="info"),
        _metric(key="classification_match_rows", label="分类匹配行数", value=classification_match_rows, unit="行", tone="info"),
    ]
    ext_data = {
        "stat_date": stat_date,
        "computed_at": computed_at,
        "rules_count": rules_count,
        "accounts_count": accounts_count,
        "rule_match_rows": rule_match_rows,
        "classification_match_rows": classification_match_rows,
    }
    return TaskRunSummaryFactory.base(
        task_key=task_key,
        inputs=inputs or {},
        scope=scope,
        metrics=metrics,
        flags=_flags(skipped=skipped, skip_reason=skip_reason),
        ext_data=ext_data,
    )


def build_auto_classify_accounts_summary(
    *,
    task_key: str,
    inputs: dict[str, Any] | None,
    rules_count: int,
    accounts_count: int,
    total_matches: int,
    total_classifications_added: int,
    failed_count: int,
    duration_ms: int,
    skipped: bool = False,
    skip_reason: str | None = None,
) -> dict[str, Any]:
    """构建 auto_classify_accounts 的最终 summary_json(v1)."""
    metrics = [
        _metric(key="rules_count", label="规则数", value=rules_count, unit="条", tone="info"),
        _metric(key="accounts_count", label="账户数", value=accounts_count, unit="个", tone="info"),
        _metric(key="total_matches", label="命中数", value=total_matches, unit="个", tone="info"),
        _metric(key="total_classifications_added", label="新增分类数", value=total_classifications_added, unit="个", tone="info"),
        _metric(key="failed_count", label="失败数", value=failed_count, unit="个", tone="danger" if failed_count else "success"),
        _metric(key="duration_ms", label="耗时", value=duration_ms, unit="ms", tone="info"),
    ]
    ext_data = {
        "rules_count": rules_count,
        "accounts_count": accounts_count,
        "total_matches": total_matches,
        "total_classifications_added": total_classifications_added,
        "failed_count": failed_count,
        "duration_ms": duration_ms,
    }
    return TaskRunSummaryFactory.base(
        task_key=task_key,
        inputs=inputs or {},
        metrics=metrics,
        flags=_flags(skipped=skipped, skip_reason=skip_reason),
        ext_data=ext_data,
    )


def build_capacity_aggregate_current_summary(
    *,
    task_key: str,
    inputs: dict[str, Any] | None,
    scope: str,
    requested_period_type: str,
    effective_period_type: str,
    period_start: date,
    period_end: date,
    status: str | None,
    message: str | None,
    skipped: bool = False,
    skip_reason: str | None = None,
) -> dict[str, Any]:
    """构建 capacity_aggregate_current 的最终 summary_json(v1)."""
    metrics = [
        _metric(key="scope", label="范围", value=scope, tone="info"),
        _metric(key="requested_period_type", label="请求周期", value=requested_period_type, tone="info"),
        _metric(key="effective_period_type", label="生效周期", value=effective_period_type, tone="info"),
    ]
    ext_data = {
        "scope": scope,
        "requested_period_type": requested_period_type,
        "effective_period_type": effective_period_type,
        "period_start": period_start,
        "period_end": period_end,
        "status": status,
        "message": message,
    }
    return TaskRunSummaryFactory.base(
        task_key=task_key,
        inputs=inputs or {},
        metrics=metrics,
        flags=_flags(skipped=skipped, skip_reason=skip_reason),
        ext_data=ext_data,
    )
