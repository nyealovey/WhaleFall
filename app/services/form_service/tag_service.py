"""标签表单服务."""

from __future__ import annotations

import re
from typing import Any, cast

from flask_login import current_user

from app.constants.colors import ThemeColors
from app.models.tag import Tag
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.types import (
    CategoryOptionDict,
    ColorOptionDict,
    ColorToken,
    ContextDict,
    MutablePayloadDict,
    PayloadMapping,
)
from app.types.converters import as_bool, as_str
from app.utils.data_validator import sanitize_form_data, validate_required_fields
from app.utils.structlog_config import log_info

class TagFormService(BaseResourceService[Tag]):
    """负责标签创建与编辑的服务.

    提供标签的表单校验、数据规范化和保存功能.

    Attributes:
        model: 关联的 Tag 模型类.
        NAME_PATTERN: 标签代码的正则表达式模式.

    """

    model = Tag
    NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

    def sanitize(self, payload: PayloadMapping) -> MutablePayloadDict:
        """清理表单数据.

        Args:
            payload: 原始表单数据.

        Returns:
            清理后的数据字典.

        """
        return sanitize_form_data(payload or {})

    def validate(self, data: MutablePayloadDict, *, resource: Tag | None) -> ServiceResult[MutablePayloadDict]:
        """校验标签数据.

        校验必填字段、代码格式、颜色有效性和唯一性.

        Args:
            data: 清理后的数据.
            resource: 已存在的标签实例(编辑场景),创建时为 None.

        Returns:
            校验结果,成功时返回规范化的数据,失败时返回错误信息.

        """
        validation_error = validate_required_fields(data, ["name", "display_name", "category"])
        if validation_error:
            return ServiceResult.fail(validation_error)

        try:
            normalized = self._normalize_payload(data, resource)
        except ValueError as exc:
            return ServiceResult.fail(str(exc))

        name_value = cast(str, normalized["name"])
        color_value = cast(ColorToken, normalized["color"])

        # 代码格式校验
        if not self.NAME_PATTERN.match(name_value):
            return ServiceResult.fail("标签代码仅支持字母、数字、下划线或中划线")

        # 颜色校验
        if not ThemeColors.is_valid_color(color_value):
            return ServiceResult.fail(f"无效的颜色选择: {color_value}")

        # 唯一性校验
        name_filter: Any = Tag.name == name_value
        query = Tag.query.filter(name_filter)
        if resource:
            exclude_current: Any = Tag.id != resource.id
            query = query.filter(exclude_current)
        if query.first():
            return ServiceResult.fail("标签代码已存在,请使用其他名称")

        return ServiceResult.ok(normalized)

    def assign(self, instance: Tag, data: MutablePayloadDict) -> None:
        """将数据赋值给标签实例.

        Args:
            instance: 标签实例.
            data: 已校验的数据.

        Returns:
            None: 属性赋值完成后返回.

        """
        instance.name = as_str(data.get("name"))
        instance.display_name = as_str(data.get("display_name"))
        instance.category = as_str(data.get("category"))
        instance.color = as_str(data.get("color"), default="primary")
        instance.is_active = as_bool(data.get("is_active"), default=True)

    def after_save(self, instance: Tag, data: MutablePayloadDict) -> None:
        """保存后记录日志.

        Args:
            instance: 已保存的标签实例.
            data: 已校验的数据.

        Returns:
            None: 日志写入后返回.

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

    def build_context(self, *, resource: Tag | None) -> ContextDict:
        """构建模板渲染上下文.

        Args:
            resource: 标签实例,创建时为 None.

        Returns:
            包含颜色选项和分类选项的上下文字典.

        """
        del resource
        color_options: list[ColorOptionDict] = [
            {
                "value": key,
                "name": info["name"],
                "description": info["description"],
                "css_class": info["css_class"],
            }
            for key, info in ThemeColors.COLOR_MAP.items()
        ]
        category_options: list[CategoryOptionDict] = [
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
    def _normalize_payload(self, data: PayloadMapping, resource: Tag | None) -> MutablePayloadDict:
        """规范化表单数据.

        Args:
            data: 原始数据.
            resource: 已存在的标签实例,创建时为 None.

        Returns:
            规范化后的数据字典.

        """
        normalized: MutablePayloadDict = {}
        normalized["name"] = as_str(
            data.get("name"),
            default=resource.name if resource else "",
        ).strip()
        normalized["display_name"] = as_str(
            data.get("display_name"),
            default=resource.display_name if resource else "",
        ).strip()
        normalized["category"] = as_str(
            data.get("category"),
            default=resource.category if resource else "",
        ).strip()
        color_value: ColorToken = (
            as_str(
                data.get("color"),
                default=resource.color if resource else "primary",
            ).strip()
            or "primary"
        )
        normalized["color"] = color_value

        normalized["is_active"] = as_bool(
            data.get("is_active"),
            default=resource.is_active if resource else True,
        )
        normalized["_is_create"] = resource is None
        return normalized

    def _create_instance(self) -> Tag:
        """提供标签模型的占位实例.

        Tag 的构造函数要求传入 name/display_name/category,
        因此前端数据尚未赋值时使用默认占位内容,随后 assign 会覆盖.
        """
        return Tag(
            name="__pending__",
            display_name="__pending__",
            category="other",
            color="primary",
            is_active=True,
        )
