---
title: Shared Kernel 编写规范
aliases:
  - shared-kernel-standards
tags:
  - standards
  - standards/backend
status: active
created: 2026-01-12
updated: 2026-01-12
owner: WhaleFall Team
scope: "`app/core/**` + shared kernel 风格代码"
related:
  - "[[standards/backend/README|后端标准索引]]"
  - "[[standards/backend/layer/README|后端分层标准(目录结构与依赖方向)]]"
  - "[[standards/backend/layer/constants-layer-standards|Constants 常量层编写规范]]"
  - "[[standards/backend/layer/types-layer-standards|Types 类型定义层编写规范]]"
  - "[[standards/backend/layer/utils-layer-standards|Utils 工具层编写规范]]"
---

# Shared Kernel 编写规范

> [!note] 说明
> Shared Kernel 指“跨层共享、稳定、且不依赖具体框架/外部基础设施”的核心代码。它不是一层业务层，而是被各层安全复用的内核。

## 目的

- 建立“跨层共享代码”的准入标准，避免 shared code 变成无边界的公共大杂烩。
- 固化依赖方向：shared kernel 不感知 HTTP/DB/框架；外层在边界处做适配。
- 降低耦合与循环依赖，让内核代码可单测、可静态检查、可复用。

## 在 WhaleFall 中的落点（仓库约定）

- **Shared Kernel（唯一路径）**：`app/core/**`
  - `app/core/exceptions.py`：异常（语义对象）
  - `app/core/constants/**`：不可变常量/枚举/静态映射（详见 [[standards/backend/layer/constants-layer-standards]]）
  - `app/core/types/**`：跨层类型契约/协议/结构（详见 [[standards/backend/layer/types-layer-standards]]）
- **shared-kernel-like utils（历史原因位于 utils，但必须保持“纯”）**
  - 例如：`app/utils/payload_converters.py`、`app/utils/time_utils.py`、`app/utils/version_parser.py`
  - 这类模块应同时遵循本规范与 [[standards/backend/layer/utils-layer-standards]] 的“纯工具”约束。

> [!important]
> 本仓库不提供 `app.core.constants` / `app.core.types` 的 re-export；所有调用方必须改用 `app.core.constants` / `app.core.types`。

## 规则（MUST/SHOULD/MAY）

### 1) 职责边界

- MUST: shared kernel 只承载“稳定契约/语义对象/纯工具”，不承载业务编排。
- MUST NOT: 引入 HTTP/Flask/Werkzeug 概念（例如 status code 映射、request context、Response）。
- MUST NOT: 引入数据库/事务概念（例如 `db.session`、ORM query、Repository）。
- SHOULD: 对外暴露最小稳定接口（函数/类），避免泄漏实现细节。

### 2) 依赖规则（关键）

原则：依赖只能指向更“内”的 shared kernel primitives，禁止反向依赖造成环。

- MUST: `app/core/exceptions.py` 允许依赖 `app/core/constants/**`、`app/core/types/**`。
- MUST NOT: `app/core/constants/**` 依赖 `app/core/types/**` 或 `app/core/exceptions.py`（constants 应保持最底层纯净）。
- SHOULD: `app/core/types/**` 可以依赖 `app/core/constants/**`，但 MUST NOT 依赖 `app/core/exceptions.py`（避免 shared kernel 内部环）。
- MUST NOT: shared kernel 依赖 `app.(api|routes|tasks|services|repositories|models|forms|views|settings|infra|schemas).*`。
- MAY: 标准库。
- SHOULD NOT: 引入重量级第三方库；如确需使用（例如纯解析库），必须在评审中说明理由与替代方案。

### 3) 稳定性与演进

- MUST: shared kernel 的公共 API 变更需做到“可追踪、可迁移、可回滚”，避免一次性破坏全局调用方。
- SHOULD: 优先“新增字段/新增函数”向前兼容，谨慎重命名/删字段（必要时提供过渡期 alias，并在迁移完成后删除）。

### 4) 放置决策（简单判断）

- 值/枚举/静态映射 → `app/core/constants/**`
- 结构/协议/TypedDict/类型别名 → `app/core/types/**`
- 语义对象（异常、值对象、跨层不变规则） → `app/core/**`
- 工具函数：
  - **纯工具**（不依赖框架/DB）→ 优先 `app/core/**`，允许暂留 `app/utils/**` 但必须标注并保持纯
  - **边界工具**（依赖 Flask/Werkzeug/structlog 等）→ 留在 `app/utils/**` 或 `app/infra/**`，不得被 shared kernel 依赖
