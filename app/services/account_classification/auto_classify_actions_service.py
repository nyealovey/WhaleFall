"""Account auto-classify actions service.

将“账户分类管理 - 自动分类”动作的编排逻辑下沉到 service 层：
- 创建 TaskRun 并返回 run_id
- 启动后台线程执行 `auto_classify_accounts`
"""

from __future__ import annotations

import importlib
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import SystemError, ValidationError
from app.core.types import ContextDict
from app.core.types.account_scope import AccountScope, parse_account_scope
from app.infra.route_safety import log_with_context
from app.schemas.task_run_summary import TaskRunSummaryFactory
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

BACKGROUND_EXCEPTIONS: tuple[type[Exception], ...] = (
    ValidationError,
    SystemError,
    SQLAlchemyError,
    RuntimeError,
)


@dataclass(frozen=True, slots=True)
class AutoClassifyAccountsPreparedRun:
    """后台自动分类准备结果(已创建 TaskRun,尚未启动线程)."""

    run_id: str
    instance_id: int | None
    account_scope: str | None


@dataclass(frozen=True, slots=True)
class AutoClassifyAccountsLaunchResult:
    """后台自动分类启动结果."""

    run_id: str
    instance_id: int | None
    account_scope: str | None
    thread_name: str


def _resolve_default_task() -> Callable[..., Any]:
    """惰性加载默认任务函数,避免导入期循环依赖."""
    module = importlib.import_module("app.tasks.account_classification_auto_tasks")
    return cast("Callable[..., Any]", module.auto_classify_accounts)


def _launch_background_auto_classify(
    *,
    created_by: int | None,
    run_id: str,
    instance_id: int | None,
    task: Callable[..., Any],
    account_scope: AccountScope | None = None,
) -> threading.Thread:
    def _run_task(
        captured_created_by: int | None,
        captured_run_id: str,
        captured_instance_id: int | None,
        captured_account_scope: AccountScope | None,
    ) -> None:
        try:
            task(
                created_by=captured_created_by,
                run_id=captured_run_id,
                instance_id=captured_instance_id,
                account_scope=captured_account_scope.value if captured_account_scope else None,
            )
        except BACKGROUND_EXCEPTIONS as exc:
            context: ContextDict = {
                "created_by": captured_created_by,
                "run_id": captured_run_id,
                "instance_id": captured_instance_id,
            }
            if captured_account_scope is not None:
                context["account_scope"] = captured_account_scope.value
            log_with_context(
                "error",
                "后台自动分类失败",
                module="account_classification",
                action="auto_classify_accounts_background",
                context=context,
                extra={
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
                include_actor=False,
            )

    thread = threading.Thread(
        target=_run_task,
        args=(created_by, run_id, instance_id, account_scope),
        name="auto_classify_accounts_manual",
        daemon=True,
    )
    thread.start()
    return thread


class AutoClassifyActionsService:
    """自动分类动作编排服务."""

    def __init__(self, *, task: Callable[..., Any] | None = None) -> None:
        """初始化服务并允许注入 task(便于测试/替换执行入口)."""
        self._task = task or _resolve_default_task()

    def prepare_background_auto_classify(
        self,
        *,
        created_by: int | None,
        instance_id: int | None,
        account_scope: AccountScope | None = None,
    ) -> AutoClassifyAccountsPreparedRun:
        """创建 TaskRun 并返回 run_id(不启动线程)."""
        run_id = TaskRunsWriteService().start_run(
            task_key="auto_classify_accounts",
            task_name="自动分类",
            task_category="classification",
            trigger_source="manual",
            created_by=created_by,
            summary_json=TaskRunSummaryFactory.base(
                task_key="auto_classify_accounts",
                inputs={"instance_id": instance_id, "account_scope": account_scope.value if account_scope else None},
            ),
            result_url="/accounts/classifications",
        )
        return AutoClassifyAccountsPreparedRun(
            run_id=run_id,
            instance_id=instance_id,
            account_scope=account_scope.value if account_scope else None,
        )

    def launch_background_auto_classify(
        self,
        *,
        created_by: int | None,
        prepared: AutoClassifyAccountsPreparedRun,
    ) -> AutoClassifyAccountsLaunchResult:
        """启动后台线程执行自动分类."""
        thread = _launch_background_auto_classify(
            created_by=created_by,
            run_id=prepared.run_id,
            instance_id=prepared.instance_id,
            task=self._task,
            account_scope=parse_account_scope(prepared.account_scope),
        )
        return AutoClassifyAccountsLaunchResult(
            run_id=prepared.run_id,
            instance_id=prepared.instance_id,
            account_scope=prepared.account_scope,
            thread_name=thread.name,
        )
