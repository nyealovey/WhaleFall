---
title: 后端标准索引
aliases:
  - backend-standards
tags:
  - standards
  - standards/backend
  - standards/index
status: active
created: 2025-12-25
updated: 2026-01-08
owner: WhaleFall Team
scope: 后端 standards 入口与索引
related:
  - "[[standards/README]]"
---

# 后端标准

本目录定义后端对外/对内契约的强约束标准(例如返回结构、错误消息口径、写操作边界、配置与迁移约束)。

## 索引

- [[standards/backend/api-response-envelope|API 响应封套(JSON Envelope)]]
- [[standards/backend/api-naming-standards|API 命名与路径规范(REST Resource Naming)]]
- [[standards/backend/api-contract-markdown-standards|API Contract Markdown 标准(SSOT)]]
- [[standards/backend/error-message-schema-unification|错误消息字段统一(error/message)]]
- [[standards/backend/request-payload-and-schema-validation|请求 payload 解析与 schema 校验]]
- [[standards/backend/action-endpoint-failure-semantics|Action endpoint failure semantics(business failure vs exception)]]
- [[standards/backend/write-operation-boundary|写操作事务边界(Write Operation Boundary)]]
- [[standards/backend/configuration-and-secrets|配置与密钥(Settings/.env/env.example)]]
- [[standards/backend/database-migrations|数据库迁移(Alembic/Flask-Migrate)]]
- [[standards/backend/sensitive-data-handling|敏感数据处理(脱敏/加密/导出)]]
- [[standards/backend/task-and-scheduler|任务与调度(APScheduler)]]
