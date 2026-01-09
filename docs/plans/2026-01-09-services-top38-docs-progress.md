# Services Top38 Docs Progress

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-09
> 更新: 2026-01-09
> 范围: `docs/Obsidian/Server/**`, `app/services/**`
> 关联: `docs/plans/2026-01-09-services-top38-docs.md`, `docs/reports/2026-01-08-services-complexity-report.md`, `docs/Obsidian/standards/doc/service-layer-documentation-standards.md`

## Milestones

- [x] Task 0: 计划与进度文档落盘
  - [x] `docs/plans/2026-01-09-services-top38-docs.md`
  - [x] `docs/plans/2026-01-09-services-top38-docs-progress.md`
- [x] Task 1: Server docs 索引
  - [x] `docs/Obsidian/Server/README.md`
- [x] Task 2: Accounts Sync 文档组
  - [x] `docs/Obsidian/Server/accounts-sync-overview.md`
  - [x] `docs/Obsidian/Server/accounts-sync-adapters.md`
  - [x] `docs/Obsidian/Server/accounts-permissions-facts-builder.md`
  - [x] 更新 `docs/Obsidian/Server/accounts-sync-permission-manager.md`（cross-link + 兼容兜底表补齐）
- [x] Task 3: Classification 文档组
  - [x] `docs/Obsidian/Server/accounts-classifications-write-service.md`
  - [x] `docs/Obsidian/Server/account-classification-orchestrator.md`
  - [x] `docs/Obsidian/Server/account-classification-dsl-v4.md`
- [x] Task 4: Aggregation / Capacity 文档组
  - [x] `docs/Obsidian/Server/aggregation-pipeline.md`
  - [x] `docs/Obsidian/Server/capacity-current-aggregation-service.md`
- [x] Task 5: Database Sync 文档组
  - [x] `docs/Obsidian/Server/database-sync-overview.md`
  - [x] `docs/Obsidian/Server/database-sync-adapters.md`
  - [x] `docs/Obsidian/Server/database-sync-table-sizes.md`
- [x] Task 6: Others 文档组
  - [x] `docs/Obsidian/Server/partition-services.md`
  - [x] `docs/Obsidian/Server/instances-write-and-batch.md`
  - [x] `docs/Obsidian/Server/cache-services.md`
  - [x] `docs/Obsidian/Server/tags-write-service.md`
  - [x] `docs/Obsidian/Server/scheduler-job-write-service.md`
  - [x] `docs/Obsidian/Server/connection-test-service.md`
  - [x] `docs/Obsidian/Server/credential-write-service.md`
  - [x] `docs/Obsidian/Server/user-write-service.md`
  - [x] `docs/Obsidian/Server/database-ledger-service.md`
  - [x] `docs/Obsidian/Server/sync-session-service.md`
- [x] Task 7: 全局收口
  - [x] 覆盖矩阵无遗漏（Top 38 全覆盖）
  - [x] 每篇都有“兼容/防御/回退/适配逻辑”表格（含清理条件）
  - [x] 关键图可读（循环折叠、无过深嵌套）

## Timeline（建议）

| Day | Date | Focus | Exit Criteria |
| --- | --- | --- | --- |
| D0 | 2026-01-09 | 计划/索引/骨架 | Task 1 DONE；至少 3 篇骨架可评审 |
| D1 | 2026-01-10 | Accounts Sync | Task 2 DONE |
| D2 | 2026-01-11 | Database Sync | Task 5 DONE |
| D3 | 2026-01-12 | Classification | Task 3 DONE |
| D4 | 2026-01-13 | Aggregation/Capacity + Others | Task 4/6 DONE |
| D5 | 2026-01-14 | 收口 | Task 7 DONE |
