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
updated: 2026-01-10
owner: WhaleFall Team
scope: 后端 standards 入口与索引
related:
  - "[[standards/README]]"
---

# 后端标准

本目录定义后端对外/对内契约的强约束标准(例如返回结构, 错误消息口径, 写操作边界, 配置与迁移约束).

## 关键入口(少量)

- [[standards/backend/layer/README|后端分层标准(目录结构与依赖方向)]]
- [[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)|API 响应封套(JSON Envelope)]]
- [[standards/backend/error-message-schema-unification|错误消息字段统一(error/message)]]
- [[standards/backend/configuration-and-secrets|配置与密钥(Settings/.env/env.example)]]
- [[standards/backend/database-migrations|数据库迁移(Alembic/Flask-Migrate)]]
- [[standards/backend/task-and-scheduler|任务与调度(APScheduler)]]

## 全量浏览(不维护手工清单)

```query
path:"standards/backend"
```
