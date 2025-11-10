from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Sequence

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.errors import SystemError, ValidationError
from app.models.account_change_log import AccountChangeLog
from app.models.account_classification import AccountClassificationAssignment
from app.models.account_permission import AccountPermission
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.instance_database import InstanceDatabase
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.tag import instance_tags
from app.utils.data_validator import DataValidator
from app.utils.structlog_config import log_error, log_info


def _init_deletion_stats() -> Dict[str, int]:
    return {
        "deleted_assignments": 0,
        "deleted_account_permissions": 0,
        "deleted_sync_records": 0,
        "deleted_change_logs": 0,
        "deleted_instance_accounts": 0,
        "deleted_instance_databases": 0,
        "deleted_instance_size_stats": 0,
        "deleted_instance_size_aggregations": 0,
        "deleted_database_size_stats": 0,
        "deleted_database_size_aggregations": 0,
        "deleted_tag_links": 0,
    }


class InstanceBatchCreationService:
    """负责批量创建实例的服务。"""

    def create_instances(
        self,
        instances_data: List[Dict[str, Any]],
        *,
        operator_id: int | None = None,
    ) -> Dict[str, Any]:
        if not instances_data:
            raise ValidationError("请提供实例数据")

        valid_data, validation_errors = DataValidator.validate_batch_data(instances_data)
        errors: List[str] = list(validation_errors)

        # 检查 payload 内部是否存在重复名称
        name_counter = Counter(
            (item.get("name") or "").strip()
            for item in valid_data
            if item.get("name")
        )
        duplicate_names = sorted({name for name, count in name_counter.items() if name and count > 1})
        if duplicate_names:
            errors.append(f"存在重复实例名称: {', '.join(duplicate_names)}")

        # 查询数据库中已存在的实例名称，避免重复插入
        payload_names = [
            item.get("name")
            for item in valid_data
            if item.get("name") and item.get("name") not in duplicate_names
        ]
        existing_names: set[str] = set()
        if payload_names:
            existing_names = {
                row[0]
                for row in db.session.execute(
                    select(Instance.name).where(Instance.name.in_(payload_names))
                )
            }
            if existing_names:
                errors.append(f"以下实例名称已存在: {', '.join(sorted(existing_names))}")

        created_count = 0

        try:
            for index, payload in enumerate(valid_data, start=1):
                name = payload.get("name")
                if not name or name in duplicate_names or name in existing_names:
                    continue

                try:
                    instance = self._build_instance_from_payload(payload)
                except ValidationError as exc:
                    errors.append(f"第 {index} 个实例数据无效: {exc}")
                    continue

                db.session.add(instance)
                created_count += 1
                log_info(
                    "batch_create_instance",
                    module="instances",
                    operator_id=operator_id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                )

            if created_count == 0:
                db.session.rollback()
            else:
                db.session.commit()

            message = f"成功创建 {created_count} 个实例"
            if not errors:
                errors = []

            return {
                "created_count": created_count,
                "errors": errors,
                "duplicate_names": duplicate_names,
                "skipped_existing_names": sorted(existing_names),
                "message": message,
            }
        except SQLAlchemyError as exc:
            db.session.rollback()
            log_error("batch_create_instance_failed", module="instances", error=str(exc))
            raise SystemError("批量创建实例失败") from exc

    @staticmethod
    def _build_instance_from_payload(payload: Dict[str, Any]) -> Instance:
        try:
            port = int(payload["port"])
        except (TypeError, ValueError, KeyError) as exc:
            raise ValidationError(f"无效的端口号: {payload.get('port')}") from exc

        credential_id = None
        if payload.get("credential_id"):
            try:
                credential_id = int(payload["credential_id"])
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"无效的凭据ID: {payload.get('credential_id')}") from exc

        instance = Instance(
            name=payload["name"],
            db_type=payload["db_type"],
            host=payload["host"],
            port=port,
            database_name=payload.get("database_name"),
            description=payload.get("description"),
            credential_id=credential_id,
            tags=[],
        )
        return instance


class InstanceBatchDeletionService:
    """负责批量删除实例及其关联数据的服务。"""

    def delete_instances(
        self,
        instance_ids: Sequence[int],
        *,
        operator_id: int | None = None,
    ) -> Dict[str, Any]:
        if not instance_ids:
            raise ValidationError("请选择要删除的实例")

        try:
            unique_ids = sorted({int(i) for i in instance_ids})
        except (TypeError, ValueError) as exc:
            raise ValidationError("实例ID列表无效") from exc
        instances = Instance.query.filter(Instance.id.in_(unique_ids)).all()
        found_ids = {instance.id for instance in instances}
        missing_ids = [instance_id for instance_id in unique_ids if instance_id not in found_ids]

        stats = _init_deletion_stats()
        deleted_count = 0

        try:
            for instance in instances:
                per_stats = self._delete_single_instance(instance)
                for key, value in per_stats.items():
                    stats[key] += value

                db.session.delete(instance)
                deleted_count += 1

                log_info(
                    "batch_delete_instance",
                    module="instances",
                    operator_id=operator_id,
                    instance_id=instance.id,
                    instance_name=instance.name,
                    db_type=instance.db_type,
                    host=instance.host,
                )

            if deleted_count == 0:
                db.session.rollback()
            else:
                db.session.commit()

            stats["deleted_count"] = deleted_count
            stats["missing_instance_ids"] = missing_ids
            stats["deleted_sync_data"] = stats["deleted_account_permissions"]

            return stats
        except SQLAlchemyError as exc:
            db.session.rollback()
            log_error("batch_delete_instance_failed", module="instances", error=str(exc))
            raise SystemError("批量删除实例失败") from exc

    def _delete_single_instance(self, instance: Instance) -> Dict[str, int]:
        stats = _init_deletion_stats()

        account_ids_subquery = (
            select(AccountPermission.id).where(AccountPermission.instance_id == instance.id)
        ).subquery()

        stats["deleted_assignments"] += AccountClassificationAssignment.query.filter(
            AccountClassificationAssignment.account_id.in_(account_ids_subquery)
        ).delete(synchronize_session=False)

        stats["deleted_account_permissions"] += AccountPermission.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        stats["deleted_sync_records"] += SyncInstanceRecord.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        stats["deleted_change_logs"] += AccountChangeLog.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        stats["deleted_instance_accounts"] += InstanceAccount.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        stats["deleted_instance_databases"] += InstanceDatabase.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        stats["deleted_instance_size_stats"] += InstanceSizeStat.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        stats["deleted_instance_size_aggregations"] += InstanceSizeAggregation.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        stats["deleted_database_size_stats"] += DatabaseSizeStat.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        stats["deleted_database_size_aggregations"] += DatabaseSizeAggregation.query.filter_by(
            instance_id=instance.id
        ).delete(synchronize_session=False)

        tag_delete_result = db.session.execute(
            instance_tags.delete().where(instance_tags.c.instance_id == instance.id)
        )
        stats["deleted_tag_links"] += tag_delete_result.rowcount or 0

        return stats
