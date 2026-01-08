"""账号分类规则表达式校验 Service.

职责:
- 支持 rule_expression 为对象或 JSON 字符串
- 强制 DSL v4
- 收集校验错误并保持错误口径不变
"""

from __future__ import annotations

import json

import app.services.account_classification.dsl_v4 as dsl_v4_module
from app.errors import ValidationError


class AccountClassificationExpressionValidationService:
    """分类规则表达式校验服务."""

    def parse_and_validate(self, expression: object) -> object:
        """解析并校验分类规则表达式(强制 DSL v4).

        Args:
            expression: 原始表达式,可为对象或 JSON 字符串.

        Returns:
            object: 解析后的表达式对象.

        Raises:
            ValidationError: 当缺少字段/JSON 解析失败/非 DSL v4/校验失败.

        """
        if expression is None:
            raise ValidationError("缺少 rule_expression 字段")

        parsed: object = expression
        if isinstance(expression, str):
            try:
                parsed = json.loads(expression)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"规则表达式 JSON 解析失败: {exc}") from exc

        if not dsl_v4_module.is_dsl_v4_expression(parsed):
            raise ValidationError("仅支持 DSL v4 表达式(version=4)", message_key="DSL_V4_REQUIRED")

        errors = dsl_v4_module.collect_dsl_v4_validation_errors(parsed)
        if errors:
            raise ValidationError(
                "DSL v4 表达式校验失败",
                message_key="INVALID_DSL_EXPRESSION",
                extra={"errors": errors},
            )

        return parsed
