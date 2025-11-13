"""
标签表单服务
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from flask_login import current_user

from app import db
from app.constants.colors import ThemeColors
from app.models.tag import Tag
from app.services.form_service.resource_form_service import BaseResourceService, ServiceResult
from app.utils.data_validator import sanitize_form_data, validate_required_fields
from app.utils.structlog_config import log_info


class TagFormService(BaseResourceService[Tag]):
    """负责标签创建与编辑的服务。"""

    model = Tag
    NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return sanitize_form_data(payload or {})

    def validate(self, data: dict[str, Any], *, resource: Tag | None) -> ServiceResult[dict[str, Any]]:
        validation_error = validate_required_fields(data, ["name", "display_name", "category"])
        if validation_error:
            return ServiceResult.fail(validation_error)

        try:
            normalized = self._normalize_payload(data, resource)
        except ValueError as exc:
            return ServiceResult.fail(str(exc))

        # 代码格式校验
        if not self.NAME_PATTERN.match(normalized["name"]):
            return ServiceResult.fail("标签代码仅支持字母、数字、下划线或中划线")

        # 颜色校验
        if not ThemeColors.is_valid_color(normalized["color"]):
            return ServiceResult.fail(f"无效的颜色选择: {normalized['color']}")

        # 唯一性校验
        query = Tag.query.filter(Tag.name == normalized["name"])
        if resource:
            query = query.filter(Tag.id != resource.id)
        if query.first():
            return ServiceResult.fail("标签代码已存在，请使用其他名称")

        return ServiceResult.ok(normalized)

    def assign(self, instance: Tag, data: dict[str, Any]) -> None:
        instance.name = data["name"]
        instance.display_name = data["display_name"]
        instance.category = data["category"]
        instance.color = data["color"]
        instance.description = data["description"]
        instance.sort_order = data["sort_order"]
        instance.is_active = data["is_active"]

    def after_save(self, instance: Tag, data: dict[str, Any]) -> None:
        action = "标签创建成功" if data.get("_is_create") else "标签更新成功"
        log_info(
            action,
            module="tags",
            user_id=getattr(current_user, "id", None),
            tag_id=instance.id,
            name=instance.name,
            category=instance.category,
            color=instance.color,
            is_active=instance.is_active,
        )

    def build_context(self, *, resource: Tag | None) -> dict[str, Any]:
        color_options = [
            {"value": key, "name": info["name"], "description": info["description"], "css_class": info["css_class"]}
            for key, info in ThemeColors.COLOR_MAP.items()
        ]
        category_options = [
            {"value": value, "label": label}
            for value, label in Tag.get_category_choices()
        ]
        return {
            "color_options": color_options,
            "category_options": category_options,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _normalize_payload(self, data: Mapping[str, Any], resource: Tag | None) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        normalized["name"] = (data.get("name") or (resource.name if resource else "")).strip()
        normalized["display_name"] = (data.get("display_name") or (resource.display_name if resource else "")).strip()
        normalized["category"] = (data.get("category") or (resource.category if resource else "")).strip()
        normalized["color"] = (data.get("color") or (resource.color if resource else "primary")).strip() or "primary"
        description_value = data.get("description")
        if description_value is None and resource:
            description_value = resource.description
        normalized["description"] = (description_value or "").strip() or None

        sort_raw = data.get("sort_order")
        if sort_raw in (None, ""):
            sort_value = resource.sort_order if resource else 0
        else:
            try:
                sort_value = int(sort_raw)
            except (TypeError, ValueError):
                raise ValueError("排序值格式错误，请输入整数")
        normalized["sort_order"] = max(0, sort_value)

        normalized["is_active"] = self._coerce_bool(
            data.get("is_active"),
            default=(resource.is_active if resource else True),
        )
        normalized["_is_create"] = resource is None
        return normalized

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
