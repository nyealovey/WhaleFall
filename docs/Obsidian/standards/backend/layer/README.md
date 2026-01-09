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
updated: 2026-01-09
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
  Routes["Routes(app/routes)"] --> Services["Services(app/services)"]
  API["API v1(app/api/v1)"] --> Services
  Tasks["Tasks(app/tasks)"] --> Services
  Services --> Repositories["Repositories(app/repositories)"]
  Repositories --> Models["Models(app/models)"]

  Routes --> FormsViews["Forms/Views(app/forms, app/views)"]

  Routes --> Utils["Utils(app/utils)"]
  API --> Utils
  Tasks --> Utils
  Services --> Utils
  Repositories --> Utils
  Models --> Utils

  Constants["Constants(app/constants)"] --> Routes
  Constants --> API
  Constants --> Tasks
  Constants --> Services
  Constants --> Repositories
  Constants --> Models
  Constants --> Utils

  Types["Types(app/types)"] --> Routes
  Types --> API
  Types --> Tasks
  Types --> Services
  Types --> Repositories
  Types --> Models
  Types --> Utils
```

## 索引

- [[standards/backend/layer/routes-layer-standards|Routes 路由层编写规范]]
- [[standards/backend/layer/api-layer-standards|API v1 层编写规范]]
- [[standards/backend/layer/services-layer-standards|Services 服务层编写规范]]
- [[standards/backend/layer/repository-layer-standards|Repository 仓储层编写规范]]
- [[standards/backend/layer/models-layer-standards|Models 数据模型层编写规范]]
- [[standards/backend/layer/forms-views-layer-standards|Forms 与 Views 层编写规范]]
- [[standards/backend/layer/tasks-layer-standards|Tasks 任务层编写规范]]
- [[standards/backend/layer/utils-layer-standards|Utils 工具层编写规范]]
- [[standards/backend/layer/types-layer-standards|Types 类型定义层编写规范]]
- [[standards/backend/layer/constants-layer-standards|Constants 常量层编写规范]]

