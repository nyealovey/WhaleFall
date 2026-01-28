"""账户同步相关定时任务."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import structlog
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.core.constants.sync_constants import SyncCategory, SyncOperationType
from app.core.exceptions import AppError, ValidationError
from app.models.instance import Instance
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.services.accounts_sync.accounts_sync_task_service import AccountsSyncTaskService
from app.services.accounts_sync.coordinator import AccountSyncCoordinator
from app.services.accounts_sync.permission_manager import PermissionSyncError
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.sync_session_service import SyncItemStats, sync_session_service
from app.services.task_runs.task_run_summary_builders import build_sync_accounts_summary
from app.services.task_runs.task_runs_write_service import TaskRunItemInit, TaskRunsWriteService
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types.structures import JsonDict
    from app.core.types.sync import CollectionSummary, InventorySummary, SyncStagesSummary
    from app.models.sync_instance_record import SyncInstanceRecord
    from app.models.sync_session import SyncSession


ACCOUNT_TASK_EXCEPTIONS: tuple[type[Exception], ...] = (
    AppError,
    PermissionSyncError,
    ConnectionAdapterError,
    SQLAlchemyError,
    RuntimeError,
    LookupError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
)


@dataclass(slots=True)
class _AccountsSyncTotals:
    instances_synced: int = 0
    instances_failed: int = 0
    accounts_synced: int = 0
    accounts_created: int = 0
    accounts_updated: int = 0
    accounts_deactivated: int = 0


def _resolve_run_id(
    *,
    task_runs_service: TaskRunsWriteService,
    manual_run: bool,
    created_by: int | None,
    run_id: str | None,
) -> str:
    trigger_source = "manual" if manual_run else "scheduled"
    resolved_run_id = run_id
    if resolved_run_id:
        existing_run = TaskRun.query.filter_by(run_id=resolved_run_id).first()
        if existing_run is None:
            raise ValidationError("run_id 不存在,无法写入任务运行记录", extra={"run_id": resolved_run_id})
        return resolved_run_id

    resolved_run_id = task_runs_service.start_run(
        task_key="sync_accounts",
        task_name="账户同步",
        task_category="account",
        trigger_source=trigger_source,
        created_by=created_by,
        summary_json=None,
        result_url="/accounts/ledgers",
    )
    db.session.commit()
    return resolved_run_id


def _is_cancelled(run_id: str) -> bool:
    current = TaskRun.query.filter_by(run_id=run_id).first()
    return bool(current and current.status == "cancelled")


def _finalize_no_instances(*, task_runs_service: TaskRunsWriteService, run_id: str, manual_run: bool) -> None:
    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run is not None and current_run.status != "cancelled":
        current_run.summary_json = build_sync_accounts_summary(
            task_key="sync_accounts",
            inputs={"manual_run": manual_run},
            instances_total=0,
            instances_successful=0,
            instances_failed=0,
            accounts_synced=0,
            accounts_created=0,
            accounts_updated=0,
            accounts_deactivated=0,
            session_id=None,
            skipped=True,
            skip_reason="没有找到启用的数据库实例",
        )
    task_runs_service.finalize_run(run_id)
    db.session.commit()


def _init_items(*, task_runs_service: TaskRunsWriteService, run_id: str, instances: list[Instance]) -> None:
    task_runs_service.init_items(
        run_id,
        items=[
            TaskRunItemInit(
                item_type="instance",
                item_key=str(instance.id),
                item_name=instance.name,
                instance_id=instance.id,
            )
            for instance in instances
        ],
    )
    db.session.commit()


def _resolve_session(
    *,
    manual_run: bool,
    created_by: int | None,
    session_id: str | None,
) -> SyncSession:
    sync_type_value = SyncOperationType.MANUAL_TASK.value if manual_run else SyncOperationType.SCHEDULED_TASK.value
    if session_id:
        session = sync_session_service.get_session_by_id(session_id)
        if session is None:
            raise ValidationError("指定的 session_id 不存在", extra={"session_id": session_id})
        return session

    return sync_session_service.create_session(
        sync_type=sync_type_value,
        sync_category=SyncCategory.ACCOUNT.value,
        created_by=created_by,
    )


def _create_records(*, session: SyncSession, instances: list[Instance]) -> list[SyncInstanceRecord]:
    instance_ids = [inst.id for inst in instances]
    records = sync_session_service.add_instance_records(
        session.session_id,
        instance_ids,
        sync_category=SyncCategory.ACCOUNT.value,
    )
    session.total_instances = len(instances)
    db.session.commit()
    return records


def _sync_instances(
    *,
    sync_logger: structlog.BoundLogger,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    session: SyncSession,
    instances: list[Instance],
    records: list[SyncInstanceRecord],
) -> _AccountsSyncTotals:
    totals = _AccountsSyncTotals()

    for i, instance in enumerate(instances):
        if _is_cancelled(run_id):
            sync_logger.info(
                "任务已取消,提前退出实例循环",
                module="accounts_sync",
                phase="running",
                operation="sync_accounts",
                run_id=run_id,
            )
            break

        record = records[i] if i < len(records) else None
        if record is None:
            continue

        task_runs_service.start_item(
            run_id,
            item_type="instance",
            item_key=str(instance.id),
        )
        db.session.commit()

        sync_session_service.start_instance_sync(record.id)
        db.session.commit()

        synced, failed = _sync_single_instance(
            session=session,
            record=record,
            instance=instance,
            sync_logger=sync_logger,
        )
        db.session.commit()
        totals.instances_synced += synced
        totals.instances_failed += failed

        totals.accounts_synced += int(record.items_synced or 0)
        totals.accounts_created += int(record.items_created or 0)
        totals.accounts_updated += int(record.items_updated or 0)
        totals.accounts_deactivated += int(record.items_deleted or 0)

        metrics = {
            "items_synced": record.items_synced or 0,
            "items_created": record.items_created or 0,
            "items_updated": record.items_updated or 0,
            "items_deleted": record.items_deleted or 0,
        }
        details = record.sync_details if isinstance(record.sync_details, dict) else {}
        if record.status == "completed":
            task_runs_service.complete_item(
                run_id,
                item_type="instance",
                item_key=str(instance.id),
                metrics_json=metrics,
                details_json=details,
            )
        else:
            task_runs_service.fail_item(
                run_id,
                item_type="instance",
                item_key=str(instance.id),
                error_message=record.error_message or "实例同步失败",
                details_json=details,
            )
        db.session.commit()

    return totals


def _finalize_success(
    *,
    sync_logger: structlog.BoundLogger,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    manual_run: bool,
    session: SyncSession,
    instances: list[Instance],
    totals: _AccountsSyncTotals,
) -> None:
    session.successful_instances = totals.instances_synced
    session.failed_instances = totals.instances_failed
    session.status = "completed" if totals.instances_failed == 0 else "failed"
    session.completed_at = time_utils.now()
    db.session.commit()

    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run is not None and current_run.status != "cancelled":
        current_run.summary_json = build_sync_accounts_summary(
            task_key="sync_accounts",
            inputs={"manual_run": manual_run},
            instances_total=len(instances),
            instances_successful=totals.instances_synced,
            instances_failed=totals.instances_failed,
            accounts_synced=totals.accounts_synced,
            accounts_created=totals.accounts_created,
            accounts_updated=totals.accounts_updated,
            accounts_deactivated=totals.accounts_deactivated,
            session_id=session.session_id,
        )

    task_runs_service.finalize_run(run_id)
    db.session.commit()

    sync_logger.info(
        "账户同步任务完成",
        module="accounts_sync",
        phase="completed",
        operation="sync_accounts",
        session_id=session.session_id,
        run_id=run_id,
        total_instances=len(instances),
        total_synced=totals.instances_synced,
        total_failed=totals.instances_failed,
    )


def _finalize_failure(
    *,
    sync_logger: structlog.BoundLogger,
    task_runs_service: TaskRunsWriteService,
    run_id: str,
    session: SyncSession | None,
    instances: list[Instance],
    exc: Exception,
) -> None:
    if session is not None:
        session.status = "failed"
        session.completed_at = time_utils.now()
        session.failed_instances = len(instances)
        db.session.commit()

    now = time_utils.now()
    current_run = TaskRun.query.filter_by(run_id=run_id).first()
    if current_run and current_run.status != "cancelled":
        current_run.error_message = str(exc)
        current_run.completed_at = now
        for item in TaskRunItem.query.filter_by(run_id=run_id).all():
            if item.status in {"pending", "running"}:
                item.status = "failed"
                item.error_message = str(exc)
                item.completed_at = now
        task_runs_service.finalize_run(run_id)
        db.session.commit()

    sync_logger.exception(
        "账户同步任务失败",
        module="accounts_sync",
        phase="error",
        operation="sync_accounts",
        run_id=run_id,
        error=str(exc),
    )


def _sync_single_instance(
    *,
    session: SyncSession,
    record: SyncInstanceRecord,
    instance: Instance,
    sync_logger: structlog.BoundLogger,
) -> tuple[int, int]:
    """同步单个实例账户,返回(成功数,失败数)."""
    instance_session_id = f"{session.session_id}_{instance.id}"
    result: tuple[int, int] = (0, 1)
    try:
        sync_logger.info(
            "开始实例账户同步",
            module="accounts_sync",
            phase="inventory",
            operation="sync_accounts",
            session_id=session.session_id,
            instance_id=instance.id,
            instance_name=instance.name,
        )

        try:
            with AccountSyncCoordinator(instance) as coordinator:
                summary = coordinator.sync_all(session_id=instance_session_id)
        except PermissionSyncError as permission_error:
            sync_session_service.fail_instance_sync(
                record.id,
                str(permission_error),
                sync_details={"version": 1, **cast(dict[str, Any], permission_error.summary)},
            )
            sync_logger.exception(
                "账户同步权限阶段失败",
                module="accounts_sync",
                phase="collection",
                operation="sync_accounts",
                session_id=session.session_id,
                instance_id=instance.id,
                instance_name=instance.name,
                errors=permission_error.summary.get("errors"),
                error=str(permission_error),
            )
            return 0, 1
        except RuntimeError as connection_error:
            error_message = str(connection_error) or "无法建立数据库连接"
            sync_session_service.fail_instance_sync(record.id, error_message)
            sync_logger.exception(
                "账户同步连接失败",
                module="accounts_sync",
                phase="connection",
                operation="sync_accounts",
                session_id=session.session_id,
                instance_id=instance.id,
                instance_name=instance.name,
                error=error_message,
            )
            return 0, 1

        summary_dict: SyncStagesSummary = cast("SyncStagesSummary", summary)
        inventory_value = summary_dict.get("inventory")
        if inventory_value is None:
            inventory_summary = cast("InventorySummary", {})
        elif isinstance(inventory_value, dict):
            inventory_summary = cast("InventorySummary", inventory_value)
        else:
            raise ValueError("sync summary.inventory must be a dict")

        collection_value = summary_dict.get("collection")
        if collection_value is None:
            collection_summary = cast("CollectionSummary", {})
        elif isinstance(collection_value, dict):
            collection_summary = cast("CollectionSummary", collection_value)
        else:
            raise ValueError("sync summary.collection must be a dict")

        stats = SyncItemStats(
            items_created=inventory_summary.get("created", 0),
            items_deleted=inventory_summary.get("deactivated", 0),
            items_updated=collection_summary.get("updated", 0),
            items_synced=(
                0 if collection_summary.get("status") == "skipped" else collection_summary.get("processed_records", 0)
            ),
        )

        sync_session_service.complete_instance_sync(
            record.id,
            stats=stats,
            sync_details={"version": 1, **cast(dict[str, Any], summary_dict)},
        )

        sync_logger.info(
            "实例账户同步完成",
            module="accounts_sync",
            phase="completed",
            operation="sync_accounts",
            session_id=session.session_id,
            instance_id=instance.id,
            instance_name=instance.name,
            inventory=cast("JsonDict", inventory_summary),
            collection=cast("JsonDict", collection_summary),
        )
        result = (1, 0)
    except ACCOUNT_TASK_EXCEPTIONS as exc:
        sync_session_service.fail_instance_sync(record.id, str(exc))
        sync_logger.exception(
            "实例账户同步异常",
            module="accounts_sync",
            phase="error",
            operation="sync_accounts",
            session_id=session.session_id,
            instance_id=instance.id,
            instance_name=instance.name,
            error=str(exc),
        )
        return 0, 1
    else:
        return result


def sync_accounts(
    *,
    manual_run: bool = False,
    created_by: int | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    **_: object,
) -> None:
    """同步账户任务 - 同步所有实例的账户信息.

    遍历所有启用的数据库实例,同步账户清单和权限信息.
    创建同步会话记录,跟踪每个实例的同步状态和结果.

    Args:
        manual_run: 是否为手动触发,默认 False(定时任务).
        created_by: 触发用户 ID,手动触发时必填.
        run_id: 可选的 TaskRun.run_id. 传入时复用既有 TaskRun,否则创建新的 TaskRun.
        session_id: 可选的会话 ID.传入时优先复用该会话.
        **_: 其他可选参数,由调度器传入但不使用.

    Returns:
        None

    Raises:
        Exception: 当任务执行失败时抛出.

    """
    # 直接创建应用实例,确保后台线程有干净的应用上下文
    app = create_app(init_scheduler_on_start=False)
    with app.app_context():
        sync_logger = get_sync_logger()
        task_runs_service = TaskRunsWriteService()

        resolved_run_id = _resolve_run_id(
            task_runs_service=task_runs_service,
            manual_run=manual_run,
            created_by=created_by,
            run_id=run_id,
        )

        session: SyncSession | None = None
        instances: list[Instance] = []
        try:
            if _is_cancelled(resolved_run_id):
                sync_logger.info(
                    "任务已取消,跳过执行",
                    module="accounts_sync",
                    phase="start",
                    operation="sync_accounts",
                    run_id=resolved_run_id,
                )
                return

            instances = AccountsSyncTaskService().list_active_instances()

            if not instances:
                sync_logger.info(
                    "没有找到启用的数据库实例",
                    module="accounts_sync",
                    phase="start",
                    operation="sync_accounts",
                    run_id=resolved_run_id,
                )
                _finalize_no_instances(
                    task_runs_service=task_runs_service,
                    run_id=resolved_run_id,
                    manual_run=manual_run,
                )
                return

            sync_logger.info(
                "开始同步账户信息",
                module="accounts_sync",
                phase="start",
                operation="sync_accounts",
                instance_count=len(instances),
                manual_run=manual_run,
                created_by=created_by,
                run_id=resolved_run_id,
            )

            _init_items(task_runs_service=task_runs_service, run_id=resolved_run_id, instances=instances)
            session = _resolve_session(manual_run=manual_run, created_by=created_by, session_id=session_id)
            records = _create_records(session=session, instances=instances)

            totals = _sync_instances(
                sync_logger=sync_logger,
                task_runs_service=task_runs_service,
                run_id=resolved_run_id,
                session=session,
                instances=instances,
                records=records,
            )

            _finalize_success(
                sync_logger=sync_logger,
                task_runs_service=task_runs_service,
                run_id=resolved_run_id,
                manual_run=manual_run,
                session=session,
                instances=instances,
                totals=totals,
            )

        except ACCOUNT_TASK_EXCEPTIONS as exc:
            _finalize_failure(
                sync_logger=sync_logger,
                task_runs_service=task_runs_service,
                run_id=resolved_run_id,
                session=session,
                instances=instances,
                exc=exc,
            )
            raise
