"""
标签表单服务
"""

from __future__ import annotations

import re
from typing import Any
from collections.abc import Mapping

from flask_login import current_user

from app.constants.colors import ThemeColors
from app.models.tag import Tag
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.utils.data_validator import sanitize_form_data, validate_required_fields
from app.utils.structlog_config import log_info


class TagFormService(BaseResourceService[Tag]):
    """负责标签创建与编辑的服务。

    提供标签的表单校验、数据规范化和保存功能。

    Attributes:
        model: 关联的 Tag 模型类。
        NAME_PATTERN: 标签代码的正则表达式模式。

    """

    model = Tag
    NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """清理表单数据。

        Args:
            payload: 原始表单数据。

        Returns:
            清理后的数据字典。

        """
        return sanitize_form_data(payload or {})

    def validate(self, data: dict[str, Any], *, resource: Tag | None) -> ServiceResult[dict[str, Any]]:
        """校验标签数据。

        校验必填字段、代码格式、颜色有效性和唯一性。

        Args:
            data: 清理后的数据。
            resource: 已存在的标签实例（编辑场景），创建时为 None。

        Returns:
            校验结果，成功时返回规范化的数据，失败时返回错误信息。

        """
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
        """将数据赋值给标签实例。

        Args:
            instance: 标签实例。
            data: 已校验的数据。

        Returns:
            None: 属性赋值完成后返回。

        """
        instance.name = data["name"]
        instance.display_name = data["display_name"]
        instance.category = data["category"]
        instance.color = data["color"]
        instance.is_active = data["is_active"]

    def after_save(self, instance: Tag, data: dict[str, Any]) -> None:
        """保存后记录日志。

        Args:
            instance: 已保存的标签实例。
            data: 已校验的数据。

        Returns:
            None: 日志写入后返回。

        """
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
        """构建模板渲染上下文。

        Args:
            resource: 标签实例，创建时为 None。

        Returns:
            包含颜色选项和分类选项的上下文字典。

        """
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
        """规范化表单数据。

        Args:
            data: 原始数据。
            resource: 已存在的标签实例，创建时为 None。

        Returns:
            规范化后的数据字典。

        """
        normalized: dict[str, Any] = {}
        normalized["name"] = (data.get("name") or (resource.name if resource else "")).strip()
        normalized["display_name"] = (data.get("display_name") or (resource.display_name if resource else "")).strip()
        normalized["category"] = (data.get("category") or (resource.category if resource else "")).strip()
        normalized["color"] = (data.get("color") or (resource.color if resource else "primary")).strip() or "primary"

        normalized["is_active"] = self._coerce_bool(
            data.get("is_active"),
            default=(resource.is_active if resource else True),
        )
        normalized["_is_create"] = resource is None
        return normalized

    def _coerce_bool(self, value: Any, *, default: bool) -> bool:
        """将值转换为布尔类型。

        Args:
            value: 待转换的值。
            default: 默认值。

        Returns:
            转换后的布尔值。

        """
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

    def _create_instance(self) -> Tag:
        """提供标签模型的占位实例。

        Tag 的构造函数要求传入 name/display_name/category，
        因此前端数据尚未赋值时使用默认占位内容，随后 assign 会覆盖。
        """

        return Tag(
            name="__pending__",
            display_name="__pending__",
            category="other",
            color="primary",
            is_active=True,
        )
