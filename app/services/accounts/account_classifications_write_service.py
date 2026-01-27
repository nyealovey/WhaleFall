"""账户分类管理 write API Service.

职责:
- 编排账户分类/规则/分配的写操作
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.core.exceptions import DatabaseError, NotFoundError, ValidationError
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.schemas.account_classifications import (
    AccountClassificationCreatePayload,
    AccountClassificationRuleCreatePayload,
    AccountClassificationRuleUpdatePayload,
    AccountClassificationUpdatePayload,
)
from app.schemas.validation import validate_or_raise
from app.services.account_classification.orchestrator import CACHE_INVALIDATION_EXCEPTIONS, AccountClassificationService
from app.utils.request_payload import parse_payload
from app.utils.structlog_config import log_info
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Mapping


def _normalize_expression(raw: str) -> str:
    """用于判断表达式/权限配置是否真实变化：忽略 key 顺序与空白差异."""
    parsed_json = json.loads(raw)
    if not isinstance(parsed_json, dict):
        return raw
    return json.dumps(parsed_json, ensure_ascii=False, sort_keys=True)


def _permission_config_changed(effective_expression: str, current_expression: str) -> bool:
    try:
        return _normalize_expression(effective_expression) != _normalize_expression(current_expression)
    except (TypeError, ValueError):
        # DB 中 rule_expression 理论上应当是合法 JSON；若异常，保守处理为“有变化”以避免误判。
        return True


@dataclass(slots=True)
class AccountClassificationDeleteOutcome:
    """账户分类删除结果."""

    classification_id: int
    classification_name: str


@dataclass(slots=True)
class ClassificationRuleDeleteOutcome:
    """分类规则删除结果."""

    rule_id: int
    rule_name: str


@dataclass(slots=True)
class AccountClassificationAssignmentDeactivateOutcome:
    """账户分类分配停用结果."""

    assignment_id: int
    account_id: int
    classification_id: int


class AccountClassificationsWriteService:
    """账户分类管理写操作服务."""

    def __init__(self, repository: AccountsClassificationsRepository | None = None) -> None:
        """初始化写操作服务."""
        self._repository = repository or AccountsClassificationsRepository()

    def get_classification_or_error(self, classification_id: int) -> AccountClassification:
        """获取账户分类(不存在则抛错)."""
        classification = self._repository.get_classification_by_id(classification_id)
        if classification is None:
            raise NotFoundError("账户分类不存在", extra={"classification_id": classification_id})
        return classification

    def get_rule_or_error(self, rule_id: int) -> ClassificationRule:
        """获取分类规则(不存在则抛错)."""
        rule = self._repository.get_rule_by_id(rule_id)
        if rule is None:
            raise NotFoundError("分类规则不存在", extra={"rule_id": rule_id})
        return rule

    def get_assignment_or_error(self, assignment_id: int) -> AccountClassificationAssignment:
        """获取分类分配记录(不存在则抛错)."""
        assignment = self._repository.get_assignment_by_id(assignment_id)
        if assignment is None:
            raise NotFoundError("分类分配不存在", extra={"assignment_id": assignment_id})
        return assignment

    def create_classification(
        self,
        payload: object | None,
        *,
        operator_id: int | None = None,
    ) -> AccountClassification:
        """创建账户分类."""
        sanitized = parse_payload(payload)
        parsed = validate_or_raise(AccountClassificationCreatePayload, sanitized)

        if self._code_exists(parsed.code, None):
            raise ValidationError("分类标识已存在", message_key="NAME_EXISTS")

        classification = AccountClassification(
            code=parsed.code,
            display_name=parsed.display_name,
            description=parsed.description,
            risk_level=parsed.risk_level,
            icon_name=parsed.icon_name,
            priority=parsed.priority,
        )

        try:
            self._repository.add_classification(classification)
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "创建账户分类失败",
                extra={"exception": str(exc)},
            ) from exc

        log_info(
            "创建账户分类成功",
            module="account_classification",
            classification_id=classification.id,
            operator_id=operator_id,
        )
        return classification

    def update_classification(
        self,
        classification: AccountClassification,
        payload: object | None,
        *,
        operator_id: int | None = None,
    ) -> AccountClassification:
        """更新账户分类."""
        sanitized = parse_payload(payload)
        parsed = validate_or_raise(AccountClassificationUpdatePayload, sanitized)

        if classification.is_system:
            forbidden_fields = {"risk_level", "icon_name"}
            illegal = forbidden_fields.intersection(parsed.model_fields_set)
            if illegal:
                raise ValidationError("系统内置分类不允许修改风险等级或图标", message_key="FORBIDDEN")

        if "display_name" in parsed.model_fields_set and parsed.display_name is not None:
            classification.display_name = parsed.display_name

        if "description" in parsed.model_fields_set and parsed.description is not None:
            classification.description = parsed.description
        if not classification.is_system:
            if "risk_level" in parsed.model_fields_set and parsed.risk_level is not None:
                classification.risk_level = parsed.risk_level
            if "icon_name" in parsed.model_fields_set and parsed.icon_name is not None:
                classification.icon_name = parsed.icon_name
        if "priority" in parsed.model_fields_set and parsed.priority is not None:
            classification.priority = parsed.priority

        try:
            self._repository.add_classification(classification)
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "更新账户分类失败",
                extra={"exception": str(exc), "classification_id": classification.id},
            ) from exc

        log_info(
            "更新账户分类成功",
            module="account_classification",
            classification_id=classification.id,
            operator_id=operator_id,
        )
        return classification

    def create_rule(
        self,
        payload: Mapping[str, object] | None,
        *,
        operator_id: int | None = None,
    ) -> ClassificationRule:
        """创建分类规则."""
        raw_payload: Mapping[str, object] = payload if payload is not None else {}
        raw_expression = raw_payload.get("rule_expression") if "rule_expression" in raw_payload else None
        sanitized = parse_payload(raw_payload, boolean_fields_default_false=["is_active"])
        sanitized_payload: dict[str, object] = dict(sanitized)
        if "rule_expression" in raw_payload:
            sanitized_payload["rule_expression"] = raw_expression
        parsed = validate_or_raise(AccountClassificationRuleCreatePayload, sanitized_payload)

        classification = self._get_classification_by_id(parsed.classification_id)

        if self._rule_name_exists(
            classification_id=classification.id,
            db_type=parsed.db_type,
            rule_name=parsed.rule_name,
            resource=None,
        ):
            raise ValidationError("同一数据库类型下规则名称重复", message_key="NAME_EXISTS")

        if self._expression_exists(
            parsed.rule_expression,
            classification_id=classification.id,
            resource=None,
        ):
            raise ValidationError("规则表达式重复", message_key="EXPRESSION_DUPLICATED")

        rule = ClassificationRule(
            classification_id=classification.id,
            db_type=parsed.db_type,
            rule_name=parsed.rule_name,
            rule_expression=parsed.rule_expression,
            rule_group_id=str(uuid4()),
            rule_version=1,
            is_active=parsed.is_active,
        )
        rule.operator = parsed.operator

        try:
            self._repository.add_rule(rule)
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "创建分类规则失败",
                extra={"exception": str(exc)},
            ) from exc

        self._invalidate_cache(rule_id=rule.id)
        log_info(
            "分类规则保存成功",
            module="account_classification",
            rule_id=rule.id,
            operator_id=operator_id,
        )
        return rule

    def update_rule(
        self,
        rule: ClassificationRule,
        payload: Mapping[str, object] | None,
        *,
        operator_id: int | None = None,
    ) -> ClassificationRule:
        """更新分类规则."""
        raw_payload: Mapping[str, object] = payload if payload is not None else {}
        raw_expression = raw_payload.get("rule_expression") if "rule_expression" in raw_payload else None
        sanitized = parse_payload(raw_payload, boolean_fields_default_false=["is_active"])
        sanitized_payload: dict[str, object] = dict(sanitized)
        if "rule_expression" in raw_payload:
            sanitized_payload["rule_expression"] = raw_expression
        parsed = validate_or_raise(AccountClassificationRuleUpdatePayload, sanitized_payload)

        # 编辑规则时不允许调整“分类 / 数据库类型”（需要重新创建规则）
        if parsed.classification_id != rule.classification_id:
            raise ValidationError("编辑分类规则时不允许修改分类", message_key="FORBIDDEN")
        if parsed.db_type != rule.db_type:
            raise ValidationError("编辑分类规则时不允许修改数据库类型", message_key="FORBIDDEN")

        classification = self._get_classification_by_id(rule.classification_id)

        effective_expression = (
            parsed.rule_expression
            if "rule_expression" in parsed.model_fields_set and parsed.rule_expression is not None
            else rule.rule_expression
        )

        if self._rule_name_exists(
            classification_id=classification.id,
            db_type=rule.db_type,
            rule_name=parsed.rule_name,
            resource=rule,
        ):
            raise ValidationError("同一数据库类型下规则名称重复", message_key="NAME_EXISTS")

        if self._expression_exists(
            effective_expression,
            classification_id=classification.id,
            resource=rule,
        ):
            raise ValidationError("规则表达式重复", message_key="EXPRESSION_DUPLICATED")
        permission_config_changed = _permission_config_changed(effective_expression, rule.rule_expression)

        # 仅当“匹配逻辑 / 权限配置”发生变化时才创建新版本；规则名称允许原地更新
        if not permission_config_changed:
            rule.rule_name = parsed.rule_name
            rule.operator = parsed.operator
            if "is_active" in parsed.model_fields_set and parsed.is_active is not None:
                rule.is_active = parsed.is_active

            try:
                self._repository.add_rule(rule)
            except SQLAlchemyError as exc:
                raise DatabaseError(
                    "更新分类规则失败",
                    extra={"exception": str(exc), "rule_id": getattr(rule, "id", None)},
                ) from exc

            self._invalidate_cache(rule_id=rule.id)
            log_info(
                "分类规则更新成功",
                module="account_classification",
                rule_id=rule.id,
                operator_id=operator_id,
            )
            return rule

        # 权限配置发生变化：创建新版本，并归档旧版本
        current_group_id = getattr(rule, "rule_group_id", None) or str(uuid4())
        current_version = int(getattr(rule, "rule_version", 1) or 1)

        new_is_active = (
            parsed.is_active
            if "is_active" in parsed.model_fields_set and parsed.is_active is not None
            else bool(rule.is_active)
        )

        new_rule = ClassificationRule(
            classification_id=classification.id,
            db_type=rule.db_type,
            rule_name=parsed.rule_name,
            rule_expression=effective_expression,
            rule_group_id=current_group_id,
            rule_version=current_version + 1,
            is_active=new_is_active,
        )
        new_rule.operator = parsed.operator

        # 旧版本归档
        rule.is_active = False
        rule.superseded_at = time_utils.now()

        try:
            self._repository.add_rule(rule)
            self._repository.add_rule(new_rule)
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "更新分类规则失败",
                extra={"exception": str(exc), "rule_id": getattr(rule, "id", None)},
            ) from exc

        self._invalidate_cache(rule_id=new_rule.id)
        log_info(
            "分类规则版本创建成功",
            module="account_classification",
            rule_id=new_rule.id,
            operator_id=operator_id,
            rule_group_id=current_group_id,
            rule_version=new_rule.rule_version,
        )
        return new_rule

    def delete_classification(
        self,
        classification: AccountClassification,
        *,
        operator_id: int | None = None,
    ) -> AccountClassificationDeleteOutcome:
        """删除账户分类."""
        outcome = AccountClassificationDeleteOutcome(
            classification_id=classification.id,
            classification_name=(getattr(classification, "display_name", None) or classification.code),
        )

        try:
            self._repository.delete_classification(classification)
            db.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "删除账户分类失败",
                extra={
                    "exception": str(exc),
                    "classification_id": classification.id,
                },
            ) from exc

        log_info(
            "删除账户分类成功",
            module="accounts_classifications",
            classification_id=outcome.classification_id,
            operator_id=operator_id,
        )
        return outcome

    def delete_rule(
        self,
        rule: ClassificationRule,
        *,
        operator_id: int | None = None,
    ) -> ClassificationRuleDeleteOutcome:
        """删除分类规则."""
        outcome = ClassificationRuleDeleteOutcome(rule_id=rule.id, rule_name=rule.rule_name)

        try:
            self._repository.delete_rule(rule)
            db.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "删除分类规则失败",
                extra={
                    "exception": str(exc),
                    "rule_id": rule.id,
                },
            ) from exc

        log_info(
            "删除分类规则成功",
            module="accounts_classifications",
            rule_id=outcome.rule_id,
            operator_id=operator_id,
        )
        return outcome

    def deactivate_assignment(
        self,
        assignment: AccountClassificationAssignment,
        *,
        operator_id: int | None = None,
    ) -> AccountClassificationAssignmentDeactivateOutcome:
        """停用分类分配."""
        assignment.is_active = False
        outcome = AccountClassificationAssignmentDeactivateOutcome(
            assignment_id=assignment.id,
            account_id=assignment.account_id,
            classification_id=assignment.classification_id,
        )

        try:
            self._repository.add_assignment(assignment)
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "移除分配失败",
                extra={
                    "exception": str(exc),
                    "assignment_id": assignment.id,
                },
            ) from exc

        log_info(
            "移除账户分类分配成功",
            module="accounts_classifications",
            assignment_id=outcome.assignment_id,
            operator_id=operator_id,
        )
        return outcome

    def _code_exists(self, code: str, resource: AccountClassification | None) -> bool:
        exclude_id = resource.id if resource else None
        return self._repository.exists_classification_code(code, exclude_classification_id=exclude_id)

    def _get_classification_by_id(self, classification_id: int) -> AccountClassification:
        classification = self._repository.get_classification_by_id(classification_id)
        if classification is None:
            raise NotFoundError("选择的分类不存在", extra={"classification_id": classification_id})
        return classification

    def _rule_name_exists(
        self,
        *,
        classification_id: int,
        db_type: str,
        rule_name: str,
        resource: ClassificationRule | None,
    ) -> bool:
        exclude_id = resource.id if resource else None
        return self._repository.exists_rule_name(
            classification_id=classification_id,
            db_type=db_type,
            rule_name=rule_name,
            exclude_rule_id=exclude_id,
        )

    def _expression_exists(
        self,
        normalized_expression: str,
        *,
        classification_id: int,
        resource: ClassificationRule | None,
    ) -> bool:
        exclude_id = resource.id if resource else None
        return self._repository.exists_rule_expression(
            classification_id=classification_id,
            rule_expression=normalized_expression,
            exclude_rule_id=exclude_id,
        )

    @staticmethod
    def _invalidate_cache(*, rule_id: int) -> None:
        try:
            AccountClassificationService().invalidate_cache()
        except CACHE_INVALIDATION_EXCEPTIONS as exc:
            log_info(
                "清除分类缓存失败",
                module="account_classification",
                rule_id=rule_id,
                error=str(exc),
            )
