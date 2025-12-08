"""实例批量操作服务，集中处理创建/删除等事务。"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List
from collections.abc import Sequence

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


def _init_deletion_stats() -> dict[str, int]:
    """初始化删除统计字典。

    Returns:
        包含所有删除计数器的字典，初始值均为 0。

    """
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
    """负责批量创建实例的服务。

    提供批量创建实例的功能，包括数据校验、重复检查和批量插入。
    """

    def create_instances(
        self,
        instances_data: list[dict[str, Any]],
        *,
        operator_id: int | None = None,
    ) -> dict[str, Any]:
        """批量创建实例。

        校验实例数据，检查重复名称，批量插入数据库。

        Args:
            instances_data: 实例数据列表，每个元素包含实例的字段信息。
            operator_id: 操作者用户 ID，可选。

        Returns:
            包含创建结果的字典，格式如下：
            {
                'created_count': 3,
                'errors': [],
                'duplicate_names': [],
                'skipped_existing_names': [],
                'message': '成功创建 3 个实例'
            }

        Raises:
            ValidationError: 当实例数据为空时抛出。
            SystemError: 当数据库操作失败时抛出。

        """
        if not instances_data:
            raise ValidationError("请提供实例数据")

        valid_data, validation_errors = DataValidator.validate_batch_data(instances_data)
        errors: list[str] = list(validation_errors)

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
    def _build_instance_from_payload(payload: dict[str, Any]) -> Instance:
        """从数据字典构建实例对象。

        Args:
            payload: 实例数据字典。

        Returns:
            构建的 Instance 对象。

        Raises:
            ValidationError: 当端口号或凭据 ID 无效时抛出。

        """
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
    """负责批量删除实例及其关联数据的服务。

    提供批量删除实例的功能，包括级联删除所有关联数据。
    """

    def delete_instances(
        self,
        instance_ids: Sequence[int],
        *,
        operator_id: int | None = None,
    ) -> dict[str, Any]:
        """批量删除实例及其关联数据。

        删除指定的实例及其所有关联数据，包括账户权限、同步记录、
        容量统计、标签关联等。

        Args:
            instance_ids: 实例 ID 列表。
            operator_id: 操作者用户 ID，可选。

        Returns:
            包含删除统计的字典，格式如下：
            {
                'deleted_count': 2,
                'deleted_assignments': 10,
                'deleted_account_permissions': 50,
                'deleted_sync_records': 5,
                'deleted_change_logs': 20,
                'deleted_instance_accounts': 30,
                'deleted_instance_databases': 15,
                'deleted_instance_size_stats': 100,
                'deleted_instance_size_aggregations': 50,
                'deleted_database_size_stats': 200,
                'deleted_database_size_aggregations': 100,
                'deleted_tag_links': 5,
                'missing_instance_ids': [],
                'deleted_sync_data': 50
            }

        Raises:
            ValidationError: 当实例 ID 列表为空或无效时抛出。
            SystemError: 当数据库操作失败时抛出。

        """
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

    def _delete_single_instance(self, instance: Instance) -> dict[str, int]:
        """删除单个实例的所有关联数据。

        Args:
            instance: 要删除的实例对象。

        Returns:
            包含各类关联数据删除数量的字典。

        """
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
