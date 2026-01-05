"""账户分类表单处理器."""

from __future__ import annotations

from typing import cast

from app.constants.colors import ThemeColors
from app.forms.definitions.account_classification_constants import ICON_OPTIONS, RISK_LEVEL_OPTIONS
from app.models.account_classification import AccountClassification
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.types.request_payload import parse_payload


class AccountClassificationFormHandler:
    """账户分类表单处理器."""

    def __init__(self, service: AccountClassificationsWriteService | None = None) -> None:
        """初始化表单处理器并注入写服务."""
        self._service = service or AccountClassificationsWriteService()

    def load(self, resource_id: ResourceIdentifier) -> AccountClassification | None:
        """加载账户分类资源."""
        if not isinstance(resource_id, int):
            return None
        return cast("AccountClassification | None", AccountClassification.query.get(resource_id))

    def upsert(
        self,
        payload: ResourcePayload,
        resource: AccountClassification | None = None,
    ) -> AccountClassification:
        """创建或更新账户分类."""
        sanitized = cast("dict[str, object]", parse_payload(payload or {}))
        if resource is None:
            return self._service.create_classification(sanitized)
        return self._service.update_classification(resource, sanitized)

    def build_context(self, *, resource: AccountClassification | None) -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        color_options = [
            {
                "value": key,
                "name": info["name"],
                "description": info["description"],
                "css_class": info["css_class"],
            }
            for key, info in ThemeColors.COLOR_MAP.items()
        ]
        return {
            "color_options": color_options,
            "risk_level_options": RISK_LEVEL_OPTIONS,
            "icon_options": ICON_OPTIONS,
        }
