---
title: 新增功能交付清单
aliases:
  - new-feature-delivery-checklist
tags:
  - reference
  - reference/development
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: 新增功能(API/页面/异步任务/脚本/配置)的最小交付清单(面向提交/评审)
related:
  - "[[standards/README]]"
  - "[[standards/doc/changes-standards]]"
  - "[[standards/coding-standards]]"
  - "[[standards/naming-standards]]"
  - "[[standards/testing-standards]]"
  - "[[standards/backend/README]]"
  - "[[standards/ui/README]]"
---

# 新增功能交付清单

> [!important] SSOT
> 本文是"交付清单"(面向执行与查阅), 不是标准 SSOT.
> 规则与硬约束以 [[standards/README]] 及其索引文档为准.

## 适用范围

- 新增/扩展路由与页面: `app/routes/`, `app/views/`, `app/templates/`, `app/static/`
- 新增/扩展服务与任务: `app/services/`, `app/tasks/`, `app/scheduler.py`
- 新增/扩展协议与类型: `app/core/types/`, `docs/Obsidian/reference/`

## 交付清单

### A. 落点与复用

- [ ] 全仓检索(例如 `rg`)确认已有同类能力可复用/可扩展
- [ ] 新增代码按业务域落位, 避免跨目录散落(路由/服务/模板/静态资源同域归类)
- [ ] 命名与目录符合 [[standards/naming-standards]] 与相关域约定

### B. 后端(如涉及)

- [ ] 路由/API 保持薄, 编排下沉到 service: [[standards/backend/layer/README]]
- [ ] 写路径事务边界遵循 [[standards/backend/write-operation-boundary]]
- [ ] 对外错误口径与封套遵循:
  - [[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)]]
  - [[standards/backend/error-message-schema-unification]]
- [ ] 新增/变更 payload 解析与 schema 校验遵循 [[standards/backend/request-payload-and-schema-validation]]
- [ ] 新增/变更配置项走 `app/settings.py` 并更新 `env.example`: [[standards/backend/configuration-and-secrets]]
- [ ] 涉及迁移时遵循 [[standards/backend/database-migrations]]
- [ ] 涉及任务/调度时遵循 [[standards/backend/task-and-scheduler]]

### C. 前端/UI(如涉及)

- [ ] modules 分层(services/stores/views/ui)遵循:
  - [[standards/ui/layer/README]]
  - [[standards/ui/javascript-module-standards]]
- [ ] Grid 列表页 wiring 使用 `Views.GridPage` skeleton: [[standards/ui/grid-list-page-skeleton-guidelines]]
- [ ] 危险操作二次确认: [[standards/ui/danger-operation-confirmation-guidelines]]
- [ ] 异步任务反馈: [[standards/ui/async-task-feedback-guidelines]]
- [ ] 设计 Token 与颜色治理: [[standards/ui/design-token-governance-guidelines]] / [[standards/ui/color-guidelines]]

### D. 文档与变更记录

- [ ] `docs/changes/**` 新增/更新变更文档, 且 PR 描述链接到该文档: [[standards/doc/changes-standards]]
- [ ] 对外接口/配置/行为变化同步更新 `docs/Obsidian/reference/**`(如适用): [[reference/README]]
- [ ] 如新增了可复用约束, 评估是否需要上升为 standards(并补齐门禁/检查方式)

### E. 自检与门禁(按改动取子集)

> [!note] 说明
> 具体命令以 [[standards/coding-standards]] 与各领域标准为准.

- [ ] `make format`
- [ ] `ruff check <paths>`
- [ ] `make typecheck`
- [ ] `./scripts/ci/refactor-naming.sh --dry-run`
- [ ] 单元测试: `uv run pytest -m unit`(或最小相关用例集)
- [ ] 改动 `app/static/js` 时: `./scripts/ci/eslint-report.sh quick`

## 变更历史

- 2026-01-09: 从 `standards/new-feature-delivery-standard` 调整为 reference checklist, 避免将"执行清单"与"规范 SSOT"混写.

