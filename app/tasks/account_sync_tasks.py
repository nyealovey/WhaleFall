"""
账户同步相关定时任务
"""

from typing import Any

from app import create_app, db
from app.constants.sync_constants import SyncCategory, SyncOperationType
from app.constants import SyncStatus, TaskStatus
from app.models.instance import Instance
from app.services.account_sync import account_sync_service
from app.services.sync_session_service import sync_session_service
from app.utils.structlog_config import get_sync_logger
from app.utils.time_utils import time_utils


def sync_accounts(**kwargs: Any) -> None:  # noqa: ANN401
    """同步账户任务 - 同步所有实例的账户信息"""
    sync_logger = get_sync_logger()

    app = create_app()
    with app.app_context():
        try:
            instances = Instance.query.filter_by(is_active=True).all()

            if not instances:
                sync_logger.info("没有找到启用的数据库实例")
                return

            sync_logger.info("开始同步 %s 个实例的账户信息", len(instances))

            total_synced = 0
            total_failed = 0

            session = sync_session_service.create_session(
                sync_type=SyncOperationType.SCHEDULED_TASK.value,
                sync_category=SyncCategory.ACCOUNT.value,
                created_by=None,
            )

            instance_ids = [inst.id for inst in instances]
            records = sync_session_service.add_instance_records(session.session_id, instance_ids)
            session.total_instances = len(instances)

            for i, instance in enumerate(instances):
                record = records[i] if i < len(records) else None
                if not record:
                    continue

                try:
                    sync_session_service.start_instance_sync(record.id)

                    result = account_sync_service.sync_accounts(
                        instance,
                        sync_type=SyncOperationType.SCHEDULED_TASK.value,
                        session_id=session.session_id,
                    )

                    if result.get("success", False):
                        total_synced += 1

                        details = result.get("details", {})
                        inventory = details.get("inventory", {})
                        permissions = details.get("permissions", {})
                        sync_session_service.complete_instance_sync(
                            record.id,
                            items_synced=permissions.get("updated", 0) + permissions.get("created", 0),
                            items_created=inventory.get("created", 0),
                            items_updated=permissions.get("updated", 0),
                            items_deleted=inventory.get("deactivated", 0),
                            sync_details=details,
                        )

                        sync_logger.info(
                            "实例 %s 同步成功",
                            instance.name,
                            instance_id=instance.id,
                            session_id=session.session_id,
                            synced_count=result.get("synced_count", 0),
                        )
                    else:
                        total_failed += 1

                        sync_session_service.fail_instance_sync(
                            record.id,
                            result.get("error", "未知错误"),
                        )

                        sync_logger.error(
                            "实例 %s 同步失败",
                            instance.name,
                            instance_id=instance.id,
                            session_id=session.session_id,
                            error=result.get("error", "未知错误"),
                        )

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
