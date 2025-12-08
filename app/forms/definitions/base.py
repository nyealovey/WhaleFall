"""
基础的资源表单定义模型。

这些定义会被后端视图、服务层以及前端控制器共享，确保字段描述只有唯一来源。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol
from collections.abc import Mapping

if False:  # typing-only import guard
    from app.services.form_service.resource_service import BaseResourceService  # pragma: no cover


class FieldComponent(str, Enum):
    """表单控件类型。"""

    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    NUMBER = "number"
    CHECKBOX = "checkbox"
    SWITCH = "switch"
    TAG_SELECTOR = "tag-selector"


@dataclass(slots=True)
class FieldOption:
    """下拉或多选项描述。"""

    value: Any
    label: str
    meta: Mapping[str, Any] | None = None


@dataclass(slots=True)
class ResourceFormField:
    """单个字段的元数据。"""

    name: str
    label: str
    component: FieldComponent = FieldComponent.TEXT
    required: bool = False
    placeholder: str | None = None
    help_text: str | None = None
    default: Any | None = None
    options: list[FieldOption] = field(default_factory=list)
    props: dict[str, Any] = field(default_factory=dict)
    visibility_condition: str | None = None


class ContextBuilder(Protocol):
    """构造额外渲染上下文的协议。

    允许在渲染表单模板前补充依赖于当前资源的数据。
    """

    def __call__(self, *, resource: Any | None) -> Mapping[str, Any]:
        """构造模板渲染所需的上下文字典。

        Args:
            resource: 当前正在编辑的资源实例，创建场景下可能为 None。

        Returns:
            一个映射对象，合并到模板上下文中。

        """
        ...


@dataclass(slots=True)
class ResourceFormDefinition:
    """
    描述某个资源表单的基础配置。

    Attributes:
        name: 资源英文名（如 instance、credential）
        template: 渲染所用的模板路径
        service_class: 负责持久化的服务类型
        fields: 字段定义列表
        success_message: 保存成功后的提示语
        redirect_endpoint: 保存成功后跳转的端点
        context_builder: 额外上下文构造器（可选）
        extra_config: 其他自定义配置

    """

    name: str
    template: str
    service_class: type[BaseResourceService]
    fields: list[ResourceFormField] = field(default_factory=list)
    success_message: str = "保存成功"
    redirect_endpoint: str | None = None
    context_builder: ContextBuilder | None = None
    extra_config: dict[str, Any] = field(default_factory=dict)
