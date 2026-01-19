"""账户分类管理 read API Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import NoReturn

from app.core.exceptions import NotFoundError, SystemError
from app.core.types.accounts_classifications import (
    AccountClassificationAssignmentItem,
    AccountClassificationListItem,
    AccountClassificationRuleFilterItem,
    AccountClassificationRuleListItem,
    AccountClassificationRuleStatItem,
)
from app.models.account_classification import AccountClassification, ClassificationRule
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.utils.structlog_config import log_error

_MODULE = "accounts_classifications_read_service"


class AccountClassificationsReadService:
    """账户分类管理读取服务."""

    def __init__(self, repository: AccountsClassificationsRepository | None = None) -> None:
        """初始化读取服务."""
        self._repository = repository or AccountsClassificationsRepository()

    def _raise_system_error(self, message: str, exc: Exception) -> NoReturn:
        log_error(message, module=_MODULE, exception=exc)
        raise SystemError(message) from exc

    def get_classification_by_id(self, classification_id: int) -> AccountClassification | None:
        """按 ID 获取账户分类(可为空)."""
        try:
            return self._repository.get_classification_by_id(classification_id)
        except Exception as exc:
            self._raise_system_error("获取账户分类失败", exc)

    def get_rule_by_id(self, rule_id: int) -> ClassificationRule | None:
        """按 ID 获取分类规则(可为空)."""
        try:
            return self._repository.get_rule_by_id(rule_id)
        except Exception as exc:
            self._raise_system_error("获取分类规则失败", exc)

    def get_classification_or_error(self, classification_id: int) -> AccountClassification:
        """获取账户分类(不存在则抛错)."""
        classification = self.get_classification_by_id(classification_id)

        if classification is None:
            raise NotFoundError("账户分类不存在", extra={"classification_id": classification_id})
        return classification

    def get_rule_or_error(self, rule_id: int) -> ClassificationRule:
        """获取分类规则(不存在则抛错)."""
        rule = self.get_rule_by_id(rule_id)

        if rule is None:
            raise NotFoundError("分类规则不存在", extra={"rule_id": rule_id})
        return rule

    def get_classification_usage(self, classification_id: int) -> tuple[int, int]:
        """统计分类的规则/分配使用情况."""
        try:
            return self._repository.fetch_classification_usage(classification_id)
        except Exception as exc:
            self._raise_system_error("获取分类使用情况失败", exc)

    def list_classifications(self) -> list[AccountClassificationListItem]:
        """获取账户分类列表."""
        try:
            classifications = self._repository.fetch_active_classifications()
            rules_count_map = self._repository.fetch_rule_counts([item.id for item in classifications])
        except Exception as exc:
            self._raise_system_error("获取账户分类失败", exc)

        items: list[AccountClassificationListItem] = []
        for classification in classifications:
            display_name = getattr(classification, "display_name", None) or classification.name
            items.append(
                AccountClassificationListItem(
                    id=classification.id,
                    name=display_name,
                    code=classification.name,
                    display_name=display_name,
                    description=classification.description,
                    risk_level=classification.risk_level,
                    color=classification.color_value,
                    color_key=classification.color,
                    icon_name=classification.icon_name,
                    priority=classification.priority,
                    is_system=bool(classification.is_system),
                    created_at=classification.created_at.isoformat() if classification.created_at else None,
                    updated_at=classification.updated_at.isoformat() if classification.updated_at else None,
                    rules_count=rules_count_map.get(classification.id, 0),
                ),
            )
        return items

    def build_classification_detail(self, classification: AccountClassification) -> AccountClassificationListItem:
        """构建账户分类详情."""
        try:
            rules_count_map = self._repository.fetch_rule_counts([classification.id])
        except Exception as exc:
            self._raise_system_error("获取账户分类详情失败", exc)

        rules_count = rules_count_map.get(classification.id, 0)
        display_name = getattr(classification, "display_name", None) or classification.name
        return AccountClassificationListItem(
            id=classification.id,
            name=display_name,
            code=classification.name,
            display_name=display_name,
            description=classification.description,
            risk_level=classification.risk_level,
            color=classification.color_value,
            color_key=classification.color,
            icon_name=classification.icon_name,
            priority=classification.priority,
            is_system=bool(classification.is_system),
            created_at=classification.created_at.isoformat() if classification.created_at else None,
            updated_at=classification.updated_at.isoformat() if classification.updated_at else None,
            rules_count=rules_count,
        )

    def list_rules(self) -> list[AccountClassificationRuleListItem]:
        """获取分类规则列表."""
        try:
            rules = self._repository.fetch_active_rules()
        except Exception as exc:
            self._raise_system_error("获取规则列表失败", exc)

        items: list[AccountClassificationRuleListItem] = []
        for rule in rules:
            classification = rule.classification
            classification_name = (
                (getattr(classification, "display_name", None) or classification.name) if classification else None
            )
            items.append(
                AccountClassificationRuleListItem(
                    id=rule.id,
                    rule_name=rule.rule_name,
                    rule_group_id=rule.rule_group_id,
                    rule_version=rule.rule_version,
                    classification_id=rule.classification_id,
                    classification_name=classification_name,
                    db_type=rule.db_type,
                    rule_expression=rule.get_rule_expression(),
                    is_active=bool(rule.is_active),
                    created_at=rule.created_at.isoformat() if rule.created_at else None,
                    updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
                    matched_accounts_count=0,
                ),
            )
        return items

    def filter_rules(
        self,
        *,
        classification_id: int | None,
        db_type: str | None,
    ) -> list[AccountClassificationRuleFilterItem]:
        """筛选分类规则."""
        try:
            rules = self._repository.fetch_active_rules(classification_id=classification_id, db_type=db_type)
        except Exception as exc:
            self._raise_system_error("获取分类规则失败", exc)

        items: list[AccountClassificationRuleFilterItem] = []
        for rule in rules:
            classification = rule.classification
            classification_name = (
                (getattr(classification, "display_name", None) or classification.name) if classification else None
            )
            items.append(
                AccountClassificationRuleFilterItem(
                    id=rule.id,
                    rule_name=rule.rule_name,
                    rule_group_id=rule.rule_group_id,
                    rule_version=rule.rule_version,
                    classification_id=rule.classification_id,
                    classification_name=classification_name,
                    db_type=rule.db_type,
                    rule_expression=rule.rule_expression,
                    is_active=bool(rule.is_active),
                    created_at=rule.created_at.isoformat() if rule.created_at else None,
                    updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
                ),
            )
        return items

    def list_assignments(self) -> list[AccountClassificationAssignmentItem]:
        """获取账户分类分配列表."""
        try:
            assignments = self._repository.fetch_active_assignments()
        except Exception as exc:
            self._raise_system_error("获取账户分类分配失败", exc)

        items: list[AccountClassificationAssignmentItem] = []
        for assignment, classification in assignments:
            display_name = getattr(classification, "display_name", None) or classification.name
            items.append(
                AccountClassificationAssignmentItem(
                    id=assignment.id,
                    account_id=assignment.account_id,
                    assigned_by=assignment.assigned_by,
                    classification_id=assignment.classification_id,
                    classification_name=display_name,
                    assigned_at=(assignment.assigned_at.isoformat() if assignment.assigned_at else None),
                ),
            )
        return items

    def get_rule_stats(self, *, rule_ids: list[int] | None) -> list[AccountClassificationRuleStatItem]:
        """获取规则命中统计."""
        try:
            stats_map = self._repository.fetch_rule_match_stats(rule_ids)
        except Exception as exc:
            self._raise_system_error("获取规则命中统计失败", exc)

        return [
            AccountClassificationRuleStatItem(rule_id=rule_id, matched_accounts_count=count)
            for rule_id, count in stats_map.items()
        ]

    def get_permissions(self, db_type: str) -> dict[str, list[dict[str, str | None]]]:
        """获取数据库权限配置."""
        try:
            return self._repository.fetch_permissions_by_db_type(db_type)
        except Exception as exc:
            self._raise_system_error("获取数据库权限失败", exc)
