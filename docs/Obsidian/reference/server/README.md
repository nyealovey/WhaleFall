---
title: Server 服务层文档索引
aliases:
  - server-docs
  - reference-server
tags:
  - reference
  - reference/server
  - reference/index
  - server
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: app/services/** 的服务层实现解读文档索引
related:
  - "[[reference/README]]"
  - "[[standards/doc/document-boundary-standards]]"
  - "[[standards/doc/service-layer-documentation-standards]]"
---

# Server 服务层文档索引

> [!note] 目标
> 本目录存放 `app/services/**` 的服务层实现解读文档(流程/失败语义/决策表/兼容兜底清单/图).

- 标准: [[standards/doc/service-layer-documentation-standards|服务层文档标准(Service Docs)]]
- 计划: `docs/plans/2026-01-09-services-top38-docs.md`
- 进度: `docs/plans/2026-01-09-services-top38-docs-progress.md`
- 复杂度报告: `docs/reports/2026-01-08-services-complexity-report.md`

> [!important] 去重原则
> Top 38 每个 `app/services/**` 文件只归属一个主文档(当前实现解读 SSOT). 其余位置仅做链接, 避免重复解释同一条链路.

## Accounts Sync

- [[reference/server/accounts-sync-overview|Accounts Sync 概览(编排 + 状态机)]]
- [[reference/server/accounts-sync-adapters|Accounts Sync Adapters(SQL 分支 + 异常归一化)]]
- [[reference/server/accounts-permissions-facts-builder|Accounts Permissions Facts Builder(事实模型 + 规则表)]]
- [[reference/server/accounts-sync-permission-manager|AccountPermissionManager 权限同步(SSOT)]]

## Account Classification

- [[reference/server/accounts-classifications-write-service|Accounts Classifications Write Service]]
- [[reference/server/account-classification-orchestrator|Account Classification Orchestrator]]
- [[reference/server/account-classification-dsl-v4|Account Classification DSL v4]]

## Aggregation / Capacity

- [[reference/server/aggregation-pipeline|Aggregation Pipeline(SSOT)]]
- [[reference/server/capacity-current-aggregation-service|Capacity Current Aggregation Service]]

## Database Sync

- [[reference/server/database-sync-overview|Database Sync 概览(编排 + filters)]]
- [[reference/server/database-sync-adapters|Database Sync Adapters(差异表)]]
- [[reference/server/database-sync-table-sizes|Database Sync Table Sizes]]

## Others

- [[reference/server/partition-services|Partition Services]]
- [[reference/server/instances-write-and-batch|Instances Write + Batch]]
- [[reference/server/cache-services|Cache Services]]
- [[reference/server/tags-write-service|Tags Write Service]]
- [[reference/server/scheduler-job-write-service|Scheduler Job Write Service]]
- [[reference/server/connection-test-service|Connection Test Service]]
- [[reference/server/credential-write-service|Credential Write Service]]
- [[reference/server/user-write-service|User Write Service]]
- [[reference/server/database-ledger-service|Database Ledger Service]]
- [[reference/server/sync-session-service|Sync Session Service]]
