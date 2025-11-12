"""
账户分类表单服务
"""

from __future__ import annotations

from typing import Any, Mapping

from flask_login import current_user

from app import db
from app.constants.colors import ThemeColors
from app.forms.definitions.account_classification import ICON_OPTIONS, RISK_LEVEL_OPTIONS
from app.models.account_classification import AccountClassification
from app.services.resource_form_service import BaseResourceService, ServiceResult


class ClassificationFormService(BaseResourceService[AccountClassification]):
    """负责账户分类创建/编辑"""

    model = AccountClassification

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return dict(payload or {})

    def validate(self, data: dict[str, Any], *, resource: AccountClassification | None) -> ServiceResult[dict[str, Any]]:
        if not data.get("name"):
            return ServiceResult.fail("分类名称不能为空")

        color_key = (data.get("color") or (resource.color if resource else "info")).strip()
        if not ThemeColors.is_valid_color(color_key):
            return ServiceResult.fail("无效的颜色选择")

        try:
            normalized = {
                "name": data.get("name", resource.name if resource else "").strip(),
                "description": (data.get("description") or (resource.description if resource else "")).strip(),
                "risk_level": data.get("risk_level") or (resource.risk_level if resource else "medium"),
                "color": color_key,
                "icon_name": data.get("icon_name") or (resource.icon_name if resource else "fa-tag"),
                "priority": self._parse_priority(data.get("priority"), resource.priority if resource else 0),
            }
        except ValueError as exc:
            return ServiceResult.fail(str(exc))

        if not self._is_valid_option(normalized["risk_level"], RISK_LEVEL_OPTIONS):
            return ServiceResult.fail("风险等级取值无效")

        if not self._is_valid_option(normalized["icon_name"], ICON_OPTIONS):
            return ServiceResult.fail("图标取值无效")

        return ServiceResult.ok(normalized)

    def assign(self, instance: AccountClassification, data: dict[str, Any]) -> None:
        instance.name = data["name"]
        instance.description = data["description"]
        instance.risk_level = data["risk_level"]
        instance.color = data["color"]
        instance.icon_name = data["icon_name"]
        instance.priority = data["priority"]

    def after_save(self, instance: AccountClassification, data: dict[str, Any]) -> None:
        action = "创建账户分类成功" if instance.id else "更新账户分类成功"
        from app.utils.structlog_config import log_info  # avoid circular import

        log_info(
            action,
            module="account_classification",
            classification_id=instance.id,
            operator_id=getattr(current_user, "id", None),
        )

    def build_context(self, *, resource: AccountClassification | None) -> dict[str, Any]:
        color_options = [
            {"value": key, "name": info["name"], "description": info["description"], "css_class": info["css_class"]}
            for key, info in ThemeColors.COLOR_MAP.items()
        ]
        return {
            "color_options": color_options,
            "risk_level_options": RISK_LEVEL_OPTIONS,
            "icon_options": ICON_OPTIONS,
        }

    def _parse_priority(self, raw_value: Any, default: int) -> int:
        if raw_value in (None, ""):
            return default
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise ValueError("优先级必须为整数")
        return max(0, min(value, 100))

    def _is_valid_option(self, value: str, options: list[dict[str, str]]) -> bool:
        return any(item["value"] == value for item in options)
