"""账户分类表单服务."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask_login import current_user

from app import db
from app.constants.colors import ThemeColors
from app.forms.definitions.account_classification_constants import ICON_OPTIONS, RISK_LEVEL_OPTIONS
from app.models.account_classification import AccountClassification
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.types.converters import as_int, as_str
from app.utils.structlog_config import log_info

if TYPE_CHECKING:
    from app.types import (
        ColorOptionDict,
        ColorToken,
        ContextDict,
        MutablePayloadDict,
        PayloadMapping,
        PayloadValue,
    )
else:
    ColorOptionDict = dict[str, Any]
    ColorToken = str
    ContextDict = dict[str, Any]
    MutablePayloadDict = dict[str, Any]
    PayloadMapping = dict[str, Any]
    PayloadValue = Any


class ClassificationFormService(BaseResourceService[AccountClassification]):
    """负责账户分类创建/编辑.

    提供账户分类的表单校验、数据规范化和保存功能.

    Attributes:
        model: 关联的 AccountClassification 模型类.

    """

    model = AccountClassification

    def sanitize(self, payload: PayloadMapping) -> MutablePayloadDict:
        """清理表单数据.

        Args:
            payload: 原始表单数据.

        Returns:
            清理后的数据字典.

        """
        return dict(payload or {})

    def validate(
        self, data: MutablePayloadDict, *, resource: AccountClassification | None,
    ) -> ServiceResult[MutablePayloadDict]:
        """校验账户分类数据.

        校验必填字段、颜色有效性、风险等级和图标选项.

        Args:
            data: 清理后的数据.
            resource: 已存在的分类实例(编辑场景),创建时为 None.

        Returns:
            校验结果,成功时返回规范化的数据,失败时返回错误信息.

        """
        error_message = None
        error_key: str | None = None

        name = as_str(data.get("name"), default=resource.name if resource else "").strip()
        if not name:
            error_message = "分类名称不能为空"
        else:
            color_key: ColorToken = as_str(
                data.get("color"),
                default=resource.color if resource else "info",
            ).strip()
            if not ThemeColors.is_valid_color(color_key):
                error_message = "无效的颜色选择"

        normalized: MutablePayloadDict | None = None
        if error_message is None:
            try:
                description_value = as_str(
                    data.get("description"),
                    default=resource.description if resource else "",
                ).strip()
                risk_level_value = as_str(
                    data.get("risk_level"),
                    default=resource.risk_level if resource else "medium",
                )
                icon_name_value = as_str(
                    data.get("icon_name"),
                    default=resource.icon_name if resource else "fa-tag",
                )
                priority_value = self._parse_priority(
                    data.get("priority"),
                    resource.priority if resource else 0,
                )
                normalized = {
                    "name": name,
                    "description": description_value,
                    "risk_level": risk_level_value,
                    "color": color_key,
                    "icon_name": icon_name_value,
                    "priority": priority_value,
                    "_is_create": resource is None,
                }
            except ValueError as exc:
                error_message = str(exc)

        if error_message is None and normalized is not None:
            if not self._is_valid_option(normalized["risk_level"], RISK_LEVEL_OPTIONS):
                error_message = "风险等级取值无效"
            elif not self._is_valid_option(normalized["icon_name"], ICON_OPTIONS):
                error_message = "图标取值无效"
            elif self._name_exists(name, resource):
                error_message = "分类名称已存在"
                error_key = "NAME_EXISTS"

        if error_message:
            return ServiceResult.fail(error_message, message_key=error_key)

        return ServiceResult.ok(normalized or {})

    def assign(self, instance: AccountClassification, data: MutablePayloadDict) -> None:
        """将数据赋值给分类实例.

        Args:
            instance: 分类实例.
            data: 已校验的数据.

        Returns:
            None: 属性赋值完成后返回.

        """
        instance.name = data["name"]
        instance.description = data["description"]
        instance.risk_level = data["risk_level"]
        instance.color = data["color"]
        instance.icon_name = data["icon_name"]
        instance.priority = data["priority"]

    def after_save(self, instance: AccountClassification, data: MutablePayloadDict) -> None:
        """保存后记录日志.

        Args:
            instance: 已保存的分类实例.
            data: 已校验的数据.

        Returns:
            None: 日志记录完成后返回.

        """
        action = "创建账户分类成功" if data.get("_is_create") else "更新账户分类成功"

        log_info(
            action,
            module="account_classification",
            classification_id=instance.id,
            operator_id=getattr(current_user, "id", None),
        )

    def build_context(self, *, resource: AccountClassification | None) -> ContextDict:
        """构建模板渲染上下文.

        Args:
            resource: 分类实例,创建时为 None.

        Returns:
            包含颜色、风险等级和图标选项的上下文字典.

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
        return {
            "color_options": color_options,
            "risk_level_options": RISK_LEVEL_OPTIONS,
            "icon_options": ICON_OPTIONS,
        }

    def _parse_priority(self, raw_value: PayloadValue, default: int) -> int:
        """解析优先级值.

        Args:
            raw_value: 原始值.
            default: 默认值.

        Returns:
            解析后的优先级值(0-100).

        Raises:
            ValueError: 当值格式错误时抛出.

        """
        candidate = as_int(raw_value, default=default)
        if candidate is None:
            msg = "优先级必须为整数"
            raise ValueError(msg)
        value = candidate
        return max(0, min(value, 100))

    def _is_valid_option(self, value: str, options: list[dict[str, str]]) -> bool:
        """检查值是否在选项列表中.

        Args:
            value: 待检查的值.
            options: 选项列表.

        Returns:
            如果值有效返回 True,否则返回 False.

        """
        return any(item["value"] == value for item in options)

    def _name_exists(self, name: str, resource: AccountClassification | None) -> bool:
        query = AccountClassification.query.filter(AccountClassification.name == name)
        if resource:
            query = query.filter(AccountClassification.id != resource.id)
        return db.session.query(query.exists()).scalar()
