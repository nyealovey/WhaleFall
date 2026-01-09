# Services Top38 Docs Progress

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-09
> 更新: 2026-01-09
> 范围: `docs/Obsidian/Server/**`, `app/services/**`
> 关联: `docs/plans/2026-01-09-services-top38-docs.md`, `docs/reports/2026-01-08-services-complexity-report.md`, `docs/Obsidian/standards/backend/service-layer-documentation-standards.md`

## Milestones

- [x] Task 0: 计划与进度文档落盘
  - [x] `docs/plans/2026-01-09-services-top38-docs.md`
  - [x] `docs/plans/2026-01-09-services-top38-docs-progress.md`
- [ ] Task 1: Server docs 索引
  - [ ] `docs/Obsidian/Server/README.md`
- [ ] Task 2: Accounts Sync 文档组
  - [ ] `docs/Obsidian/Server/accounts-sync-overview.md`
  - [ ] `docs/Obsidian/Server/accounts-sync-adapters.md`
  - [ ] `docs/Obsidian/Server/accounts-permissions-facts-builder.md`
  - [ ] 更新 `docs/Obsidian/Server/accounts-sync-permission-manager.md`（cross-link + 兼容兜底表补齐）
- [ ] Task 3: Classification 文档组
  - [ ] `docs/Obsidian/Server/accounts-classifications-write-service.md`
  - [ ] `docs/Obsidian/Server/account-classification-orchestrator.md`
  - [ ] `docs/Obsidian/Server/account-classification-dsl-v4.md`
- [ ] Task 4: Aggregation / Capacity 文档组
  - [ ] `docs/Obsidian/Server/aggregation-pipeline.md`
  - [ ] `docs/Obsidian/Server/capacity-current-aggregation-service.md`
- [ ] Task 5: Database Sync 文档组
  - [ ] `docs/Obsidian/Server/database-sync-overview.md`
  - [ ] `docs/Obsidian/Server/database-sync-adapters.md`
  - [ ] `docs/Obsidian/Server/database-sync-table-sizes.md`
- [ ] Task 6: Others 文档组
  - [ ] `docs/Obsidian/Server/partition-services.md`
  - [ ] `docs/Obsidian/Server/instances-write-and-batch.md`
  - [ ] `docs/Obsidian/Server/cache-services.md`
  - [ ] `docs/Obsidian/Server/tags-write-service.md`
  - [ ] `docs/Obsidian/Server/scheduler-job-write-service.md`
  - [ ] `docs/Obsidian/Server/connection-test-service.md`
  - [ ] `docs/Obsidian/Server/logs-export-service.md`
  - [ ] `docs/Obsidian/Server/credential-write-service.md`
  - [ ] `docs/Obsidian/Server/user-write-service.md`
  - [ ] `docs/Obsidian/Server/database-ledger-service.md`
  - [ ] `docs/Obsidian/Server/sync-session-service.md`
- [ ] Task 7: 全局收口
  - [ ] 覆盖矩阵无遗漏（Top 38 全覆盖）
  - [ ] 每篇都有“兼容/防御/回退/适配逻辑”表格（含清理条件）
  - [ ] 关键图可读（循环折叠、无过深嵌套）

## Timeline（建议）

| Day | Date | Focus | Exit Criteria |
| --- | --- | --- | --- |
| D0 | 2026-01-09 | 计划/索引/骨架 | Task 1 DONE；至少 3 篇骨架可评审 |
| D1 | 2026-01-10 | Accounts Sync | Task 2 DONE |
| D2 | 2026-01-11 | Database Sync | Task 5 DONE |
| D3 | 2026-01-12 | Classification | Task 3 DONE |
| D4 | 2026-01-13 | Aggregation/Capacity + Others | Task 4/6 DONE |
| D5 | 2026-01-14 | 收口 | Task 7 DONE |

