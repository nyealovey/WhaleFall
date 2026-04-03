from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from typing import cast

import pytest

from app.services.task_runs.task_runs_write_service import TaskRunItemInit
from app.tasks import email_alert_tasks


class _StubApp:
    def app_context(self):
        return nullcontext()


class _StubLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return None

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return None

    def exception(self, *_args: object, **_kwargs: object) -> None:
        return None


@pytest.mark.unit
def test_email_alert_skips_send_step_when_no_pending_events(monkeypatch) -> None:
    monkeypatch.setattr(email_alert_tasks, "create_app", lambda **_: _StubApp())
    monkeypatch.setattr(email_alert_tasks, "get_system_logger", lambda: _StubLogger())

    class _StubDigestService:
        def send_pending_digest(self) -> dict[str, object]:
            return {
                "sent": False,
                "skipped": True,
                "skip_reason": "no_pending_events",
                "event_count": 0,
                "rule_results": [
                    {
                        "item_key": "database_capacity_growth",
                        "item_name": "数据库容量异常增长",
                        "display_state": "no_event",
                        "summary": "当天未产生事件",
                    },
                    {
                        "item_key": "account_sync_failure",
                        "item_name": "账户同步异常",
                        "display_state": "no_event",
                        "summary": "当天未产生事件",
                    },
                    {
                        "item_key": "database_sync_failure",
                        "item_name": "数据库同步异常",
                        "display_state": "no_event",
                        "summary": "当天未产生事件",
                    },
                    {
                        "item_key": "privileged_account_discovery",
                        "item_name": "新增高权限账户",
                        "display_state": "no_event",
                        "summary": "当天未产生事件",
                    },
                ],
                "send_step": {
                    "item_key": "deliver_digest",
                    "item_name": "发送汇总邮件",
                    "status": "completed",
                    "display_state": "skipped_no_event",
                    "summary": "无待发送事件",
                    "skip_reason": "no_pending_events",
                },
            }

    monkeypatch.setattr(email_alert_tasks, "EmailAlertDigestService", lambda: _StubDigestService())

    run = SimpleNamespace(status="running", error_message=None, completed_at=None, summary_json=None)

    class _StubQuery:
        def filter_by(self, **_: object):
            return self

        def first(self):
            return run

    monkeypatch.setattr(email_alert_tasks, "TaskRun", SimpleNamespace(query=_StubQuery()))

    class _StubTaskRunsWriteService:
        def __init__(self) -> None:
            self.finalized: list[str] = []
            self.started: list[dict[str, object]] = []
            self.init_calls: list[tuple[str, list[TaskRunItemInit]]] = []
            self.completed_calls: list[dict[str, object]] = []

        def start_run(self, **kwargs: object) -> str:
            self.started.append(dict(kwargs))
            return "run-1"

        def init_items(self, run_id: str, *, items: list[TaskRunItemInit]) -> None:
            self.init_calls.append((run_id, list(items)))

        def start_item(self, run_id: str, **kwargs: object) -> None:
            return None

        def complete_item(self, run_id: str, **kwargs: object) -> None:
            payload: dict[str, object] = {"run_id": run_id}
            payload.update(cast("dict[str, object]", kwargs))
            self.completed_calls.append(payload)

        def finalize_run(self, run_id: str) -> None:
            self.finalized.append(run_id)

    task_runs_service = _StubTaskRunsWriteService()
    monkeypatch.setattr(email_alert_tasks, "TaskRunsWriteService", lambda: task_runs_service)

    commits: list[bool] = []
    monkeypatch.setattr(email_alert_tasks.db.session, "commit", lambda: commits.append(True))
    monkeypatch.setattr(email_alert_tasks.db.session, "rollback", lambda: None)

    result = email_alert_tasks.email_alert()

    assert result["success"] is True
    assert result["event_count"] == 0
    assert task_runs_service.started == [
        {
            "task_key": "email_alert",
            "task_name": "邮件告警汇总",
            "task_category": "notification",
            "trigger_source": "scheduled",
            "created_by": None,
            "summary_json": None,
        }
    ]
    assert task_runs_service.init_calls
    run_id, items = task_runs_service.init_calls[0]
    assert run_id == "run-1"
    assert [(item.item_type, item.item_key, item.item_name) for item in items] == [
        ("rule", "database_capacity_growth", "数据库容量异常增长"),
        ("rule", "account_sync_failure", "账户同步异常"),
        ("rule", "database_sync_failure", "数据库同步异常"),
        ("rule", "privileged_account_discovery", "新增高权限账户"),
        ("step", "deliver_digest", "发送汇总邮件"),
    ]
    assert any(
        call["item_key"] == "deliver_digest"
        and call["details_json"]
        == {
            "display_state": "skipped_no_event",
            "summary": "无待发送事件",
            "skip_reason": "no_pending_events",
        }
        for call in task_runs_service.completed_calls
    )
    assert task_runs_service.finalized == ["run-1"]
    assert commits
