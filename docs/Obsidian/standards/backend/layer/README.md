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
updated: 2026-01-10
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
  API["API v1(app/api/v1)"]
  Tasks["Tasks(app/tasks)"]
  Services["Services(app/services)"]
  Repositories["Repositories(app/repositories)"]
  Models["Models(app/models)"]
  FormsViews["Forms/Views(app/forms, app/views)"]
  Utils["Utils(app/utils)"]
  Errors["Errors(app/errors.py)"]
  Constants["Constants(app/constants)"]
  Types["Types(app/types)"]

  Routes --> Services & FormsViews & Utils
  API --> Services & Utils
  Tasks --> Services & Utils
  Services --> Repositories & Utils
  Repositories --> Models & Utils
  Models --> Utils
  Errors --> Routes & API & Tasks & Services & Repositories & FormsViews & Utils
  Constants --> Routes & API & Tasks & Services & Repositories & Models & Utils
  Types --> Routes & API & Tasks & Services & Repositories & Models & Utils
```

## 关键入口(少量)

- [[standards/backend/layer/api-layer-standards|API v1 层编写规范]]
- [[standards/backend/layer/services-layer-standards|Services 服务层编写规范]]
- [[standards/backend/layer/repository-layer-standards|Repository 仓储层编写规范]]
- [[standards/backend/layer/tasks-layer-standards|Tasks 任务层编写规范]]

## 全量浏览(不维护手工清单)

```query
path:"standards/backend/layer"
```
