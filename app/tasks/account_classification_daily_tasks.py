"""账户分类每日统计定时任务."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Mapping
from datetime import date
from typing import Any

from app import create_app, db
from app.core.exceptions import ValidationError
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.repositories.account_classification_daily_stats_repository import AccountClassificationDailyStatsRepository
from app.repositories.account_classification_repository import ClassificationRepository
from app.services.account_classification.dsl_v4 import DslV4Evaluator
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def calculate_account_classification_daily_stats(
    *,
    manual_run: bool = False,
    created_by: int | None = None,
    run_id: str | None = None,
    stat_date: date | None = None,
    **_: object,
) -> dict[str, Any]:
    """计算并写入账户分类每日统计(规则命中数 + 分类去重账号数)."""
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        task_runs_service = TaskRunsWriteService()
        started_at = time.perf_counter()

        trigger_source = "manual" if manual_run else "scheduled"
        resolved_run_id = run_id
        if resolved_run_id:
            existing_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if existing_run is None:
                raise ValidationError("run_id 不存在,无法写入任务运行记录", extra={"run_id": resolved_run_id})
        else:
            resolved_run_id = task_runs_service.start_run(
                task_key="calculate_account_classification_daily_stats",
                task_name="账户分类统计",
                task_category="classification",
                trigger_source=trigger_source,
                created_by=created_by,
                summary_json=None,
                result_url="/accounts/classifications",
            )
            db.session.commit()

        def _is_cancelled() -> bool:
            current = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            return bool(current and current.status == "cancelled")

        sync_logger.info(
            "开始计算账户分类每日统计",
            module="account_classification_daily_stats",
            run_id=resolved_run_id,
        )

        try:
            if _is_cancelled():
                sync_logger.info(
                    "任务已取消,跳过执行",
                    module="account_classification_daily_stats",
                    run_id=resolved_run_id,
                )
                return {"success": True, "message": "任务已取消"}

            resolved_date = stat_date or time_utils.now_china().date()
            computed_at = time_utils.now()

            classification_repo = ClassificationRepository()
            daily_stats_repo = AccountClassificationDailyStatsRepository()

            rules = classification_repo.fetch_active_rules()
            accounts = classification_repo.fetch_accounts()

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

            if not rules:
                current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
                if current_run is not None and current_run.status != "cancelled":
                    current_run.status = "failed"
                    current_run.error_message = "没有可用的分类规则"
                    current_run.summary_json = {
                        "stat_date": resolved_date.isoformat(),
                        "rules_count": 0,
                        "accounts_count": len(accounts),
                        "rule_match_rows": 0,
                        "classification_match_rows": 0,
                    }
                task_runs_service.finalize_run(resolved_run_id)
                db.session.commit()
                return {"success": False, "message": "没有可用的分类规则", "run_id": resolved_run_id}

            if not accounts:
                current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
                if current_run is not None and current_run.status != "cancelled":
                    current_run.status = "failed"
                    current_run.error_message = "没有需要统计的账户"
                    current_run.summary_json = {
                        "stat_date": resolved_date.isoformat(),
                        "rules_count": len(rules),
                        "accounts_count": 0,
                        "rule_match_rows": 0,
                        "classification_match_rows": 0,
                    }
                    now = time_utils.now()
                    for item in TaskRunItem.query.filter_by(run_id=resolved_run_id).all():
                        if item.status in {"pending", "running"}:
                            item.status = "failed"
                            item.error_message = "没有需要统计的账户"
                            item.completed_at = now
                task_runs_service.finalize_run(resolved_run_id)
                db.session.commit()
                return {"success": False, "message": "没有需要统计的账户", "run_id": resolved_run_id}

            accounts_by_db_type: dict[str, list[Any]] = defaultdict(list)
            instance_ids_by_db_type: dict[str, set[int]] = defaultdict(set)

            for account in accounts:
                db_type = str(getattr(account, "db_type", "") or "").strip().lower()
                instance_id = int(getattr(account, "instance_id", 0) or 0)
                if not db_type or instance_id <= 0:
                    continue
                accounts_by_db_type[db_type].append(account)
                instance_ids_by_db_type[db_type].add(instance_id)

            classification_db_types: dict[int, set[str]] = defaultdict(set)
            for rule in rules:
                db_type = str(getattr(rule, "db_type", "") or "").strip().lower()
                if not db_type:
                    continue
                classification_db_types[int(rule.classification_id)].add(db_type)

            matched_accounts_by_classification_instance: dict[tuple[int, str, int], set[int]] = defaultdict(set)
            rule_records: list[dict[str, object]] = []

            for rule in rules:
                if _is_cancelled():
                    sync_logger.info(
                        "任务已取消,提前退出规则循环",
                        module="account_classification_daily_stats",
                        run_id=resolved_run_id,
                    )
                    task_runs_service.finalize_run(resolved_run_id)
                    db.session.commit()
                    return {"success": True, "message": "任务已取消", "run_id": resolved_run_id}

                rule_id_value = getattr(rule, "id", None)
                if rule_id_value is None:
                    continue
                rule_id = int(rule_id_value)
                rule_key = str(rule_id)

                task_runs_service.start_item(resolved_run_id, item_type="rule", item_key=rule_key)
                db.session.commit()

                started_rule_at = time.perf_counter()
                try:
                    db_type = str(getattr(rule, "db_type", "") or "").strip().lower()
                    classification_id = int(getattr(rule, "classification_id", 0) or 0)
                    expression = rule.get_rule_expression()

                    candidate_accounts = accounts_by_db_type.get(db_type) or []
                    instance_ids = sorted(instance_ids_by_db_type.get(db_type) or [])

                    matched_by_instance: dict[int, set[int]] = defaultdict(set)
                    for account in candidate_accounts:
                        account_id = int(getattr(account, "id", 0) or 0)
                        instance_id = int(getattr(account, "instance_id", 0) or 0)
                        if account_id <= 0 or instance_id <= 0:
                            continue

                        raw_facts = getattr(account, "permission_facts", None)
                        facts: Mapping[str, object] = raw_facts if isinstance(raw_facts, Mapping) else {}
                        merged_facts = dict(facts)
                        merged_facts["db_type"] = db_type

                        outcome = DslV4Evaluator(facts=merged_facts).evaluate(expression)
                        if not outcome.matched:
                            continue

                        matched_by_instance[instance_id].add(account_id)
                        matched_accounts_by_classification_instance[(classification_id, db_type, instance_id)].add(
                            account_id,
                        )

                    for instance_id in instance_ids:
                        matched = matched_by_instance.get(instance_id) or set()
                        rule_records.append(
                            {
                                "stat_date": resolved_date,
                                "rule_id": rule_id,
                                "classification_id": classification_id,
                                "db_type": db_type,
                                "instance_id": instance_id,
                                "matched_accounts_count": len(matched),
                                "computed_at": computed_at,
                                "created_at": computed_at,
                                "updated_at": computed_at,
                            },
                        )

                    duration_ms = int(round((time.perf_counter() - started_rule_at) * 1000))
                    matched_accounts_total = sum(len(values) for values in matched_by_instance.values())

                    task_runs_service.complete_item(
                        resolved_run_id,
                        item_type="rule",
                        item_key=rule_key,
                        metrics_json={
                            "matched_accounts_total": matched_accounts_total,
                            "rule_match_rows_written": len(instance_ids),
                            "duration_ms": duration_ms,
                            "instances_covered": len(instance_ids),
                        },
                        details_json={
                            "db_type": db_type,
                            "classification_id": classification_id,
                        },
                    )
                    db.session.commit()
                except Exception as rule_exc:  # noqa: BLE001 - task boundary + fail-fast
                    task_runs_service.fail_item(
                        resolved_run_id,
                        item_type="rule",
                        item_key=rule_key,
                        error_message=str(rule_exc),
                        details_json={
                            "rule_id": rule_id,
                            "rule_name": getattr(rule, "rule_name", None),
                            "db_type": getattr(rule, "db_type", None),
                        },
                    )
                    now = time_utils.now()
                    current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
                    if current_run is not None and current_run.status != "cancelled":
                        current_run.status = "failed"
                        current_run.error_message = str(rule_exc)
                        current_run.completed_at = now
                        for item in TaskRunItem.query.filter_by(run_id=resolved_run_id).all():
                            if item.status in {"pending", "running"}:
                                item.status = "failed"
                                item.error_message = str(rule_exc)
                                item.completed_at = now
                    task_runs_service.finalize_run(resolved_run_id)
                    db.session.commit()
                    raise

            classification_records: list[dict[str, object]] = []
            for classification_id, db_types in classification_db_types.items():
                for db_type in sorted(db_types):
                    instance_ids = sorted(instance_ids_by_db_type.get(db_type) or [])
                    for instance_id in instance_ids:
                        matched = (
                            matched_accounts_by_classification_instance.get(
                                (classification_id, db_type, instance_id),
                            )
                            or set()
                        )
                        classification_records.append(
                            {
                                "stat_date": resolved_date,
                                "classification_id": classification_id,
                                "db_type": db_type,
                                "instance_id": instance_id,
                                "matched_accounts_distinct_count": len(matched),
                                "computed_at": computed_at,
                                "created_at": computed_at,
                                "updated_at": computed_at,
                            },
                        )

            daily_stats_repo.upsert_rule_match_stats(rule_records, current_utc=computed_at)
            daily_stats_repo.upsert_classification_match_stats(classification_records, current_utc=computed_at)

            current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if current_run is not None and current_run.status != "cancelled":
                current_run.summary_json = {
                    "stat_date": resolved_date.isoformat(),
                    "computed_at": computed_at.isoformat(),
                    "rules_count": len(rules),
                    "accounts_count": len(accounts),
                    "rule_match_rows": len(rule_records),
                    "classification_match_rows": len(classification_records),
                }

            task_runs_service.finalize_run(resolved_run_id)
            db.session.commit()

            result = {
                "success": True,
                "message": "账户分类每日统计计算完成",
                "run_id": resolved_run_id,
                "stat_date": resolved_date.isoformat(),
                "computed_at": computed_at.isoformat(),
                "rules_count": len(rules),
                "accounts_count": len(accounts),
                "rule_match_rows": len(rule_records),
                "classification_match_rows": len(classification_records),
            }
        except Exception as exc:  # noqa: BLE001 - scheduler task boundary
            db.session.rollback()
            sync_logger.exception(
                "账户分类每日统计计算失败",
                module="account_classification_daily_stats",
                error=str(exc),
                run_id=resolved_run_id,
            )
            now = time_utils.now()
            current_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
            if current_run is not None and current_run.status != "cancelled":
                current_run.status = "failed"
                current_run.error_message = str(exc)
                current_run.completed_at = now
                for item in TaskRunItem.query.filter_by(run_id=resolved_run_id).all():
                    if item.status in {"pending", "running"}:
                        item.status = "failed"
                        item.error_message = str(exc)
                        item.completed_at = now
                task_runs_service.finalize_run(resolved_run_id)
                db.session.commit()
            return {
                "success": False,
                "message": f"账户分类每日统计计算失败: {exc!s}",
                "error": str(exc),
                "run_id": resolved_run_id,
            }

        sync_logger.info(
            "账户分类每日统计计算完成",
            module="account_classification_daily_stats",
            stat_date=result["stat_date"],
            computed_at=time_utils.format_china_time(result["computed_at"]),
            rules_count=result["rules_count"],
            accounts_count=result["accounts_count"],
            rule_match_rows=result["rule_match_rows"],
            classification_match_rows=result["classification_match_rows"],
            duration_seconds=round(time.perf_counter() - started_at, 2),
            run_id=resolved_run_id,
        )

        return result
