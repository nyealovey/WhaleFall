"""资源表单视图与服务层共享的类型定义.

统一描述资源标识、上下文与协议,方便在视图与服务之间传递结构化数据.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, TypeVar, runtime_checkable

from app.core.types.structures import ContextMapping, PayloadMapping

ResourceIdentifier = int | str
ResourcePayload = PayloadMapping
TemplateContext = Mapping[str, object]
ResourceContext = ContextMapping


@runtime_checkable
class SupportsResourceId(Protocol):
    """约束具备 id 属性的资源对象."""

    id: ResourceIdentifier


ResourceInstance = TypeVar("ResourceInstance", bound="SupportsResourceId")
