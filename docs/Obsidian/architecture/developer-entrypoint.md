---
title: 开发者入口(常见任务导航)
aliases:
  - developer-entrypoint
tags:
  - architecture
  - architecture/developer-entrypoint
  - developer
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 常见开发任务(API/task/UI/db adapter)导航与关键文档入口
related:
  - "[[architecture/project-structure]]"
  - "[[architecture/identity-access]]"
  - "[[standards/README|standards]]"
  - "[[reference/README|reference]]"
  - "[[operations/observability-ops]]"
  - "[[API/api-v1-api-contract|API v1 contract index]]"
  - "[[reference/development/new-feature-delivery|新增功能交付清单]]"
---

# 开发者入口(Developer entrypoint)

> [!note] 目标
> 让你在 30 秒内知道: 要改什么, 该去哪里改, 该看哪些标准, 怎么自检.

## 快速导航

- 新增/修改 API: [[#1 新增/修改 API(/api/v1)|1 新增/修改 API(/api/v1)]]
- 新增/修改后台任务: [[#2 新增/修改后台任务(task + scheduler)|2 新增/修改后台任务(task + scheduler)]]
- 新增/修改页面(UI): [[#3 新增/修改页面(UI)|3 新增/修改页面(UI)]]
- 新增数据库类型/适配器(db_type): [[#4 新增数据库类型/适配器(db_type)|4 新增数据库类型/适配器(db_type)]]

## 0. 通用入口(先看这些)

- 代码落点: [[architecture/project-structure|项目结构与代码落点]]
- 关键流程 SOP: [[architecture/flows/README|关键流程索引(flows)]]
- 认证与权限: [[architecture/identity-access|Identity & Access(认证/授权/RBAC/CSRF/JWT)]]
- 标准(SSOT): [[standards/README|standards]] -> [[standards/backend/README|backend]] / [[standards/ui/README|ui]] / [[standards/doc/README|doc]]
- 参考(查阅型): [[reference/README|reference]] -> [[reference/service/README|server]] / [[reference/config/README|config]] / [[reference/database/README|database]] / [[reference/security/README|security]] / [[reference/errors/README|errors]]
- 可观测与排障: [[operations/observability-ops|Observability Ops(日志字段/定位路径/会话与任务排障)]]
- 错误码对齐表: [[reference/errors/message-code-catalog|message_code/message_key catalog]]
- API curl cookbook: [[reference/examples/api-v1-cookbook|API v1 调用 cookbook(curl)]]
- API contract(SSOT): [[API/api-v1-api-contract|API v1 contract index]] + `docs/Obsidian/API/*-api-contract.md`
- 交付自检: [[reference/development/new-feature-delivery|新增功能交付清单]]
- 测试指南(仓库 docs): [[getting-started/testing-guide]]

## 1. 新增/修改 API(/api/v1)

### 1.1 先决定: resource vs action

- Resource: 用名词表示资源, 用 HTTP method 表达 CRUD.
- Action: 用 `/actions/<action>` 表达非 CRUD 动作(尤其是 side effect).
- 标准入口:
  - [[standards/backend/layer/api-layer-standards#API 命名与路径规范(REST Resource Naming)|API 命名与路径规范]]
  - [[standards/backend/action-endpoint-failure-semantics|Action endpoint failure semantics]]

### 1.2 先更新 contract(再写代码)

- 修改或新增 `docs/Obsidian/API/<domain>-api-contract.md` 中的 "Endpoints 总览" 表格.
- 如新增了新的 contract 文档, 同步更新 [[API/api-v1-api-contract|API v1 contract index]].
- 标准: [[standards/doc/api-contract-markdown-standards|API Contract Markdown 标准(SSOT)]]

### 1.3 落点与分层(代码)

- HTTP 层:
  - namespaces: `app/api/v1/namespaces/*.py`
  - RestX schema: `app/api/v1/restx_models/*.py`
  - Base helper: `app/api/v1/resources/base.py`(`BaseResource.safe_call`)
- 业务层: `app/services/**`
- 数据访问: `app/repositories/**`
- 模型: `app/models/**`

核心规则:

- 路由保持薄: 入参解析/权限/调用 service/返回封套.
- 写操作事务边界: [[standards/backend/write-operation-boundary|写操作事务边界]].
- 入参解析与 schema: [[standards/backend/request-payload-and-schema-validation|request payload and schema validation]].
- 错误封套与对外口径: [[standards/backend/error-message-schema-unification|error message schema unification]].

### 1.4 最小自检(按改动取子集)

- 单测: `uv run pytest -m unit`
- Ruff: `./scripts/ci/ruff-report.sh style`(或 `ruff check <paths>`)
- 类型: `make typecheck`

## 2. 新增/修改后台任务(task + scheduler)

### 2.1 落点(代码)

- 任务实现: `app/tasks/**`
- 调度器: `app/scheduler.py`
- job 常量: `app/core/constants/scheduler_jobs.py`

### 2.2 关键约束

- 必须在 `app.app_context()` 内运行(任务入口保证).
- 任务只做调度入口与可观测性字段, 业务逻辑下沉到 `app/services/**`.
- 事务边界与失败语义必须明确, 不要在 service 内 commit/rollback.

标准入口:

- [[standards/backend/task-and-scheduler|task and scheduler]]
- [[standards/backend/write-operation-boundary|写操作事务边界]]
- [[standards/backend/sensitive-data-handling|sensitive data handling]]

## 3. 新增/修改页面(UI)

### 3.1 落点(代码)

- 页面路由: `app/routes/**`
- 模板: `app/templates/**`
- 前端脚本:
  - modules: `app/static/js/modules/**`
  - legacy/common: `app/static/js/common/**`

### 3.2 常见场景入口

- Grid 列表页 wiring: [[standards/ui/grid-list-page-skeleton-guidelines|Grid list page skeleton 指南]]
- modules 分层: [[standards/ui/javascript-module-standards|前端模块化(modules)规范]] + [[standards/ui/layer/README|前端分层(layer)标准索引]]
- 异步任务反馈: [[standards/ui/async-task-feedback-guidelines|异步任务反馈规范]]
- 可复用组件 DOM id: [[standards/ui/component-dom-id-scope-guidelines|可复用组件 DOM id 作用域规范]]

### 3.3 最小自检(按改动取子集)

- JS 变更: `./scripts/ci/eslint-report.sh quick`
- 单测: `uv run pytest -m unit`

## 4. 新增数据库类型/适配器(db_type)

> [!warning] 说明
> 新增 db_type 通常不是单点改动, 需要同时覆盖 "连接" + "同步/采集" + "权限/差异" + "文档与门禁".

### 4.1 常见落点(按能力拆分)

- db_type 常量与展示: `app/core/constants/database_types.py`
- 连接适配器:
  - adapters: `app/services/connection_adapters/adapters/*.py`
  - factory/service: `app/services/connection_adapters/connection_factory.py`, `app/services/connection_adapters/connection_test_service.py`
- 账户同步适配器(accounts sync):
  - adapters: `app/services/accounts_sync/adapters/*.py`
  - factory: `app/services/accounts_sync/adapters/factory.py`
- 容量/数据库同步适配器(database sync):
  - adapters: `app/services/database_sync/adapters/*.py`
  - factory: `app/services/database_sync/adapters/factory.py`

### 4.2 对应文档(先读)

- 外部数据库账号权限要求: [[reference/database/database-permissions-overview|外部数据库账号权限要求]]
- 驱动与连接方式: [[reference/database/database-drivers|驱动与连接方式]]
- 服务层文档标准(补文档时): [[standards/doc/service-layer-documentation-standards|服务层文档标准]]

### 4.3 最小自检(按改动取子集)

- 单测: `uv run pytest -m unit`
- 类型: `make typecheck`
- 如涉及新依赖/环境变量: 走 `app/settings.py` 并更新 `env.example`(见 [[standards/backend/configuration-and-secrets|configuration and secrets]])
