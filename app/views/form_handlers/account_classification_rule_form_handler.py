"""账户分类规则表单处理器(View layer)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.constants import DatabaseType
from app.constants.classification_constants import OPERATOR_OPTIONS
from app.services.accounts.account_classifications_read_service import AccountClassificationsReadService
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService
from app.services.common.filter_options_service import FilterOptionsService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.types.request_payload import parse_payload

if TYPE_CHECKING:
    from app.models.account_classification import ClassificationRule


class AccountClassificationRuleFormHandler:
    """账户分类规则表单处理器."""

    def __init__(
        self,
        *,
        read_service: AccountClassificationsReadService | None = None,
        write_service: AccountClassificationsWriteService | None = None,
        filter_options_service: FilterOptionsService | None = None,
    ) -> None:
        self._read_service = read_service or AccountClassificationsReadService()
        self._write_service = write_service or AccountClassificationsWriteService()
        self._filter_options_service = filter_options_service or FilterOptionsService()

    def load(self, resource_id: ResourceIdentifier) -> "ClassificationRule | None":
        """加载分类规则资源."""
        if not isinstance(resource_id, int):
            return None
        return self._read_service.get_rule_by_id(resource_id)

    def upsert(
        self,
        payload: ResourcePayload,
        resource: "ClassificationRule | None" = None,
    ) -> "ClassificationRule":
        """创建或更新分类规则."""
        sanitized = cast(
            "dict[str, object]",
            parse_payload(payload or {}, boolean_fields_default_false=["is_active"]),
        )
        if resource is None:
            return self._write_service.create_rule(sanitized)
        return self._write_service.update_rule(resource, sanitized)

    def build_context(self, *, resource: "ClassificationRule | None") -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        db_type_options = [
            {"value": db_type, "label": DatabaseType.get_display_name(db_type)} for db_type in DatabaseType.RELATIONAL
        ]
        classification_options = self._filter_options_service.list_classification_options()
        return {
            "classification_options": classification_options,
            "db_type_options": db_type_options,
            "operator_options": OPERATOR_OPTIONS,
        }

