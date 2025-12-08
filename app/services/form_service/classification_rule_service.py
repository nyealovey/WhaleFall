"""
账户分类规则表单服务
"""

from __future__ import annotations

import json
from typing import Any
from collections.abc import Mapping

from flask_login import current_user

from app import db
from app.forms.definitions.account_classification_rule_constants import DB_TYPE_OPTIONS, OPERATOR_OPTIONS
from app.models.account_classification import AccountClassification, ClassificationRule
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.services.account_classification.orchestrator import AccountClassificationService
from app.services.database_type_service import DatabaseTypeService


class ClassificationRuleFormService(BaseResourceService[ClassificationRule]):
    """分类规则创建/编辑。

    提供分类规则的表单校验、数据规范化和保存功能。

    Attributes:
        model: 关联的 ClassificationRule 模型类。

    """

    model = ClassificationRule

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """清理表单数据。

        Args:
            payload: 原始表单数据。

        Returns:
            清理后的数据字典。

        """
        return dict(payload or {})

    def validate(self, data: dict[str, Any], *, resource: ClassificationRule | None) -> ServiceResult[dict[str, Any]]:
        """校验分类规则数据。

        校验必填字段、分类存在性、数据库类型、匹配逻辑和规则表达式格式。

        Args:
            data: 清理后的数据。
            resource: 已存在的规则实例（编辑场景），创建时为 None。

        Returns:
            校验结果，成功时返回规范化的数据，失败时返回错误信息。

        """
        required = ["rule_name", "classification_id", "db_type", "operator"]
        missing = [field for field in required if not data.get(field)]
        if missing:
            return ServiceResult.fail(f"缺少必填字段: {', '.join(missing)}")

        classification = self._get_classification_by_id(data["classification_id"])
        if not classification:
            return ServiceResult.fail("选择的分类不存在")

        if not self._is_valid_option(data["db_type"], self._get_db_type_options()):
            return ServiceResult.fail("数据库类型取值无效")

        if not self._is_valid_option(data["operator"], OPERATOR_OPTIONS):
            return ServiceResult.fail("匹配逻辑取值无效")

        try:
            expression = data.get("rule_expression") or (resource.rule_expression if resource else "{}")
            if isinstance(expression, str):
                json.loads(expression)  # ensure valid json
            else:
                json.dumps(expression, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            return ServiceResult.fail(f"规则表达式格式错误: {exc}")

        normalized_expression = self._normalize_expression(data.get("rule_expression"))
        normalized = {
            "rule_name": data["rule_name"].strip(),
            "classification_id": classification.id,
            "db_type": data["db_type"],
            "operator": data["operator"],
            "rule_expression": normalized_expression,
            "is_active": self._coerce_bool(data.get("is_active"), default=True),
        }

        if self._rule_name_exists(normalized, resource):
            return ServiceResult.fail("同一数据库类型下规则名称重复", message_key="NAME_EXISTS")

        if self._expression_exists(normalized_expression, classification.id, resource):
            return ServiceResult.fail("规则表达式重复", message_key="EXPRESSION_DUPLICATED")

        return ServiceResult.ok(normalized)

    def assign(self, instance: ClassificationRule, data: dict[str, Any]) -> None:
        """将数据赋值给规则实例。

        Args:
            instance: 规则实例。
            data: 已校验的数据。

        Returns:
            None: 属性赋值完成后返回。

        """
        instance.rule_name = data["rule_name"]
        instance.classification_id = data["classification_id"]
        instance.db_type = data["db_type"]
        instance.operator = data["operator"]
        instance.rule_expression = data["rule_expression"]
        instance.is_active = data["is_active"]

    def after_save(self, instance: ClassificationRule, data: dict[str, Any]) -> None:
        """保存后记录日志并清除缓存。

        Args:
            instance: 已保存的规则实例。
            data: 已校验的数据。

        Returns:
            None: 日志与缓存刷新操作完成后返回。

        """
        from app.utils.structlog_config import log_info

        log_info(
            "分类规则保存成功",
            module="account_classification",
            rule_id=instance.id,
            operator_id=getattr(current_user, "id", None),
        )
        try:
            service = AccountClassificationService()
            service.invalidate_cache()
        except Exception as exc:
            log_info(
                "清除分类缓存失败",
                module="account_classification",
                rule_id=instance.id,
                error=str(exc),
            )

    def build_context(self, *, resource: ClassificationRule | None) -> dict[str, Any]:
        """构建模板渲染上下文。

        Args:
            resource: 规则实例，创建时为 None。

        Returns:
            包含分类、数据库类型和匹配逻辑选项的上下文字典。

        """
        classifications = AccountClassification.query.with_entities(
            AccountClassification.id, AccountClassification.name
        ).order_by(AccountClassification.priority.desc()).all()
        return {
            "classification_options": [{"value": c.id, "label": c.name} for c in classifications],
            "db_type_options": self._get_db_type_options(),
            "operator_options": OPERATOR_OPTIONS,
        }

    def _normalize_expression(self, expression: Any) -> str:
        """规范化规则表达式为 JSON 字符串。

        Args:
            expression: 原始表达式（字符串或字典）。

        Returns:
            JSON 格式的表达式字符串。

        Raises:
            ValueError: 当表达式格式错误时抛出。

        """
        parsed = json.loads(expression) if isinstance(expression, str) else expression or {}
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)

    def _coerce_bool(self, value: Any, *, default: bool) -> bool:
        """将值转换为布尔类型。

        Args:
            value: 待转换的值。
            default: 默认值。

        Returns:
            转换后的布尔值。

        """
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
            return default
        return default

    def _is_valid_option(self, value: str, options: list[dict[str, str]]) -> bool:
        """检查值是否在选项列表中。

        Args:
            value: 待检查的值。
            options: 选项列表。

        Returns:
            如果值有效返回 True，否则返回 False。

        """
        return any(item["value"] == value for item in options)

    def _get_db_type_options(self) -> list[dict[str, str]]:
        configs = DatabaseTypeService.get_active_types()
        if configs:
            return [
                {
                    "value": config.name,
                    "label": config.display_name or config.name,
                }
                for config in configs
            ]
        return DB_TYPE_OPTIONS

    def _rule_name_exists(self, data: dict[str, Any], resource: ClassificationRule | None) -> bool:
        query = ClassificationRule.query.filter(
            ClassificationRule.classification_id == data["classification_id"],
            ClassificationRule.db_type == data["db_type"],
            ClassificationRule.rule_name == data["rule_name"],
        )
        if resource:
            query = query.filter(ClassificationRule.id != resource.id)
        return db.session.query(query.exists()).scalar()

    def _expression_exists(
        self,
        normalized_expression: str,
        classification_id: int,
        resource: ClassificationRule | None,
    ) -> bool:
        query = ClassificationRule.query.filter(
            ClassificationRule.classification_id == classification_id,
            ClassificationRule.rule_expression == normalized_expression,
        )
        if resource:
            query = query.filter(ClassificationRule.id != resource.id)
        return db.session.query(query.exists()).scalar()

    def _get_classification_by_id(self, classification_id: int) -> AccountClassification | None:
        return AccountClassification.query.get(classification_id)
