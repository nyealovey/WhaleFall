"""邮件告警相关定时任务."""

from __future__ import annotations

from typing import Any

from app import create_app, db
from app.models.task_run import TaskRun
from app.schemas.task_run_summary import TaskRunSummaryFactory
from app.services.alerts.email_alert_digest_service import EmailAlertDigestService
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils


def send_email_alert_digest(**_: object) -> dict[str, Any]:
    """发送每日邮件告警汇总."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        logger = get_system_logger()
        task_runs_service = TaskRunsWriteService()
        run_id = task_runs_service.start_run(
            task_key="send_email_alert_digest",
            task_name="邮件告警汇总",
            task_category="notification",
            trigger_source="scheduled",
            summary_json=None,
        )
        db.session.commit()
        result: dict[str, Any]

        try:
            summary = EmailAlertDigestService().send_pending_digest()
            current_run = TaskRun.query.filter_by(run_id=run_id).first()
            if current_run is not None and current_run.status != "cancelled":
                current_run.summary_json = TaskRunSummaryFactory.base(
                    task_key="send_email_alert_digest",
                    ext_data=summary,
                    flags={
                        "skipped": bool(summary.get("skipped", False)),
                        "skip_reason": summary.get("skip_reason"),
                    },
                )
            task_runs_service.finalize_run(run_id)
            db.session.commit()
            result = {"success": True, "run_id": run_id, **summary}
        except Exception as exc:
            db.session.rollback()
            current_run = TaskRun.query.filter_by(run_id=run_id).first()
            if current_run is not None and current_run.status != "cancelled":
                current_run.status = "failed"
                current_run.error_message = str(exc)
                current_run.completed_at = time_utils.now()
                current_run.summary_json = TaskRunSummaryFactory.base(
                    task_key="send_email_alert_digest",
                    ext_data={"error": str(exc)},
                )
            task_runs_service.finalize_run(run_id)
            db.session.commit()
            logger.exception(
                "发送邮件告警汇总失败",
                module="email_alerts",
                task="send_email_alert_digest",
                error=str(exc),
            )
            raise
        else:
            return result
