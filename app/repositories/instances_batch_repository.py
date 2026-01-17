"""实例批量操作 Repository.

职责:
- 封装批量创建/删除场景的 Query 与批量 delete/execute
- 不做业务编排、不返回 Response、不 commit
"""

from __future__ import annotations

from sqlalchemy import select

from app import db
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
from app.repositories.instances_repository import InstancesRepository


class InstancesBatchRepository:
    """实例批量操作 Repository."""

    @staticmethod
    def list_instances_by_ids(instance_ids: list[int]) -> list[Instance]:
        """按 ID 列表获取实例."""
        return InstancesRepository.list_instances_by_ids(instance_ids)

    @staticmethod
    def fetch_existing_instance_names(names: list[str]) -> set[str]:
        """查询已存在的实例名称集合."""
        resolved_names = names if names is not None else []
        normalized = [name for name in resolved_names if name]
        if not normalized:
            return set()
        rows = db.session.execute(select(Instance.name).where(Instance.name.in_(normalized))).all()
        return {row[0] for row in rows if row and row[0]}

    @staticmethod
    def delete_related_data_for_instance(*, instance_id: int) -> dict[str, int]:
        """删除实例关联数据并返回各类删除数量."""
        stats = {
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

        account_ids_subquery = (
            select(AccountPermission.id).where(AccountPermission.instance_id == instance_id).subquery()
        )

        stats["deleted_assignments"] += AccountClassificationAssignment.query.filter(
            AccountClassificationAssignment.account_id.in_(account_ids_subquery),
        ).delete(synchronize_session=False)

        stats["deleted_account_permissions"] += AccountPermission.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        stats["deleted_sync_records"] += SyncInstanceRecord.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        stats["deleted_change_logs"] += AccountChangeLog.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        stats["deleted_instance_accounts"] += InstanceAccount.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        stats["deleted_instance_databases"] += InstanceDatabase.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        stats["deleted_instance_size_stats"] += InstanceSizeStat.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        stats["deleted_instance_size_aggregations"] += InstanceSizeAggregation.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        stats["deleted_database_size_stats"] += DatabaseSizeStat.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        stats["deleted_database_size_aggregations"] += DatabaseSizeAggregation.query.filter_by(
            instance_id=instance_id,
        ).delete(synchronize_session=False)

        tag_delete_result = db.session.execute(
            instance_tags.delete().where(instance_tags.c.instance_id == instance_id),
        )
        rowcount_value = tag_delete_result.rowcount
        stats["deleted_tag_links"] += int(rowcount_value) if rowcount_value is not None else 0

        return stats

    @staticmethod
    def add_instance(instance: Instance) -> Instance:
        """新增实例(不 commit)."""
        db.session.add(instance)
        return instance

    @staticmethod
    def save_instance(instance: Instance) -> Instance:
        """保存实例变更(不 commit)."""
        db.session.add(instance)
        return instance

    @staticmethod
    def delete_instance(instance: Instance) -> None:
        """删除实例(不 commit)."""
        db.session.delete(instance)
