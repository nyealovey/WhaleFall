# Forms 与 Views 层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/forms/` 和 `app/views/` 目录的编写规范

---

## 核心原则

### Forms 层
**Forms = 表单定义 + 字段校验 + 常量配置**

### Views 层
**Views = 表单视图 + 渲染逻辑 + 请求处理**

```python
# ✅ Forms/Views 职责
- 定义 WTForms 表单结构
- 字段校验规则
- 处理表单渲染和提交
- 调用 Service 执行业务

# ❌ Forms/Views 禁止
- 直接查询数据库
- 直接调用 Repository
- 包含复杂业务逻辑
```

---

## 目录结构

```
forms/
├── __init__.py
└── definitions/              # 表单定义
    ├── __init__.py
    ├── base.py               # 基类
    ├── instance.py           # 实例表单
    ├── credential.py         # 凭据表单
    ├── tag.py                # 标签表单
    ├── user.py               # 用户表单
    └── {entity}_constants.py # 表单常量

views/
├── __init__.py
├── mixins/                   # 视图混入
│   └── resource_forms.py     # 资源表单基类
├── instance_forms.py         # 实例表单视图
├── credential_forms.py       # 凭据表单视图
├── tag_forms.py              # 标签表单视图
└── user_forms.py             # 用户表单视图
```

---

## 表单定义规范

```python
"""实例表单定义."""

from wtforms import StringField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange

from app.forms.definitions.base import BaseFormDefinition


INSTANCE_FORM_DEFINITION = BaseFormDefinition(
    model_name="Instance",
    template="instances/form.html",
    fields=[
        {
            "name": "name",
            "type": StringField,
            "label": "实例名称",
            "validators": [
                DataRequired(message="实例名称不能为空"),
                Length(min=1, max=255, message="名称长度 1-255 字符"),
            ],
        },
        {
            "name": "db_type",
            "type": SelectField,
            "label": "数据库类型",
            "choices": [
                ("mysql", "MySQL"),
                ("postgresql", "PostgreSQL"),
            ],
        },
        {
            "name": "port",
            "type": IntegerField,
            "label": "端口",
            "validators": [
                DataRequired(),
                NumberRange(min=1, max=65535),
            ],
        },
    ],
)
```

---

## 表单视图规范

```python
"""实例表单视图."""

from flask import request, url_for

from app.forms.definitions.instance import INSTANCE_FORM_DEFINITION
from app.views.mixins.resource_forms import ResourceFormView


class InstanceFormView(ResourceFormView):
    """实例创建/编辑视图."""

    form_definition = INSTANCE_FORM_DEFINITION

    def _resolve_success_redirect(self, instance) -> str:
        """成功后重定向地址."""
        if request.view_args and request.view_args.get("instance_id"):
            return url_for("instances_detail.detail", instance_id=instance.id)
        return url_for("instances.index")

    def get_success_message(self, instance) -> str:
        """成功消息."""
        if request.view_args and request.view_args.get("instance_id"):
            return "实例更新成功!"
        return "实例创建成功!"
```

---

## 依赖规则

### Forms 层

| 允许依赖 | 说明 |
|---------|------|
| `wtforms` | 表单库 |
| `app.constants.*` | 常量 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.models.*` | 数据模型 |
| `app.services.*` | 服务层 |

### Views 层

| 允许依赖 | 说明 |
|---------|------|
| `app.forms.*` | 表单定义 |
| `app.services.*` | 服务层（通过基类） |
| `flask` | Flask 工具 |

---

## 命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 表单定义文件 | `{entity}.py` | `instance.py` |
| 常量文件 | `{entity}_constants.py` | `instance_constants.py` |
| 视图文件 | `{entity}_forms.py` | `instance_forms.py` |
| 视图类 | `{Entity}FormView` | `InstanceFormView` |

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
