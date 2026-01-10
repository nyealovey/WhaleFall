---
title: 模块依赖边界图(layer-first)
aliases:
  - module-dependency-graph
tags:
  - architecture
  - architecture/dependency
  - layer-first
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 代码分层依赖方向, 以及允许/禁止的模块依赖边界
related:
  - "[[architecture/project-structure]]"
  - "[[architecture/spec]]"
  - "[[architecture/developer-entrypoint]]"
  - "[[standards/backend/layer/README|后端分层标准]]"
---

# 模块依赖边界图(layer-first)

> [!note] 目标
> 给出一个能落到 `import` 级别的依赖方向: 谁可以依赖谁, 谁不应该依赖谁.

## 1. 依赖方向总览(Depends on)

```mermaid
graph TD
  subgraph HTTP["HTTP layer"]
    Routes["Routes(app/routes/**)"]
    ApiV1["API v1(app/api/v1/**)"]
  end

  subgraph Domain["Domain layer"]
    Tasks["Tasks(app/tasks/**)"]
    Services["Services(app/services/**)"]
    Schemas["Schemas(app/schemas/**)"]
    FormsViews["Forms/Views(app/forms/**, app/views/**)"]
  end

  subgraph Data["Data layer"]
    Repos["Repositories(app/repositories/**)"]
    Models["Models(app/models/**)"]
  end

  subgraph Foundations["Foundations (base)"]
    Constants["Constants(app/constants/**)"]
    Types["Types(app/types/**)"]
    Errors["Errors(app/errors/**)"]
    Utils["Utils(app/utils/**)"]
    Settings["Settings(app/settings.py)"]
  end

  Routes --> Services
  Routes --> FormsViews
  Routes --> Utils
  Routes --> Constants
  Routes --> Types

  ApiV1 --> Services
  ApiV1 --> Schemas
  ApiV1 --> Utils
  ApiV1 --> Constants
  ApiV1 --> Types

  Tasks --> Services
  Tasks --> Schemas
  Tasks --> Utils
  Tasks --> Constants
  Tasks --> Types

  Services --> Repos
  Services --> Models
  Services --> Schemas
  Services --> Utils
  Services --> Errors
  Services --> Constants
  Services --> Types

  Repos --> Models
  Repos --> Utils
  Repos --> Constants
  Repos --> Types

  Models --> Utils
  Models --> Constants
  Models --> Types

  Settings --> Constants
  Settings --> Types
  Settings --> Utils
```

## 2. 核心规则(看这几条就够用)

- Routes/API 只能做 "HTTP 边界层": 解析入参/权限/调用 service/返回封套, 禁止在这里堆业务逻辑.
- Services 承载业务编排与事务边界, 可以调用 repositories/models, 但不应依赖 routes/api.
- Repositories 只做 read query 组合与数据访问细节, 不应依赖 services.
- Utils/Types/Constants/Errors 属于基础层, 禁止反向依赖上层(例如 utils import services).

## 3. 常见违规形态(快速自检)

> [!tip]
> 当你不确定边界是否被破坏时, 先用 `rg` 找 import 链路.

```bash
# services 不应 import routes/api
rg -n \"from app\\.routes|import app\\.routes|from app\\.api|import app\\.api\" app/services

# repositories 不应 import services/routes/api
rg -n \"from app\\.services|import app\\.services|from app\\.routes|import app\\.routes|from app\\.api|import app\\.api\" app/repositories

# utils 不应 import services/routes/api/repos
rg -n \"from app\\.services|from app\\.routes|from app\\.api|from app\\.repositories\" app/utils
```

## 4. 关联标准与入口

- 分层标准(SSOT): [[standards/backend/layer/README|后端分层标准]]
- 代码地图: [[architecture/project-structure]]
- 常见开发任务入口: [[architecture/developer-entrypoint]]

