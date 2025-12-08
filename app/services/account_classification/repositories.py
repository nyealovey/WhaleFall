"""账户分类数据访问辅助工具。."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import joinedload

from app import db
from app.models.account_classification import (
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


class ClassificationRepository:
    """封装账户分类场景下的数据库访问。.

    提供账户分类相关的数据查询、清理和更新操作。
    负责规则查询、账户查询和分类分配管理。
    """

    def fetch_active_rules(self) -> list[ClassificationRule]:
        """获取所有启用的分类规则。.

        Returns:
            按创建时间排序的启用规则列表。

        """
        return (
            ClassificationRule.query.options(joinedload(ClassificationRule.classification))
            .filter_by(is_active=True)
            .order_by(ClassificationRule.created_at.asc())
            .all()
        )

    def fetch_accounts(self, instance_id: int | None = None) -> list[AccountPermission]:
        """获取需要分类的账户列表。.

        Args:
            instance_id: 可选的实例 ID，用于筛选特定实例的账户。

        Returns:
            符合条件的账户权限列表（仅活跃实例和账户）。

        """
        query = (
            AccountPermission.query.join(Instance)
            .join(InstanceAccount, AccountPermission.instance_account)
            .filter(
                Instance.is_active.is_(True),
                Instance.deleted_at.is_(None),
                InstanceAccount.is_active.is_(True),
            )
        )
        if instance_id:
            query = query.filter(AccountPermission.instance_id == instance_id)
        return query.all()

    def cleanup_all_assignments(self) -> int:
        """重新分类前清理所有既有分配关系。.

        删除所有现有的账户分类分配记录，为重新分类做准备。

        Returns:
            删除的记录数量。

        Raises:
            Exception: 当清理操作失败时抛出。

        """
        try:
            deleted = db.session.query(AccountClassificationAssignment).delete()
            if deleted:
                log_info(
                    "清理所有旧分配记录",
                    module="account_classification",
                    deleted_count=deleted,
                )
            db.session.commit()
            return deleted
        except Exception as exc:
            db.session.rollback()
            log_error("清理旧分配记录失败", module="account_classification", error=str(exc))
            raise

    def upsert_assignments(
        self,
        matched_accounts: Sequence[AccountPermission],
        classification_id: int,
        *,
        rule_id: int | None = None,
    ) -> int:
        """为指定账户集重新写入分类分配记录。.

        先删除现有的分配记录，然后批量插入新的分配记录。

        Args:
            matched_accounts: 匹配的账户列表。
            classification_id: 分类 ID。
            rule_id: 可选的规则 ID。

        Returns:
            插入的记录数量。

        Raises:
            Exception: 当操作失败时抛出。

        """
        if not matched_accounts:
            return 0

        account_ids = [account.id for account in matched_accounts]
        try:
            deleted_count = (
                db.session.query(AccountClassificationAssignment)
                .filter(
                    AccountClassificationAssignment.classification_id == classification_id,
                    AccountClassificationAssignment.account_id.in_(account_ids),
                )
                .delete(synchronize_session=False)
            )
            if deleted_count:
                log_info(
                    "清理分类旧分配记录",
                    module="account_classification",
                    classification_id=classification_id,
                    deleted_count=deleted_count,
                    account_ids=account_ids,
                )

            new_assignments = [
                {
                    "account_id": account.id,
                    "classification_id": classification_id,
                    "rule_id": rule_id,
                    "assigned_by": None,
                    "assignment_type": "auto",
                    "notes": None,
                    "is_active": True,
                    "created_at": time_utils.now(),
                    "updated_at": time_utils.now(),
                }
                for account in matched_accounts
            ]

            if new_assignments:
                db.session.bulk_insert_mappings(AccountClassificationAssignment, new_assignments)
                db.session.commit()

            return len(new_assignments)
        except Exception as exc:
            log_error(
                "批量写入分类分配失败",
                module="account_classification",
                error=str(exc),
                classification_id=classification_id,
            )
            db.session.rollback()
            return 0

    # --------- Cache serialization helpers ---------------------------------
    @staticmethod
    def serialize_rules(rules: Iterable[ClassificationRule]) -> list[dict]:
        """序列化规则模型以便写入缓存。.

        Args:
            rules: 数据库读取的规则对象列表。

        Returns:
            list[dict]: 仅包含缓存必要字段的轻量化字典列表。

        """
        payload: list[dict] = []
        for rule in rules:
            payload.append(
                {
                    "id": rule.id,
                    "classification_id": rule.classification_id,
                    "db_type": rule.db_type,
                    "rule_name": rule.rule_name,
                    "rule_expression": rule.rule_expression,
                    "is_active": rule.is_active,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None,
                    "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                },
            )
        return payload

    @staticmethod
    def hydrate_rules(rules_data: Iterable[dict]) -> list[ClassificationRule]:
        """从缓存字典还原规则模型。.

        Args:
            rules_data: 缓存中的规则字典集合。

        Returns:
            list[ClassificationRule]: 还原后的 `ClassificationRule` 对象列表。

        """
        hydrated: list[ClassificationRule] = []
        for data in rules_data:
            try:
                rule = ClassificationRule()
                rule.id = data.get("id")
                rule.classification_id = data.get("classification_id")
                rule.db_type = data.get("db_type")
                rule.rule_name = data.get("rule_name")
                rule.rule_expression = data.get("rule_expression")
                rule.is_active = data.get("is_active", True)
                hydrated.append(rule)
            except Exception as exc:
                log_error("反序列化规则缓存失败", module="account_classification", error=str(exc))
        return hydrated
