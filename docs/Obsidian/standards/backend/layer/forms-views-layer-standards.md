---
title: Forms 与 Views 层编写规范
aliases:
  - forms-views-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: "`app/forms/**`, `app/views/**` 下所有表单与表单视图"
related:
  - "[[standards/backend/layer/routes-layer-standards]]"
  - "[[standards/backend/layer/services-layer-standards]]"
---

# Forms 与 Views 层编写规范

> [!note] 说明
> Forms 负责表单结构与字段校验, Views 负责表单渲染/提交处理的通用视图逻辑. 业务编排仍应在 Service 中完成.

## 目的

- 统一表单定义与表单视图的组织方式, 避免模板与路由中散落校验规则.
- 固化依赖方向, 防止在表单层直接查库或写业务逻辑.
- 提供可复用的表单基类与通用行为, 降少重复代码.

## 适用范围

- `app/forms/**` 下所有 WTForms 表单定义与表单常量.
- `app/views/**` 下所有表单视图类(例如资源表单基类, 表单提交处理).

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: Forms 只定义表单结构, 字段校验, 静态 choices/常量配置.
- MUST: Views 负责表单渲染与提交流程控制, 调用 Service 完成业务动作.
- MUST NOT: Forms/Views 直接访问数据库(包括 `Model.query`, `db.session`).
- MUST NOT: Forms/Views 直接调用 Repository.
- SHOULD: 复杂业务校验(例如跨表冲突)放到 Service, 表单层只做字段级校验.

### 2) 目录结构(推荐)

```text
app/forms/
├── __init__.py
└── definitions/
    ├── __init__.py
    ├── base.py
    ├── instance.py
    ├── credential.py
    └── {entity}_constants.py

app/views/
├── __init__.py
├── mixins/
│   └── resource_forms.py
├── instance_forms.py
└── user_forms.py
```

### 3) 依赖规则

Forms 允许依赖:

- MUST: `wtforms`
- MAY: `app.constants.*`

Forms 禁止依赖:

- MUST NOT: `app.models.*`, `app.services.*`, `app.repositories.*`, `app` 的 `db`

Views 允许依赖:

- MUST: `app.forms.*`
- MAY: `app.services.*`(通过基类或明确的 service 注入)
- MAY: `app.errors`
- MAY: `flask` 的模板/URL 工具

### 4) 命名规范

| 类型 | 命名规则 | 示例 |
|---|---|---|
| 表单定义文件 | `{entity}.py` | `instance.py` |
| 表单常量文件 | `{entity}_constants.py` | `instance_constants.py` |
| 视图文件 | `{entity}_forms.py` | `instance_forms.py` |
| 视图类 | `{Entity}FormView` | `InstanceFormView` |

## 正反例

### 正例: 表单定义

- 判定点:
  - Forms 只定义字段/校验/展示信息, 不依赖 Model/Repository/DB.
  - 视图通过 form definition 渲染模板并处理提交, 业务校验下沉到 Service.
- 长示例见: [[reference/examples/backend-layer-examples#表单定义|Forms 表单定义(长示例)]]

### 正例: 表单视图

```python
"""实例表单视图."""

from flask import request, url_for

from app.forms.definitions.instance import INSTANCE_FORM_DEFINITION
from app.views.mixins.resource_forms import ResourceFormView


class InstanceFormView(ResourceFormView):
    form_definition = INSTANCE_FORM_DEFINITION

    def _resolve_success_redirect(self, instance) -> str:
        if request.view_args and request.view_args.get("instance_id"):
            return url_for("instances_detail.detail", instance_id=instance.id)
        return url_for("instances.index")
```

### 反例: 表单内查库

```python
class BadForm:
    def validate(self):
        # 反例: Forms 不应直接查询 Model
        return Instance.query.count()
```

## 门禁/检查方式

- 评审检查:
  - Forms/Views 是否保持无数据库依赖?
  - 业务校验是否下沉到 Service?
- 自查命令(示例):

```bash
rg -n "Model\\.query|db\\.session|from app\\.repositories\\." app/forms app/views
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
