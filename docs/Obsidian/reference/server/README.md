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
updated: 2026-01-10
owner: WhaleFall Team
scope: app/services/** 的服务层实现解读文档索引
related:
  - "[[reference/README]]"
  - "[[architecture/flows/README]]"
  - "[[standards/doc/document-boundary-standards]]"
  - "[[standards/doc/service-layer-documentation-standards]]"
---

# Server 服务层文档索引

> [!note] 目标
> 本目录存放 `app/services/**` 的服务层实现解读文档(流程/失败语义/决策表/兼容兜底清单/图).

- 标准: [[standards/doc/service-layer-documentation-standards|服务层文档标准(Service Docs)]]
- 流程(SOP): [[architecture/flows/README]]
- 计划: `docs/plans/2026-01-09-services-top38-docs.md`
- 进度: `docs/plans/2026-01-09-services-top38-docs-progress.md`
- 复杂度报告: `docs/reports/2026-01-08-services-complexity-report.md`

> [!important] 去重原则
> Top 38 每个 `app/services/**` 文件只归属一个主文档(当前实现解读 SSOT). 其余位置仅做链接, 避免重复解释同一条链路.

## Auth

- [[reference/server/auth-services|Auth Services(Login/Change Password/Auth Me)]]

## Accounts

- [[reference/server/accounts-ledger-services|Accounts Ledger Services(台账列表/权限详情/变更历史)]]
- [[reference/server/accounts-statistics-read-service|Accounts Statistics Read Service(账户统计汇总)]]

## Accounts Sync

- [[reference/server/accounts-sync-overview|Accounts Sync 概览(编排 + 状态机)]]
- [[reference/server/accounts-sync-actions-service|Accounts Sync Actions Service(触发后台同步/单实例同步)]]
- [[reference/server/accounts-sync-adapters|Accounts Sync Adapters(SQL 分支 + 异常归一化)]]
- [[reference/server/accounts-permissions-facts-builder|Accounts Permissions Facts Builder(事实模型 + 规则表)]]
- [[reference/server/accounts-sync-permission-manager|AccountPermissionManager 权限同步(SSOT)]]

## Account Classification

- [[reference/server/accounts-classifications-read-service|Accounts Classifications Read Service(分类/规则/分配/权限选项)]]
- [[reference/server/accounts-classifications-write-service|Accounts Classifications Write Service]]
- [[reference/server/account-classification-orchestrator|Account Classification Orchestrator]]
- [[reference/server/account-classification-dsl-v4|Account Classification DSL v4]]
- [[reference/server/auto-classify-service|Auto Classify Service(自动分类 action 编排)]]

## Aggregation / Capacity

- [[reference/server/aggregation-pipeline|Aggregation Pipeline(SSOT)]]
- [[reference/server/capacity-current-aggregation-service|Capacity Current Aggregation Service]]
- [[reference/server/capacity-aggregations-read-services|Capacity Aggregations Read Services(聚合查询/summary)]]
- [[reference/server/instance-capacity-sync-actions-service|Instance Capacity Sync Actions Service(单实例容量同步)]]

## Database Sync

- [[reference/server/database-sync-overview|Database Sync 概览(编排 + filters)]]
- [[reference/server/database-sync-adapters|Database Sync Adapters(差异表)]]
- [[reference/server/database-sync-table-sizes|Database Sync Table Sizes]]

## Instances

- [[reference/server/instances-read-services|Instances Read Services(列表/详情/统计)]]
- [[reference/server/instances-write-and-batch|Instances Write + Batch]]
- [[reference/server/instances-connection-status-service|Instance Connection Status Service(连接状态推断)]]
- [[reference/server/instances-database-sizes-services|Instance Database Sizes Services(容量历史/表容量快照查询)]]

## Partitions

- [[reference/server/partition-services|Partition Services]]
- [[reference/server/partition-read-services|Partition Read/Statistics Services(分区 info/list/core-metrics)]]

## Scheduler

- [[reference/server/scheduler-actions-and-read-services|Scheduler Actions/Read Services(任务列表/详情/运行/重载)]]
- [[reference/server/scheduler-job-write-service|Scheduler Job Write Service]]

## Logs

- [[reference/server/history-logs-services|History Logs Services(日志列表/统计/模块/详情)]]

## Tags

- [[reference/server/tags-read-services|Tags Read Services(列表/options/categories)]]
- [[reference/server/tags-write-service|Tags Write Service]]
- [[reference/server/tags-bulk-actions-service|Tags Bulk Actions Service]]

## Users

- [[reference/server/users-read-services|Users Read Services(用户列表/统计)]]
- [[reference/server/user-write-service|User Write Service]]

## Credentials

- [[reference/server/credentials-list-service|Credentials List Service(凭据列表)]]
- [[reference/server/credential-write-service|Credential Write Service]]
- [[reference/server/connection-test-service|Connection Test Service]]

## Databases

- [[reference/server/database-ledger-service|Database Ledger Service]]

## Files

- [[reference/server/files-export-services|Files Export Services(CSV 导出与模板)]]

## Dashboard

- [[reference/server/dashboard-activities-service|Dashboard Activities Service(仪表板活动列表)]]

## Sessions

- [[reference/server/history-sessions-read-service|History Sessions Read Service(会话中心读取)]]
- [[reference/server/sync-session-service|Sync Session Service]]

## Common

- [[reference/server/filter-options-service|Filter Options Service(通用筛选器选项)]]
- [[reference/server/cache-services|Cache Services(缓存服务/清理动作)]]

## Health

- [[reference/server/health-checks-service|Health Checks Service(基础探活/基础设施健康)]]
