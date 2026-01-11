"""账户分类表单处理器(View layer)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.constants.classification_constants import ICON_OPTIONS, RISK_LEVEL_OPTIONS
from app.constants.colors import ThemeColors
from app.services.accounts.account_classifications_read_service import AccountClassificationsReadService
from app.services.accounts.account_classifications_write_service import AccountClassificationsWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload
from app.types.request_payload import parse_payload

if TYPE_CHECKING:
    from app.models.account_classification import AccountClassification


class AccountClassificationFormHandler:
    """账户分类表单处理器."""

    def __init__(
        self,
        *,
        read_service: AccountClassificationsReadService | None = None,
        write_service: AccountClassificationsWriteService | None = None,
    ) -> None:
        self._read_service = read_service or AccountClassificationsReadService()
        self._write_service = write_service or AccountClassificationsWriteService()

    def load(self, resource_id: ResourceIdentifier) -> "AccountClassification | None":
        """加载账户分类资源."""
        if not isinstance(resource_id, int):
            return None
        return self._read_service.get_classification_by_id(resource_id)

    def upsert(
        self,
        payload: ResourcePayload,
        resource: "AccountClassification | None" = None,
    ) -> "AccountClassification":
        """创建或更新账户分类."""
        sanitized = cast("dict[str, object]", parse_payload(payload or {}))
        if resource is None:
            return self._write_service.create_classification(sanitized)
        return self._write_service.update_classification(resource, sanitized)

    def build_context(self, *, resource: "AccountClassification | None") -> ResourceContext:
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

