"""
表单定义包

集中管理资源级表单配置（字段、模板、服务映射等）。
"""

from .definitions.base import (
    FieldComponent,
    FieldOption,
    ResourceFormDefinition,
    ResourceFormField,
)

__all__ = [
    "FieldComponent",
    "FieldOption",
    "ResourceFormDefinition",
    "ResourceFormField",
]
