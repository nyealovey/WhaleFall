"""邮件告警相关定时任务."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app import create_app, db
from app.core.exceptions import ValidationError
from app.models.task_run import TaskRun
from app.schemas.task_run_summary import TaskRunSummaryFactory
from app.services.alerts.email_alert_digest_service import EmailAlertDigestService
from app.services.alerts.email_alert_event_service import EmailAlertEventService
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils

_RULE_ITEMS = (
    ("database_capacity_growth", "数据库容量异常增长"),
    ("account_sync_failure", "账户同步异常"),
    ("database_sync_failure", "数据库同步异常"),
    ("privileged_account_discovery", "新增高权限账户"),
    ("backup_status_issue", "备份告警"),
)
_SEND_STEP = ("deliver_digest", "发送汇总邮件")


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _as_dict(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): val for key, val in value.items()}


def _as_rule_results(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [_as_dict(item) for item in value]


def _resolve_run_id(
    *,
    task_runs_service: TaskRunsWriteService,
    manual_run: bool,
    created_by: int | None,
    run_id: str | None,
) -> str:
    trigger_source = "manual" if manual_run else "scheduled"
    if run_id:
        existing_run = TaskRun.query.filter_by(run_id=run_id).first()
        if existing_run is None:
            raise ValidationError("run_id 不存在,无法写入任务运行记录", extra={"run_id": run_id})
        return run_id

    return task_runs_service.start_run(
        task_key="email_alert",
        task_name="邮件告警汇总",
        task_category="notification",
        trigger_source=trigger_source,
        created_by=created_by,
        summary_json=None,
    )


def _init_items(task_runs_service: TaskRunsWriteService, run_id: str) -> None:
    items = [
        TaskRunItemInit(item_type="rule", item_key=item_key, item_name=item_name) for item_key, item_name in _RULE_ITEMS
    ]
    items.append(TaskRunItemInit(item_type="step", item_key=_SEND_STEP[0], item_name=_SEND_STEP[1]))
    task_runs_service.init_items(run_id, items=items)
    db.session.commit()


def _complete_rule_items(
    task_runs_service: TaskRunsWriteService, run_id: str, rule_results: list[dict[str, object]]
) -> None:
    for rule in rule_results:
        item_key = str(rule.get("item_key") or "")
        if not item_key:
            continue
        pending_count = _as_int(rule.get("pending_count"))
        sent_count = _as_int(rule.get("sent_count"))
        task_runs_service.start_item(run_id, item_type="rule", item_key=item_key)
        task_runs_service.complete_item(
            run_id,
            item_type="rule",
            item_key=item_key,
            metrics_json={"pending_count": pending_count, "sent_count": sent_count},
            details_json={
                "display_state": rule.get("display_state"),
                "summary": rule.get("summary"),
                "enabled": bool(rule.get("enabled", False)),
                "pending_count": pending_count,
                "sent_count": sent_count,
            },
        )


def _write_send_step(task_runs_service: TaskRunsWriteService, run_id: str, send_step: dict[str, object]) -> None:
    task_runs_service.start_item(run_id, item_type="step", item_key=_SEND_STEP[0])
    details_json = {
        "display_state": send_step.get("display_state"),
        "summary": send_step.get("summary"),
        "skip_reason": send_step.get("skip_reason"),
    }
    metrics_json = {"recipient_count": _as_int(send_step.get("recipient_count"))}
    status = str(send_step.get("status") or "completed")
    if status == "failed":
        task_runs_service.fail_item(
            run_id,
            item_type="step",
            item_key=_SEND_STEP[0],
            error_message=str(send_step.get("error_message") or send_step.get("summary") or "发送汇总邮件失败"),
            details_json=details_json,
        )
        return
    task_runs_service.complete_item(
        run_id,
        item_type="step",
        item_key=_SEND_STEP[0],
        metrics_json=metrics_json,
        details_json=details_json,
    )


def _write_summary(run_id: str, summary: dict[str, Any]) -> None:
    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run is None or current_run.status == "cancelled":
        return

    send_step = _as_dict(summary.get("send_step"))
    if send_step.get("status") == "failed":
        current_run.status = "failed"
        current_run.error_message = str(
            send_step.get("error_message") or send_step.get("summary") or "发送汇总邮件失败"
        )
        current_run.completed_at = time_utils.now()

    current_run.summary_json = TaskRunSummaryFactory.base(
        task_key="email_alert",
        metrics=[
            {"key": "event_count", "label": "事件数", "value": _as_int(summary.get("event_count")), "unit": "条"},
            {
                "key": "recipient_count",
                "label": "收件人数",
                "value": _as_int(summary.get("recipient_count")),
                "unit": "个",
            },
        ],
        flags={
            "skipped": bool(summary.get("skipped", False)),
            "skip_reason": summary.get("skip_reason"),
        },
        ext_data={
            "sent": bool(summary.get("sent", False)),
            "subject": summary.get("subject"),
            "event_count": _as_int(summary.get("event_count")),
            "recipient_count": _as_int(summary.get("recipient_count")),
            "rule_results": summary.get("rule_results") or [],
            "send_step": send_step,
        },
    )


def _fail_unexpected(
    *,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    exc: Exception,
) -> None:
    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run is not None and current_run.status != "cancelled":
        current_run.status = "failed"
        current_run.error_message = str(exc)
        current_run.completed_at = time_utils.now()
        current_run.summary_json = TaskRunSummaryFactory.base(
            task_key="email_alert",
            ext_data={"error": str(exc)},
        )
    try:
        task_runs_service.fail_item(
            run_id,
            item_type="step",
            item_key=_SEND_STEP[0],
            error_message=str(exc),
            details_json={"display_state": "failed", "summary": "发送汇总邮件失败"},
        )
    except Exception:
        return


def email_alert(
    *,
    manual_run: bool = False,
    created_by: int | None = None,
    run_id: str | None = None,
    **_: object,
) -> dict[str, Any]:
    """发送每日邮件告警汇总."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        logger = get_system_logger()
        task_runs_service = TaskRunsWriteService()
        resolved_run_id = _resolve_run_id(
            task_runs_service=task_runs_service,
            manual_run=manual_run,
            created_by=created_by,
            run_id=run_id,
        )
        db.session.commit()
        _init_items(task_runs_service, resolved_run_id)

        try:
            EmailAlertEventService().sync_backup_issue_events_for_active_instances()
            summary = EmailAlertDigestService().send_pending_digest()
            _complete_rule_items(task_runs_service, resolved_run_id, _as_rule_results(summary.get("rule_results")))
            _write_send_step(task_runs_service, resolved_run_id, _as_dict(summary.get("send_step")))
            _write_summary(resolved_run_id, summary)
            task_runs_service.finalize_run(resolved_run_id)
            db.session.commit()
            send_step = _as_dict(summary.get("send_step"))
            success = str(send_step.get("status") or "completed") != "failed"
            return {"success": success, "run_id": resolved_run_id, **summary}
        except Exception as exc:
            db.session.rollback()
            _fail_unexpected(task_runs_service=task_runs_service, run_id=resolved_run_id, exc=exc)
            task_runs_service.finalize_run(resolved_run_id)
            db.session.commit()
            logger.exception(
                "发送邮件告警汇总失败",
                module="email_alerts",
                task="email_alert",
                error=str(exc),
            )
            return {
                "success": False,
                "message": f"邮件告警汇总失败: {exc!s}",
                "error": str(exc),
                "run_id": resolved_run_id,
            }
