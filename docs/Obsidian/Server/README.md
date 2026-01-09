# Server 服务层文档索引

> [!note] 目标
> 本目录存放 `app/services/**` 的服务层文档(流程/失败语义/决策表/兼容兜底清单/图).

- 标准: [[standards/backend/service-layer-documentation-standards|服务层文档标准(Service Docs)]]
- 计划: `docs/plans/2026-01-09-services-top38-docs.md`
- 进度: `docs/plans/2026-01-09-services-top38-docs-progress.md`
- 复杂度报告: `docs/reports/2026-01-08-services-complexity-report.md`

> [!important] 去重原则
> Top 38 每个 `app/services/**` 文件只归属一个主文档(SSOT). 其余位置仅做链接, 避免重复解释同一条链路.

## Accounts Sync

- [[Server/accounts-sync-overview|Accounts Sync 概览(编排 + 状态机)]]
- [[Server/accounts-sync-adapters|Accounts Sync Adapters(SQL 分支 + 异常归一化)]]
- [[Server/accounts-permissions-facts-builder|Accounts Permissions Facts Builder(事实模型 + 规则表)]]
- [[Server/accounts-sync-permission-manager|AccountPermissionManager 权限同步(SSOT)]]

## Account Classification

- [[Server/accounts-classifications-write-service|Accounts Classifications Write Service]]
- [[Server/account-classification-orchestrator|Account Classification Orchestrator]]
- [[Server/account-classification-dsl-v4|Account Classification DSL v4]]

## Aggregation / Capacity

- [[Server/aggregation-pipeline|Aggregation Pipeline(SSOT)]]
- [[Server/capacity-current-aggregation-service|Capacity Current Aggregation Service]]

## Database Sync

- [[Server/database-sync-overview|Database Sync 概览(编排 + filters)]]
- [[Server/database-sync-adapters|Database Sync Adapters(差异表)]]
- [[Server/database-sync-table-sizes|Database Sync Table Sizes]]

## Others

- [[Server/partition-services|Partition Services]]
- [[Server/instances-write-and-batch|Instances Write + Batch]]
- [[Server/cache-services|Cache Services]]
- [[Server/tags-write-service|Tags Write Service]]
- [[Server/scheduler-job-write-service|Scheduler Job Write Service]]
- [[Server/connection-test-service|Connection Test Service]]
- [[Server/logs-export-service|Logs Export Service]]
- [[Server/credential-write-service|Credential Write Service]]
- [[Server/user-write-service|User Write Service]]
- [[Server/database-ledger-service|Database Ledger Service]]
- [[Server/sync-session-service|Sync Session Service]]
