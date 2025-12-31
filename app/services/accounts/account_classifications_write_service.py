"""账户分类管理 write API Service.

职责:
- 编排账户分类/规则/分配的写操作
- 调用 repository 执行 add/delete/flush
- 不返回 Response、不 commit
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.constants import DatabaseType
from app.constants.colors import ThemeColors
from app.errors import DatabaseError, NotFoundError, ValidationError
from app.forms.definitions.account_classification_constants import ICON_OPTIONS, RISK_LEVEL_OPTIONS
from app.forms.definitions.account_classification_rule_constants import OPERATOR_OPTIONS
from app.models.account_classification import (
    AccountClassification,
    AccountClassificationAssignment,
    ClassificationRule,
)
from app.repositories.accounts_classifications_repository import AccountsClassificationsRepository
from app.services.account_classification.dsl_v4 import collect_dsl_v4_validation_errors, is_dsl_v4_expression
from app.services.account_classification.orchestrator import CACHE_INVALIDATION_EXCEPTIONS, AccountClassificationService
from app.types.converters import as_bool, as_int, as_optional_str, as_str
from app.utils.structlog_config import log_info


@dataclass(slots=True)
class AccountClassificationDeleteOutcome:
    classification_id: int
    classification_name: str


@dataclass(slots=True)
class ClassificationRuleDeleteOutcome:
    rule_id: int
    rule_name: str


@dataclass(slots=True)
class AccountClassificationAssignmentDeactivateOutcome:
    assignment_id: int
    account_id: int
    classification_id: int


class AccountClassificationsWriteService:
    """账户分类管理写操作服务."""

    def __init__(self, repository: AccountsClassificationsRepository | None = None) -> None:
        self._repository = repository or AccountsClassificationsRepository()

    def create_classification(
        self,
        payload: dict[str, object] | None,
        *,
        operator_id: int | None = None,
    ) -> AccountClassification:
        normalized = self._validate_and_normalize_classification(payload or {}, resource=None)

        classification = AccountClassification(
            name=cast(str, normalized["name"]),
            description=cast(str, normalized["description"]),
            risk_level=cast(str, normalized["risk_level"]),
            color=cast(str, normalized["color"]),
            icon_name=cast(str, normalized["icon_name"]),
            priority=cast(int, normalized["priority"]),
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
        payload: dict[str, object] | None,
        *,
        operator_id: int | None = None,
    ) -> AccountClassification:
        normalized = self._validate_and_normalize_classification(payload or {}, resource=classification)

        classification.name = cast(str, normalized["name"])
        classification.description = cast(str, normalized["description"])
        classification.risk_level = cast(str, normalized["risk_level"])
        classification.color = cast(str, normalized["color"])
        classification.icon_name = cast(str, normalized["icon_name"])
        classification.priority = cast(int, normalized["priority"])

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
        payload: dict[str, object] | None,
        *,
        operator_id: int | None = None,
    ) -> ClassificationRule:
        normalized = self._validate_and_normalize_rule(payload or {}, resource=None)
        rule = ClassificationRule(
            classification_id=cast(int, normalized["classification_id"]),
            db_type=cast(str, normalized["db_type"]),
            rule_name=cast(str, normalized["rule_name"]),
            rule_expression=cast(str, normalized["rule_expression"]),
            is_active=cast(bool, normalized["is_active"]),
        )
        rule.operator = cast(str, normalized["operator"])

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
        payload: dict[str, object] | None,
        *,
        operator_id: int | None = None,
    ) -> ClassificationRule:
        normalized = self._validate_and_normalize_rule(payload or {}, resource=rule)

        rule.rule_name = cast(str, normalized["rule_name"])
        rule.classification_id = cast(int, normalized["classification_id"])
        rule.db_type = cast(str, normalized["db_type"])
        rule.operator = cast(str, normalized["operator"])
        rule.rule_expression = cast(str, normalized["rule_expression"])
        rule.is_active = cast(bool, normalized["is_active"])

        try:
            self._repository.add_rule(rule)
        except SQLAlchemyError as exc:
            raise DatabaseError(
                "更新分类规则失败",
                extra={"exception": str(exc), "rule_id": rule.id},
            ) from exc

        self._invalidate_cache(rule_id=rule.id)
        log_info(
            "分类规则保存成功",
            module="account_classification",
            rule_id=rule.id,
            operator_id=operator_id,
        )
        return rule

    def delete_classification(
        self,
        classification: AccountClassification,
        *,
        operator_id: int | None = None,
    ) -> AccountClassificationDeleteOutcome:
        outcome = AccountClassificationDeleteOutcome(
            classification_id=classification.id,
            classification_name=classification.name,
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

    @staticmethod
    def _parse_priority(raw_value: object, default: int) -> int:
        candidate = as_int(raw_value, default=default)
        if candidate is None:
            raise ValidationError("优先级必须为整数")
        return max(0, min(int(candidate), 100))

    @staticmethod
    def _is_valid_option(value: str, options: list[dict[str, str]]) -> bool:
        return any(item["value"] == value for item in options)

    def _name_exists(self, name: str, resource: AccountClassification | None) -> bool:
        query = AccountClassification.query.filter(AccountClassification.name == name)
        if resource:
            query = query.filter(AccountClassification.id != resource.id)
        return bool(db.session.query(query.exists()).scalar())

    def _validate_and_normalize_classification(
        self,
        data: dict[str, object],
        *,
        resource: AccountClassification | None,
    ) -> dict[str, object]:
        name = as_str(data.get("name"), default=(resource.name if resource else "")).strip()
        if not name:
            raise ValidationError("分类名称不能为空")

        color_key = as_str(data.get("color"), default=(resource.color if resource else "info")).strip()
        if not ThemeColors.is_valid_color(color_key):
            raise ValidationError("无效的颜色选择")

        description_value = as_str(data.get("description"), default=(resource.description if resource else "")).strip()
        risk_level_value = as_str(data.get("risk_level"), default=(resource.risk_level if resource else "medium"))
        icon_name_value = as_str(data.get("icon_name"), default=(resource.icon_name if resource else "fa-tag"))
        priority_value = self._parse_priority(data.get("priority"), resource.priority if resource else 0)

        if not self._is_valid_option(risk_level_value, RISK_LEVEL_OPTIONS):
            raise ValidationError("风险等级取值无效")
        if not self._is_valid_option(icon_name_value, ICON_OPTIONS):
            raise ValidationError("图标取值无效")
        if self._name_exists(name, resource):
            raise ValidationError("分类名称已存在", message_key="NAME_EXISTS")

        return {
            "name": name,
            "description": description_value,
            "risk_level": risk_level_value,
            "color": color_key,
            "icon_name": icon_name_value,
            "priority": priority_value,
        }

    def _get_classification_by_id(self, classification_id: int) -> AccountClassification:
        classification = AccountClassification.query.get(classification_id)
        if not classification:
            raise NotFoundError("选择的分类不存在", extra={"classification_id": classification_id})
        return classification

    def _get_db_type_options(self) -> list[dict[str, str]]:
        return [
            {"value": db_type, "label": DatabaseType.get_display_name(db_type)} for db_type in DatabaseType.RELATIONAL
        ]

    def _validate_and_normalize_rule(
        self,
        data: dict[str, object],
        *,
        resource: ClassificationRule | None,
    ) -> dict[str, object]:
        required_fields = ["rule_name", "classification_id", "db_type", "operator"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            raise ValidationError(f"缺少必填字段: {', '.join(missing)}")

        classification_id = as_int(data.get("classification_id"))
        if classification_id is None:
            raise ValidationError("选择的分类不存在")
        classification = self._get_classification_by_id(classification_id)

        db_type_value_raw = as_optional_str(data.get("db_type"))
        db_type_value = DatabaseType.normalize(db_type_value_raw) if db_type_value_raw else None
        if not db_type_value or not self._is_valid_option(db_type_value, self._get_db_type_options()):
            raise ValidationError("数据库类型取值无效")

        operator_value = as_optional_str(data.get("operator"))
        if not operator_value or not self._is_valid_option(operator_value, OPERATOR_OPTIONS):
            raise ValidationError("匹配逻辑取值无效")

        normalized_expression = self._normalize_expression(
            data.get("rule_expression"),
            fallback=(resource.rule_expression if resource else "{}"),
        )

        normalized = {
            "rule_name": as_str(data.get("rule_name"), default="").strip(),
            "classification_id": classification.id,
            "db_type": db_type_value,
            "operator": operator_value,
            "rule_expression": normalized_expression,
            "is_active": as_bool(data.get("is_active"), default=True),
        }

        if self._rule_name_exists(
            classification_id=classification.id,
            db_type=db_type_value,
            rule_name=cast(str, normalized["rule_name"]),
            resource=resource,
        ):
            raise ValidationError("同一数据库类型下规则名称重复", message_key="NAME_EXISTS")

        if self._expression_exists(
            normalized_expression,
            classification_id=classification.id,
            resource=resource,
        ):
            raise ValidationError("规则表达式重复", message_key="EXPRESSION_DUPLICATED")

        try:
            parsed_expression = json.loads(normalized_expression)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValidationError(f"规则表达式格式错误: {exc}") from exc

        if is_dsl_v4_expression(parsed_expression):
            errors = collect_dsl_v4_validation_errors(parsed_expression)
            if errors:
                raise ValidationError(
                    "DSL v4 规则表达式校验失败",
                    message_key="INVALID_DSL_EXPRESSION",
                    extra={"errors": errors},
                )

        return normalized

    @staticmethod
    def _normalize_expression(expression: object, *, fallback: str) -> str:
        raw_value = expression
        if raw_value is None:
            raw_value = fallback
        if isinstance(raw_value, str) and not raw_value.strip():
            raw_value = fallback
        try:
            parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"规则表达式格式错误: {exc}") from exc
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict):
            raise ValidationError("规则表达式必须为对象")
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _rule_name_exists(
        *,
        classification_id: int,
        db_type: str,
        rule_name: str,
        resource: ClassificationRule | None,
    ) -> bool:
        query = ClassificationRule.query.filter_by(
            classification_id=classification_id,
            db_type=db_type,
            rule_name=rule_name,
        )
        if resource:
            query = query.filter(ClassificationRule.id != resource.id)
        return bool(db.session.query(query.exists()).scalar())

    @staticmethod
    def _expression_exists(
        normalized_expression: str,
        *,
        classification_id: int,
        resource: ClassificationRule | None,
    ) -> bool:
        query = ClassificationRule.query.filter_by(
            classification_id=classification_id,
            rule_expression=normalized_expression,
        )
        if resource:
            query = query.filter(ClassificationRule.id != resource.id)
        return bool(db.session.query(query.exists()).scalar())

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
