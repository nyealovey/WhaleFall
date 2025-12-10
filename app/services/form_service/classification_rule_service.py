"""账户分类规则表单服务."""

from __future__ import annotations

import json

from typing import cast

from flask_login import current_user

from app import db
from app.forms.definitions.account_classification_rule_constants import DB_TYPE_OPTIONS, OPERATOR_OPTIONS
from app.models.account_classification import AccountClassification, ClassificationRule
from app.services.account_classification.orchestrator import AccountClassificationService
from app.services.database_type_service import DatabaseTypeService
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.types import ContextDict, MutablePayloadDict, PayloadMapping, PayloadValue
from app.types.converters import as_bool, as_int, as_optional_str, as_str
from app.utils.structlog_config import log_info

class ClassificationRuleFormService(BaseResourceService[ClassificationRule]):
    """分类规则创建/编辑.

    提供分类规则的表单校验、数据规范化和保存功能.

    Attributes:
        model: 关联的 ClassificationRule 模型类.

    """

    model = ClassificationRule

    def sanitize(self, payload: PayloadMapping) -> MutablePayloadDict:
        """清理表单数据.

        Args:
            payload: 原始表单数据.

        Returns:
            清理后的数据字典.

        """
        return dict(payload or {})

    def validate(self, data: MutablePayloadDict, *, resource: ClassificationRule | None) -> ServiceResult[MutablePayloadDict]:
        """校验分类规则数据.

        校验必填字段、分类存在性、数据库类型、匹配逻辑和规则表达式格式.

        Args:
            data: 清理后的数据.
            resource: 已存在的规则实例(编辑场景),创建时为 None.

        Returns:
            校验结果,成功时返回规范化的数据,失败时返回错误信息.

        """
        failure = self._validate_required_fields(data)

        classification: AccountClassification | None = None
        classification_id = as_int(data.get("classification_id"))
        if not failure:
            if classification_id is None:
                failure = ServiceResult.fail("选择的分类不存在")
            else:
                classification = self._get_classification_by_id(classification_id)
                if not classification:
                    failure = ServiceResult.fail("选择的分类不存在")

        db_type_value = as_optional_str(data.get("db_type"))
        if not failure:
            failure = self._validate_option(
                db_type_value,
                self._get_db_type_options(),
                "数据库类型取值无效",
            )

        operator_value = as_optional_str(data.get("operator"))
        if not failure:
            failure = self._validate_option(
                operator_value,
                OPERATOR_OPTIONS,
                "匹配逻辑取值无效",
            )

        expression_error, normalized_expression = self._validate_expression_payload(data, resource)
        failure = failure or expression_error

        if failure or not classification:
            return failure or ServiceResult.fail("选择的分类不存在")

        normalized: MutablePayloadDict = {
            "rule_name": as_str(data.get("rule_name"), default="").strip(),
            "classification_id": classification.id,
            "db_type": db_type_value or "",
            "operator": operator_value or "",
            "rule_expression": normalized_expression,
            "is_active": as_bool(data.get("is_active"), default=True),
        }

        if self._rule_name_exists(normalized, resource):
            failure = ServiceResult.fail("同一数据库类型下规则名称重复", message_key="NAME_EXISTS")

        if not failure and self._expression_exists(normalized_expression, classification.id, resource):
            failure = ServiceResult.fail("规则表达式重复", message_key="EXPRESSION_DUPLICATED")

        if failure:
            return failure

        return ServiceResult.ok(normalized)

    def assign(self, instance: ClassificationRule, data: MutablePayloadDict) -> None:
        """将数据赋值给规则实例.

        Args:
            instance: 规则实例.
            data: 已校验的数据.

        Returns:
            None: 属性赋值完成后返回.

        """
        instance.rule_name = cast(str, data["rule_name"])
        instance.classification_id = cast(int, data["classification_id"])
        instance.db_type = cast(str, data["db_type"])
        instance.operator = cast(str, data["operator"])
        instance.rule_expression = cast(str, data["rule_expression"])
        instance.is_active = cast(bool, data["is_active"])

    def after_save(self, instance: ClassificationRule, data: MutablePayloadDict) -> None:
        """保存后记录日志并清除缓存.

        Args:
            instance: 已保存的规则实例.
            data: 已校验的数据.

        Returns:
            None: 日志与缓存刷新操作完成后返回.

        """
        del data
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

    def build_context(self, *, resource: ClassificationRule | None) -> ContextDict:
        """构建模板渲染上下文.

        Args:
            resource: 规则实例,创建时为 None.

        Returns:
            包含分类、数据库类型和匹配逻辑选项的上下文字典.

        """
        del resource
        classifications = AccountClassification.query.with_entities(
            AccountClassification.id, AccountClassification.name,
        ).order_by(AccountClassification.priority.desc()).all()
        return {
            "classification_options": [{"value": c.id, "label": c.name} for c in classifications],
            "db_type_options": self._get_db_type_options(),
            "operator_options": OPERATOR_OPTIONS,
        }

    def _validate_required_fields(self, data: MutablePayloadDict) -> ServiceResult[MutablePayloadDict] | None:
        """校验必填字段是否全部存在."""
        required_fields = ["rule_name", "classification_id", "db_type", "operator"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return ServiceResult.fail(f"缺少必填字段: {', '.join(missing)}")
        return None

    def _validate_option(
        self,
        value: str | None,
        options: list[dict[str, str]],
        message: str,
    ) -> ServiceResult[MutablePayloadDict] | None:
        """校验值是否存在于预设选项中."""
        if not value or not self._is_valid_option(value, options):
            return ServiceResult.fail(message)
        return None

    def _validate_expression_payload(
        self,
        data: MutablePayloadDict,
        resource: ClassificationRule | None,
    ) -> tuple[ServiceResult[MutablePayloadDict] | None, str]:
        """校验表达式格式并返回规范化结果."""
        expression = data.get("rule_expression") or (resource.rule_expression if resource else "{}")
        try:
            if isinstance(expression, str):
                json.loads(expression)
            else:
                json.dumps(expression, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            return ServiceResult.fail(f"规则表达式格式错误: {exc}"), "{}"
        normalized_expression = self._normalize_expression(data.get("rule_expression"))
        return None, normalized_expression

    def _normalize_expression(self, expression: PayloadValue | None) -> str:
        """规范化规则表达式为 JSON 字符串.

        Args:
            expression: 原始表达式(字符串或字典).

        Returns:
            JSON 格式的表达式字符串.

        Raises:
            ValueError: 当表达式格式错误时抛出.

        """
        parsed = json.loads(expression) if isinstance(expression, str) else expression or {}
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)

    def _is_valid_option(self, value: str, options: list[dict[str, str]]) -> bool:
        """检查值是否在选项列表中.

        Args:
            value: 待检查的值.
            options: 选项列表.

        Returns:
            如果值有效返回 True,否则返回 False.

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

    def _rule_name_exists(self, data: MutablePayloadDict, resource: ClassificationRule | None) -> bool:
        classification_id = cast(int, data["classification_id"])
        db_type = cast(str, data["db_type"])
        rule_name = cast(str, data["rule_name"])
        query = ClassificationRule.query.filter_by(
            classification_id=classification_id,
            db_type=db_type,
            rule_name=rule_name,
        )
        if resource:
            resource_id = cast(int, resource.id)
            query = query.filter(ClassificationRule.id != resource_id)
        return db.session.query(query.exists()).scalar()

    def _expression_exists(
        self,
        normalized_expression: str,
        classification_id: int,
        resource: ClassificationRule | None,
    ) -> bool:
        query = ClassificationRule.query.filter_by(
            classification_id=classification_id,
            rule_expression=normalized_expression,
        )
        if resource:
            resource_id = cast(int, resource.id)
            query = query.filter(ClassificationRule.id != resource_id)
        return db.session.query(query.exists()).scalar()

    def _get_classification_by_id(self, classification_id: int) -> AccountClassification | None:
        return AccountClassification.query.get(classification_id)
