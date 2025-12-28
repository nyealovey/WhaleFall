"""账户分类规则表单处理器."""

from __future__ import annotations

from typing import cast

from app.constants import DatabaseType
from app.forms.definitions.account_classification_rule_constants import OPERATOR_OPTIONS
from app.models.account_classification import AccountClassification, ClassificationRule
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.utils.data_validator import DataValidator


class AccountClassificationRuleFormHandler:
    """账户分类规则表单处理器."""

    def __init__(self, service: AccountClassificationsWriteService | None = None) -> None:
        self._service = service or AccountClassificationsWriteService()

    def load(self, resource_id: ResourceIdentifier) -> ClassificationRule | None:
        if not isinstance(resource_id, int):
            return None
        return cast("ClassificationRule | None", ClassificationRule.query.get(resource_id))

    def upsert(
        self,
        payload: ResourcePayload,
        resource: ClassificationRule | None = None,
    ) -> ClassificationRule:
        sanitized = cast("dict[str, object]", DataValidator.sanitize_form_data(payload or {}))
        if resource is None:
            return self._service.create_rule(sanitized)
        return self._service.update_rule(resource, sanitized)

    def build_context(self, *, resource: ClassificationRule | None) -> ResourceContext:
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
