"""账户分类管理相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass

from app.types.classification import RuleExpression


@dataclass(slots=True)
class AccountClassificationListItem:
    """账户分类列表项."""

    id: int
    name: str
    description: str | None
    risk_level: str
    color: str
    color_key: str | None
    icon_name: str | None
    priority: int
    is_system: bool
    created_at: str | None
    updated_at: str | None
    rules_count: int


@dataclass(slots=True)
class AccountClassificationRuleListItem:
    """分类规则列表项."""

    id: int
    rule_name: str
    classification_id: int
    classification_name: str | None
    db_type: str
    rule_expression: RuleExpression
    is_active: bool
    created_at: str | None
    updated_at: str | None
    matched_accounts_count: int = 0


@dataclass(slots=True)
class AccountClassificationRuleFilterItem:
    """分类规则筛选列表项."""

    id: int
    rule_name: str
    classification_id: int
    classification_name: str | None
    db_type: str
    rule_expression: object
    is_active: bool
    created_at: str | None
    updated_at: str | None


@dataclass(slots=True)
class AccountClassificationRuleStatItem:
    """规则命中统计项."""

    rule_id: int
    matched_accounts_count: int


@dataclass(slots=True)
class AccountClassificationAssignmentItem:
    """账户分类分配记录项."""

    id: int
    account_id: int
    assigned_by: int | None
    classification_id: int
    classification_name: str
    assigned_at: str | None
