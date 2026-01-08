---
title: 规范标准(Standards)索引
aliases:
  - standards
tags:
  - standards
  - standards/index
status: active
created: 2025-12-25
updated: 2026-01-08
owner: WhaleFall Team
scope: WhaleFall standards 入口与索引
related:
  - "[[standards/documentation-standards]]"
---

# 规范标准

> [!info] Single source of truth
> `docs/Obsidian/standards/` 是 WhaleFall 规范标准的 SSOT. 新增/调整标准仅在此目录内进行, 不再使用旧 standards 目录.

## 总则

- [[standards/documentation-standards|文档结构与编写规范]]
- [[standards/halfwidth-character-standards|半角字符与全角字符禁用规范]]
- [[standards/changes-standards|变更文档(docs/changes)规范]]
- [[standards/coding-standards|编码规范]]
- [[standards/git-workflow-standards|Git 工作流与分支规范]]
- [[standards/naming-standards|命名规范]]
- [[standards/scripts-standards|脚本规范]]
- [[standards/testing-standards|测试规范]]
- [[standards/terminology|术语与用词标准]]
- [[standards/new-feature-delivery-standard|新增功能交付标准]]
- [[standards/version-update-guide|版本更新与版本漂移控制]]

## 后端

- [[standards/backend/README|后端标准索引]]
- [[standards/backend/api-response-envelope|API 响应封套(JSON Envelope)]]
- [[standards/backend/api-naming-standards|API 命名与路径规范(REST Resource Naming)]]
- [[standards/backend/api-contract-markdown-standards|API Contract Markdown 标准(SSOT)]]
- [[standards/backend/error-message-schema-unification|错误消息字段统一(error/message)]]
- [[standards/backend/action-endpoint-failure-semantics|Action endpoint failure semantics(business failure vs exception)]]
- [[standards/backend/write-operation-boundary|写操作事务边界(Write Operation Boundary)]]
- [[standards/backend/request-payload-and-schema-validation|请求 payload 解析与 schema 校验]]
- [[standards/backend/configuration-and-secrets|配置与密钥(Settings/.env/env.example)]]
- [[standards/backend/database-migrations|数据库迁移(Alembic/Flask-Migrate)]]
- [[standards/backend/sensitive-data-handling|敏感数据处理(脱敏/加密/导出)]]
- [[standards/backend/task-and-scheduler|任务与调度(APScheduler)]]

## UI

- [[standards/ui/README|UI 标准索引]]
- [[standards/ui/button-hierarchy-guidelines|按钮层级与状态]]
- [[standards/ui/close-button-accessible-name-guidelines|关闭按钮(btn-close)可访问名称]]
- [[standards/ui/color-guidelines|界面色彩与视觉疲劳控制]]
- [[standards/ui/danger-operation-confirmation-guidelines|高风险操作二次确认]]
- [[standards/ui/design-token-governance-guidelines|设计 Token 治理(CSS Variables)]]
- [[standards/ui/component-dom-id-scope-guidelines|组件 DOM ID 作用域]]
- [[standards/ui/layout-sizing-guidelines|布局尺寸与滚动规则]]
- [[standards/ui/grid-list-page-skeleton-guidelines|列表页骨架(loading/empty/error)]]
- [[standards/ui/grid-wrapper-performance-logging-guidelines|GridWrapper 性能与日志]]
- [[standards/ui/gridjs-migration-standard|Grid.js 列表页迁移标准]]
- [[standards/ui/javascript-module-standards|前端模块化(modules)规范]]
- [[standards/ui/async-task-feedback-guidelines|异步任务反馈指南]]
- [[standards/ui/pagination-sorting-parameter-guidelines|分页与排序参数规范]]
