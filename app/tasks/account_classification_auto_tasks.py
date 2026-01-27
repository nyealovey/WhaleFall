"""账户自动分类任务.

用于“账户分类管理”页面按钮触发的异步任务：
- 统一创建/复用 TaskRun
- 按规则维度写入 TaskRunItem 进度
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from app import create_app, db
from app.core.exceptions import ValidationError
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.repositories.account_classification_repository import ClassificationRepository
from app.schemas.task_run_summary import TaskRunSummaryFactory
from app.services.account_classification.dsl_v4 import (
    DslV4Evaluator,
    collect_dsl_v4_validation_errors,
    is_dsl_v4_expression,
)
from app.services.task_runs.task_run_summary_builders import build_auto_classify_accounts_summary
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def _duration_ms(started_at: float) -> int:
    return round((time.perf_counter() - started_at) * 1000)


def _resolve_run_id(
    *,
    task_runs_service: TaskRunsWriteService,
    instance_id: int | None,
    created_by: int | None,
    run_id: str | None,
) -> str:
    resolved_run_id = run_id
    if resolved_run_id:
        existing_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
        if existing_run is None:
            raise ValidationError("run_id 不存在,无法写入任务运行记录", extra={"run_id": resolved_run_id})
        return resolved_run_id

    resolved_run_id = task_runs_service.start_run(
        task_key="auto_classify_accounts",
        task_name="自动分类",
        task_category="classification",
        trigger_source="manual",
        created_by=created_by,
        summary_json=TaskRunSummaryFactory.base(
            task_key="auto_classify_accounts",
            inputs={"instance_id": instance_id},
        ),
        result_url="/accounts/classifications",
    )
    db.session.commit()
    return resolved_run_id


def _is_cancelled(run_id: str) -> bool:
    current = TaskRun.query.filter_by(run_id=run_id).first()
    return bool(current and current.status == "cancelled")


def _get_valid_dsl_v4_expression(rule: Any) -> str:
    expression = rule.get_rule_expression()
    if not is_dsl_v4_expression(expression):
        raise ValidationError("rule_expression 仅支持 DSL v4")
    validation_errors = collect_dsl_v4_validation_errors(expression)
    if validation_errors:
        raise ValidationError("rule_expression 非法: " + "; ".join(validation_errors))
    return expression


def _get_permission_facts(account: Any) -> Mapping[str, object]:
    raw_facts = getattr(account, "permission_facts", None)
    if not isinstance(raw_facts, Mapping):
        raise ValidationError(
            "permission_facts 缺失,请先执行账户同步",
            extra={
                "account_id": getattr(account, "id", None),
                "instance_id": getattr(account, "instance_id", None),
            },
        )
    return raw_facts


def _find_matched_accounts(*, expression: str, accounts: list[Any]) -> list[Any]:
    matched_accounts: list[Any] = []
    for account in accounts:
        facts = _get_permission_facts(account)
        outcome = DslV4Evaluator(facts=facts).evaluate(expression)
        if outcome.matched:
            matched_accounts.append(account)
    return matched_accounts


def _build_accounts_by_db_type(accounts: list[Any]) -> dict[str, list[Any]]:
    accounts_by_db_type: dict[str, list[Any]] = {}
    for account in accounts:
        db_type = str(getattr(account, "db_type", "") or "").strip().lower()
        if not db_type:
            continue
        accounts_by_db_type.setdefault(db_type, []).append(account)
    return accounts_by_db_type


def _finalize_run_no_rules(
    *,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    instance_id: int | None,
    started_at: float,
    accounts_count: int,
) -> dict[str, Any]:
    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run is not None and current_run.status != "cancelled":
        current_run.status = "failed"
        current_run.error_message = "没有可用的分类规则"
        current_run.summary_json = build_auto_classify_accounts_summary(
            task_key="auto_classify_accounts",
            inputs={"instance_id": instance_id},
            rules_count=0,
            accounts_count=accounts_count,
            total_matches=0,
            total_classifications_added=0,
            failed_count=0,
            duration_ms=_duration_ms(started_at),
        )
    task_runs_service.finalize_run(run_id)
    db.session.commit()
    return {"success": False, "message": "没有可用的分类规则", "run_id": run_id}


def _finalize_run_no_accounts(
    *,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    instance_id: int | None,
    started_at: float,
    rules: list[Any],
) -> dict[str, Any]:
    for rule in rules:
        rule_id_value = getattr(rule, "id", None)
        if rule_id_value is None:
            continue
        rule_key = str(rule_id_value)
        task_runs_service.start_item(run_id, item_type="rule", item_key=rule_key)
        task_runs_service.complete_item(
            run_id,
            item_type="rule",
            item_key=rule_key,
            metrics_json={
                "matched_accounts_total": 0,
                "classifications_added": 0,
                "duration_ms": 0,
                "instances_covered": 0,
            },
            details_json={"skipped": True, "skip_reason": "没有需要分类的账户"},
        )

    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run is not None and current_run.status != "cancelled":
        current_run.summary_json = build_auto_classify_accounts_summary(
            task_key="auto_classify_accounts",
            inputs={"instance_id": instance_id},
            rules_count=len(rules),
            accounts_count=0,
            total_matches=0,
            total_classifications_added=0,
            failed_count=0,
            duration_ms=_duration_ms(started_at),
            skipped=True,
            skip_reason="没有需要分类的账户",
        )

    task_runs_service.finalize_run(run_id)
    db.session.commit()
    return {"success": True, "message": "没有需要分类的账户", "run_id": run_id}


def _process_rule(
    *,
    rule: Any,
    repository: ClassificationRepository,
    accounts_by_db_type: dict[str, list[Any]],
    db_type: str,
    rule_id: int,
) -> tuple[int, int, int, int]:
    rule_started_at = time.perf_counter()
    expression = _get_valid_dsl_v4_expression(rule)
    matched_accounts = _find_matched_accounts(expression=expression, accounts=accounts_by_db_type.get(db_type) or [])

    added_count = repository.upsert_assignments(
        matched_accounts,
        int(getattr(rule, "classification_id", 0) or 0),
        rule_id=rule_id,
    )

    matched_count = len(matched_accounts)
    instances_covered = len({int(getattr(acc, "instance_id", 0) or 0) for acc in matched_accounts if acc})
    duration_ms = _duration_ms(rule_started_at)
    return matched_count, int(added_count), duration_ms, instances_covered


def _finalize_rule_failure(
    *,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    rule_key: str,
    rule_id: int,
    rule: Any,
    exc: Exception,
) -> None:
    task_runs_service.fail_item(
        run_id,
        item_type="rule",
        item_key=rule_key,
        error_message=str(exc),
        details_json={
            "rule_id": rule_id,
            "rule_name": getattr(rule, "rule_name", None),
            "db_type": getattr(rule, "db_type", None),
            "classification_id": getattr(rule, "classification_id", None),
        },
    )
    now = time_utils.now()
    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run is not None and current_run.status != "cancelled":
        current_run.status = "failed"
        current_run.error_message = str(exc)
        current_run.completed_at = now
        for item in TaskRunItem.query.filter_by(run_id=run_id).all():
            if item.status in {"pending", "running"}:
                item.status = "failed"
                item.error_message = str(exc)
                item.completed_at = now
    task_runs_service.finalize_run(run_id)
    db.session.commit()


def _finalize_run_success(
    *,
    task_runs_service: TaskRunsWriteService,
    sync_logger: Any,
    run_id: str,
    instance_id: int | None,
    started_at: float,
    rules_count: int,
    accounts_count: int,
    total_matches: int,
    total_classifications_added: int,
) -> dict[str, Any]:
    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run is not None and current_run.status != "cancelled":
        current_run.summary_json = build_auto_classify_accounts_summary(
            task_key="auto_classify_accounts",
            inputs={"instance_id": instance_id},
            rules_count=rules_count,
            accounts_count=accounts_count,
            total_matches=total_matches,
            total_classifications_added=total_classifications_added,
            failed_count=0,
            duration_ms=_duration_ms(started_at),
        )

    task_runs_service.finalize_run(run_id)
    db.session.commit()

    sync_logger.info(
        "自动分类完成",
        module="account_classification",
        task="auto_classify_accounts",
        run_id=run_id,
        instance_id=instance_id,
        duration_seconds=round(time.perf_counter() - started_at, 2),
    )
    return {"success": True, "message": "自动分类完成", "run_id": run_id}


def auto_classify_accounts(
    *,
    instance_id: int | None = None,
    created_by: int | None = None,
    run_id: str | None = None,
    **_: object,
) -> dict[str, Any]:
    """执行自动分类,并写入 TaskRun."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        task_runs_service = TaskRunsWriteService()
        resolved_run_id = _resolve_run_id(
            task_runs_service=task_runs_service,
            instance_id=instance_id,
            created_by=created_by,
            run_id=run_id,
        )
        if _is_cancelled(resolved_run_id):
            sync_logger.info(
                "任务已取消,跳过执行",
                module="account_classification",
                task="auto_classify_accounts",
                run_id=resolved_run_id,
                instance_id=instance_id,
            )
            return {"success": True, "message": "任务已取消", "run_id": resolved_run_id}

        started_at = time.perf_counter()
        repository = ClassificationRepository()
        rules = repository.fetch_active_rules()
        accounts = repository.fetch_accounts(instance_id=instance_id)

        if not rules:
            return _finalize_run_no_rules(
                task_runs_service=task_runs_service,
                run_id=resolved_run_id,
                instance_id=instance_id,
                started_at=started_at,
                accounts_count=len(accounts),
            )

        task_runs_service.init_items(
            resolved_run_id,
            items=[
                TaskRunItemInit(
                    item_type="rule",
                    item_key=str(rule.id),
                    item_name=getattr(rule, "rule_name", None),
                )
                for rule in rules
                if getattr(rule, "id", None) is not None
            ],
        )
        db.session.commit()

        if not accounts:
            return _finalize_run_no_accounts(
                task_runs_service=task_runs_service,
                run_id=resolved_run_id,
                instance_id=instance_id,
                started_at=started_at,
                rules=rules,
            )

        # 重新分类前清空旧分配
        repository.cleanup_all_assignments()
        db.session.commit()

        accounts_by_db_type = _build_accounts_by_db_type(accounts)

        total_matches = 0
        total_classifications_added = 0

        for rule in rules:
            if _is_cancelled(resolved_run_id):
                sync_logger.info(
                    "任务已取消,提前退出规则循环",
                    module="account_classification",
                    task="auto_classify_accounts",
                    run_id=resolved_run_id,
                    instance_id=instance_id,
                )
                task_runs_service.finalize_run(resolved_run_id)
                db.session.commit()
                return {"success": True, "message": "任务已取消", "run_id": resolved_run_id}

            rule_id_value = getattr(rule, "id", None)
            if rule_id_value is None:
                continue

            rule_id = int(rule_id_value)
            rule_key = str(rule_id)
            db_type = str(getattr(rule, "db_type", "") or "").strip().lower()

            task_runs_service.start_item(resolved_run_id, item_type="rule", item_key=rule_key)
            db.session.commit()

            try:
                matched_count, added_count, duration_ms, instances_covered = _process_rule(
                    rule=rule,
                    repository=repository,
                    accounts_by_db_type=accounts_by_db_type,
                    db_type=db_type,
                    rule_id=rule_id,
                )
                total_matches += matched_count
                total_classifications_added += added_count

                task_runs_service.complete_item(
                    resolved_run_id,
                    item_type="rule",
                    item_key=rule_key,
                    metrics_json={
                        "matched_accounts_total": matched_count,
                        "classifications_added": added_count,
                        "duration_ms": duration_ms,
                        "instances_covered": instances_covered,
                    },
                    details_json={
                        "classification_id": getattr(rule, "classification_id", None),
                        "db_type": db_type,
                    },
                )
                db.session.commit()
            except Exception as rule_exc:
                _finalize_rule_failure(
                    task_runs_service=task_runs_service,
                    run_id=resolved_run_id,
                    rule_key=rule_key,
                    rule_id=rule_id,
                    rule=rule,
                    exc=rule_exc,
                )
                raise

        return _finalize_run_success(
            task_runs_service=task_runs_service,
            sync_logger=sync_logger,
            run_id=resolved_run_id,
            instance_id=instance_id,
            started_at=started_at,
            rules_count=len(rules),
            accounts_count=len(accounts),
            total_matches=total_matches,
            total_classifications_added=total_classifications_added,
        )
