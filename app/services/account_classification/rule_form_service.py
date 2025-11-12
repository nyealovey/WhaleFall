"""
账户分类规则表单服务
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from flask_login import current_user

from app import db
from app.forms.definitions.account_classification_rule import DB_TYPE_OPTIONS, OPERATOR_OPTIONS
from app.models.account_classification import AccountClassification, ClassificationRule
from app.services.resource_form_service import BaseResourceService, ServiceResult
from app.services.account_classification.orchestrator import AccountClassificationService


class ClassificationRuleFormService(BaseResourceService[ClassificationRule]):
    """分类规则创建/编辑"""

    model = ClassificationRule

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return dict(payload or {})

    def validate(self, data: dict[str, Any], *, resource: ClassificationRule | None) -> ServiceResult[dict[str, Any]]:
        required = ["rule_name", "classification_id", "db_type", "operator"]
        missing = [field for field in required if not data.get(field)]
        if missing:
            return ServiceResult.fail(f"缺少必填字段: {', '.join(missing)}")

        classification = AccountClassification.query.get(data["classification_id"])
        if not classification:
            return ServiceResult.fail("选择的分类不存在")

        if not self._is_valid_option(data["db_type"], DB_TYPE_OPTIONS):
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

        normalized = {
            "rule_name": data["rule_name"].strip(),
            "classification_id": classification.id,
            "db_type": data["db_type"],
            "operator": data["operator"],
            "rule_expression": self._normalize_expression(data.get("rule_expression")),
            "is_active": self._coerce_bool(data.get("is_active"), default=True),
        }

        return ServiceResult.ok(normalized)

    def assign(self, instance: ClassificationRule, data: dict[str, Any]) -> None:
        instance.rule_name = data["rule_name"]
        instance.classification_id = data["classification_id"]
        instance.db_type = data["db_type"]
        instance.operator = data["operator"]
        instance.rule_expression = data["rule_expression"]
        instance.is_active = data["is_active"]

    def after_save(self, instance: ClassificationRule, data: dict[str, Any]) -> None:
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
        except Exception as exc:  # noqa: BLE001
            log_info(
                "清除分类缓存失败",
                module="account_classification",
                rule_id=instance.id,
                error=str(exc),
            )

    def build_context(self, *, resource: ClassificationRule | None) -> dict[str, Any]:
        classifications = AccountClassification.query.with_entities(
            AccountClassification.id, AccountClassification.name
        ).order_by(AccountClassification.priority.desc()).all()
        return {
            "classification_options": [{"value": c.id, "label": c.name} for c in classifications],
            "db_type_options": DB_TYPE_OPTIONS,
            "operator_options": OPERATOR_OPTIONS,
        }

    def _normalize_expression(self, expression: Any) -> str:
        if isinstance(expression, str):
            json.loads(expression)  # ensure valid json
            return expression
        return json.dumps(expression or {}, ensure_ascii=False)

    def _coerce_bool(self, value: Any, *, default: bool) -> bool:
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
        return any(item["value"] == value for item in options)
