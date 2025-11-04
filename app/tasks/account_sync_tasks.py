"""
账户同步相关定时任务
"""

from typing import Any

from app import create_app, db
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.constants import SyncStatus, TaskStatus
from app.models.instance import Instance
from app.services.account_sync.coordinator import AccountSyncCoordinator
from app.services.sync_session_service import sync_session_service
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def sync_accounts(manual_run: bool = False, created_by: int | None = None, **kwargs: Any) -> None:  # noqa: ANN401
    """同步账户任务 - 同步所有实例的账户信息"""
    sync_logger = get_sync_logger()

    app = create_app()
    with app.app_context():
        try:
            instances = Instance.query.filter_by(is_active=True).all()

            if not instances:
                sync_logger.info("没有找到启用的数据库实例")
                return

            sync_logger.info(
                "开始同步账户信息",
                module="account_sync_task",
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

                try:
                    sync_session_service.start_instance_sync(record.id)

                    coordinator = AccountSyncCoordinator(instance)

                    try:
                        if not coordinator.connect():
                            error_msg = f"无法获取数据库连接"
                            sync_session_service.fail_instance_sync(record.id, error_msg)
                            sync_logger.error(
                                "实例 %s 同步失败：无法建立连接",
                                instance.name,
                                instance_id=instance.id,
                                session_id=session.session_id,
                                error=error_msg,
                            )
                            total_failed += 1
                            continue

                        temp_session_id = f"{session.session_id}_{instance.id}"
                        summary = coordinator.sync_all(session_id=temp_session_id)

                        inventory = summary.get("inventory", {})
                        permissions = summary.get("permissions", {})

                        sync_session_service.complete_instance_sync(
                            record.id,
                            items_synced=permissions.get("updated", 0) + permissions.get("created", 0),
                            items_created=inventory.get("created", 0),
                            items_updated=permissions.get("updated", 0),
                            items_deleted=inventory.get("deactivated", 0),
                            sync_details=summary,
                        )

                        total_synced += 1

                        sync_logger.info(
                            "实例 %s 同步成功",
                            instance.name,
                            instance_id=instance.id,
                            session_id=session.session_id,
                            inventory=inventory,
                            permissions=permissions,
                        )

                    finally:
                        coordinator.disconnect()

                except Exception as exc:  # noqa: BLE001
                    total_failed += 1

                    sync_session_service.fail_instance_sync(record.id, str(exc))

                    sync_logger.error(
                        "实例 %s 同步异常",
                        instance.name,
                        instance_id=instance.id,
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
                error=str(exc),
                exc_info=True,
            )
            raise
