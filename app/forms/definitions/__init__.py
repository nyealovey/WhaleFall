"""资源表单定义集合，按需惰性导入避免循环依赖。"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .base import FieldComponent, FieldOption, ResourceFormDefinition, ResourceFormField

_LAZY_ATTRS: dict[str, str] = {
    "INSTANCE_FORM_DEFINITION": "app.forms.definitions.instance",
    "CREDENTIAL_FORM_DEFINITION": "app.forms.definitions.credential",
    "TAG_FORM_DEFINITION": "app.forms.definitions.tag",
    "CLASSIFICATION_FORM_DEFINITION": "app.forms.definitions.account_classification",
    "CLASSIFICATION_RULE_FORM_DEFINITION": "app.forms.definitions.account_classification_rule",
    "USER_FORM_DEFINITION": "app.forms.definitions.user",
    "CHANGE_PASSWORD_FORM_DEFINITION": "app.forms.definitions.change_password",
    "SCHEDULER_JOB_FORM_DEFINITION": "app.forms.definitions.scheduler_job",
}

__all__ = [
    "FieldComponent",
    "FieldOption",
    "ResourceFormDefinition",
    "ResourceFormField",
    *_LAZY_ATTRS.keys(),
]


def __getattr__(name: str) -> Any:
    """在首次访问时加载具体表单定义，规避导入环。"""

    if name not in _LAZY_ATTRS:
        raise AttributeError(f"module 'app.forms.definitions' 没有属性 {name}")

    module = import_module(_LAZY_ATTRS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
