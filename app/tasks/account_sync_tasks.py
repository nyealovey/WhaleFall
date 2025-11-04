"""
账户同步相关定时任务
"""

from typing import Any

from app import create_app, db
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.constants import SyncStatus, TaskStatus
from app.models.instance import Instance
from app.services.account_sync.coordinator import AccountSyncCoordinator
from app.services.account_sync.permission_manager import PermissionSyncError
from app.services.sync_session_service import sync_session_service
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def sync_accounts(manual_run: bool = False, created_by: int | None = None, **kwargs: Any) -> None:  # noqa: ANN401
    """同步账户任务 - 同步所有实例的账户信息"""
    app = create_app()
    with app.app_context():
        sync_logger = get_sync_logger()

        try:
            instances = Instance.query.filter_by(is_active=True).all()

            if not instances:
                sync_logger.info("没有找到启用的数据库实例", module="account_sync")
                return

            sync_logger.info(
                "开始同步账户信息",
                module="account_sync",
                instance_count=len(instances),
                manual_run=manual_run,
                created_by=created_by,
            )

            session = sync_session_service.create_session(
                sync_type=SyncOperationType.MANUAL_TASK.value if manual_run else SyncOperationType.SCHEDULED_TASK.value,
                sync_category=SyncCategory.ACCOUNT.value,
                created_by=created_by,
            )

            instance_ids = [inst.id for inst in instances]
            records = sync_session_service.add_instance_records(
                session.session_id,
                instance_ids,
                sync_category=SyncCategory.ACCOUNT.value,
            )
            session.total_instances = len(instances)

            total_synced = 0
            total_failed = 0

            for i, instance in enumerate(instances):
                record = records[i] if i < len(records) else None
                if not record:
                    continue

                instance_session_id = f"{session.session_id}_{instance.id}"

                try:
                    sync_session_service.start_instance_sync(record.id)

                    sync_logger.info(
                        "开始实例账户同步",
                        module="account_sync",
                        phase="inventory",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                    )

                    try:
                        with AccountSyncCoordinator(instance) as coordinator:
                            summary = coordinator.sync_all(session_id=instance_session_id)
                    except RuntimeError as connection_error:
                        error_message = str(connection_error) or "无法建立数据库连接"
                        sync_session_service.fail_instance_sync(record.id, error_message)
                        sync_logger.error(
                            "账户同步连接失败",
                            module="account_sync",
                            phase="connection",
                            session_id=session.session_id,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            error=error_message,
                        )
                        total_failed += 1
                        continue
                    except PermissionSyncError as permission_error:
                        sync_session_service.fail_instance_sync(record.id, str(permission_error), sync_details=permission_error.summary)
                        sync_logger.error(
                            "账户同步权限阶段失败",
                            module="account_sync",
                            phase="collection",
                            session_id=session.session_id,
                            instance_id=instance.id,
                            instance_name=instance.name,
                            errors=permission_error.summary.get("errors"),
                            error=str(permission_error),
                        )
                        total_failed += 1
                        continue

                    inventory_summary = summary.get("inventory", {}) or {}
                    collection_summary = summary.get("collection", {}) or {}

                    items_created = inventory_summary.get("created", 0)
                    items_deleted = inventory_summary.get("deactivated", 0)
                    items_updated = collection_summary.get("updated", 0)
                    items_synced = collection_summary.get("processed_records", 0)

                    if collection_summary.get("status") == "skipped":
                        items_synced = 0

                    sync_session_service.complete_instance_sync(
                        record.id,
                        items_synced=items_synced,
                        items_created=items_created,
                        items_updated=items_updated,
                        items_deleted=items_deleted,
                        sync_details=summary,
                    )

                    total_synced += 1

                    sync_logger.info(
                        "实例账户同步完成",
                        module="account_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        inventory=inventory_summary,
                        collection=collection_summary,
                    )

                except Exception as exc:  # noqa: BLE001
                    total_failed += 1

                    sync_session_service.fail_instance_sync(record.id, str(exc))

                    sync_logger.error(
                        "实例账户同步异常",
                        module="account_sync",
                        session_id=session.session_id,
                        instance_id=instance.id,
                        instance_name=instance.name,
                        error=str(exc),
                        exc_info=True,
                    )

            session.successful_instances = total_synced
            session.failed_instances = total_failed
            session.status = "completed" if total_failed == 0 else "failed"
            session.completed_at = time_utils.now()
            db.session.commit()

            sync_logger.info(
                "账户同步任务完成",
                module="account_sync",
                session_id=session.session_id,
                total_instances=len(instances),
                total_synced=total_synced,
                total_failed=total_failed,
            )

        except Exception as exc:  # noqa: BLE001
            if "session" in locals() and session:
                session.status = "failed"
                session.completed_at = time_utils.now()
                session.failed_instances = len(instances)
                db.session.commit()

            sync_logger.error(
                "账户同步任务失败",
                module="account_sync",
                error=str(exc),
                exc_info=True,
            )
            raise
