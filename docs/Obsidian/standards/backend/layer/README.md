---
title: 后端分层标准索引
aliases:
  - backend-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
  - standards/index
status: active
created: 2026-01-09
updated: 2026-01-12
owner: WhaleFall Team
scope: 后端分层(layer)标准入口与索引
related:
  - "[[standards/backend/README]]"
---

# 后端分层标准

本目录定义后端各层的职责边界, 依赖方向, 命名与组织方式.

## 依赖方向(概览)

```mermaid
graph TD
  Routes["Routes(app/routes)"]
  API["API(app/api)"]
  Tasks["Tasks(app/tasks)"]
  Services["Services(app/services)"]
  Schemas["Schemas(app/schemas)"]
  Repositories["Repositories(app/repositories)"]
  Models["Models(app/models)"]
  FormsViews["Forms/Views(app/forms, app/views)"]
  Infra["Infra(app/infra, app/scheduler.py)"]
  Utils["Utils(app/utils)"]
  Settings["Settings(app/settings.py)"]
  SharedKernel["Shared Kernel(app/core)"]
  Constants["Constants(app/core/constants)"]
  Types["Types(app/core/types)"]

  Routes --> Services & FormsViews & Utils & Infra
  API --> Services & Utils & Infra
  Tasks --> Services & Utils
  Services --> Repositories & Utils & Schemas
  Schemas --> Utils
  Repositories --> Models & Utils
  Models --> Utils
  Infra --> Utils
  Settings --> Constants
  Routes & API & Tasks & Services & Schemas & Repositories & Models & FormsViews & Utils & Infra & Settings --> SharedKernel
  Routes & API & Tasks & Services & Schemas & Repositories & Models & FormsViews & Utils & Infra & Settings --> Constants
  Routes & API & Tasks & Services & Schemas & Repositories & Models & FormsViews & Utils & Infra & Settings --> Types
```

> [!note]
> `app/core/**` 为 shared kernel(跨层复用的核心对象),不属于某个业务层; 规范见 [[standards/backend/shared-kernel-standards|Shared Kernel 编写规范]]；异常定义见 `app/core/exceptions.py`, 异常→HTTP status 映射见 `app/infra/error_mapping.py`。

## 关键入口(少量)

- [[standards/backend/layer/api-layer-standards|API 层编写规范]]
- [[standards/backend/layer/services-layer-standards|Services 服务层编写规范]]
- [[standards/backend/layer/repository-layer-standards|Repository 仓储层编写规范]]
- [[standards/backend/layer/tasks-layer-standards|Tasks 任务层编写规范]]

## 全量浏览(不维护手工清单)

```query
path:"standards/backend/layer"
```
