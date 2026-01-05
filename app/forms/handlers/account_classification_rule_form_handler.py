"""账户分类规则表单处理器."""

from __future__ import annotations

from typing import cast

from app.constants import DatabaseType
from app.forms.definitions.account_classification_rule_constants import OPERATOR_OPTIONS
from app.models.account_classification import AccountClassification, ClassificationRule
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.types.request_payload import parse_payload


class AccountClassificationRuleFormHandler:
    """账户分类规则表单处理器."""

    def __init__(self, service: AccountClassificationsWriteService | None = None) -> None:
        """初始化表单处理器并注入写服务."""
        self._service = service or AccountClassificationsWriteService()

    def load(self, resource_id: ResourceIdentifier) -> ClassificationRule | None:
        """加载分类规则资源."""
        if not isinstance(resource_id, int):
            return None
        return cast("ClassificationRule | None", ClassificationRule.query.get(resource_id))

    def upsert(
        self,
        payload: ResourcePayload,
        resource: ClassificationRule | None = None,
    ) -> ClassificationRule:
        """创建或更新分类规则."""
        sanitized = cast(
            "dict[str, object]",
            parse_payload(payload or {}, boolean_fields_default_false=["is_active"]),
        )
        if resource is None:
            return self._service.create_rule(sanitized)
        return self._service.update_rule(resource, sanitized)

    def build_context(self, *, resource: ClassificationRule | None) -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        classifications = (
            AccountClassification.query.with_entities(
                AccountClassification.id,
                AccountClassification.name,
            )
            .order_by(AccountClassification.priority.desc())
            .all()
        )

        db_type_options = [
            {"value": db_type, "label": DatabaseType.get_display_name(db_type)} for db_type in DatabaseType.RELATIONAL
        ]

        return {
            "classification_options": [{"value": c.id, "label": c.name} for c in classifications],
            "db_type_options": db_type_options,
            "operator_options": OPERATOR_OPTIONS,
        }
