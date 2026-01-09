# Services Top38 Docs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 依据 `docs/Obsidian/standards/backend/service-layer-documentation-standards.md`，为 `docs/reports/2026-01-08-services-complexity-report.md` 的 `Top 38` 高复杂度 `app/services/**` 文件补齐“服务层文档”(去重、可维护、可交叉引用)。

**Architecture:** 采用“按域聚合 + 覆盖矩阵”的方式：
- `docs/Obsidian/Server/**` 存放 service docs（流程/失败语义/决策表/兼容兜底清单/图）。
- 避免为强耦合调用链重复写文档：同一域内由一个“overview/adapter/pipeline”文档覆盖多个实现文件；其余独立服务一文件一文档。
- 在本计划中维护 *Top 38 -> 文档* 覆盖矩阵，确保每个文件只归属一个主文档（其余地方只做链接）。

**Tech Stack:** Obsidian Markdown（frontmatter + wikilinks）、Mermaid（flow/sequence/state/ER 简化）、表格（决策表/兼容兜底清单）。

---

## 文档清单(去重后)

> 说明：以下为“最佳实践目标文档集合”，并非 38 篇；通过聚合覆盖避免重复。

- `docs/Obsidian/Server/README.md`（Server docs 索引）
- Accounts Sync
  - `docs/Obsidian/Server/accounts-sync-overview.md`
  - `docs/Obsidian/Server/accounts-sync-adapters.md`
  - `docs/Obsidian/Server/accounts-permissions-facts-builder.md`
  - `docs/Obsidian/Server/accounts-sync-permission-manager.md`（已存在：仅补齐 cross-link/兼容清单时更新）
- Classification
  - `docs/Obsidian/Server/accounts-classifications-write-service.md`
  - `docs/Obsidian/Server/account-classification-orchestrator.md`
  - `docs/Obsidian/Server/account-classification-dsl-v4.md`
- Aggregation / Capacity
  - `docs/Obsidian/Server/aggregation-pipeline.md`
  - `docs/Obsidian/Server/capacity-current-aggregation-service.md`
- Database Sync
  - `docs/Obsidian/Server/database-sync-overview.md`
  - `docs/Obsidian/Server/database-sync-adapters.md`
  - `docs/Obsidian/Server/database-sync-table-sizes.md`
- Others
  - `docs/Obsidian/Server/partition-services.md`
  - `docs/Obsidian/Server/instances-write-and-batch.md`
  - `docs/Obsidian/Server/cache-services.md`
  - `docs/Obsidian/Server/tags-write-service.md`
  - `docs/Obsidian/Server/scheduler-job-write-service.md`
  - `docs/Obsidian/Server/connection-test-service.md`
  - `docs/Obsidian/Server/credential-write-service.md`
  - `docs/Obsidian/Server/user-write-service.md`
  - `docs/Obsidian/Server/database-ledger-service.md`
  - `docs/Obsidian/Server/sync-session-service.md`

---

## 覆盖矩阵(Top 38 -> 主文档)

| Rank | File | 主文档(SSOT) |
| --- | --- | --- |
| 1 | `app/services/accounts_sync/permission_manager.py` | `docs/Obsidian/Server/accounts-sync-permission-manager.md` |
| 2 | `app/services/accounts_sync/adapters/sqlserver_adapter.py` | `docs/Obsidian/Server/accounts-sync-adapters.md` |
| 3 | `app/services/accounts/account_classifications_write_service.py` | `docs/Obsidian/Server/accounts-classifications-write-service.md` |
| 4 | `app/services/aggregation/aggregation_service.py` | `docs/Obsidian/Server/aggregation-pipeline.md` |
| 5 | `app/services/aggregation/instance_aggregation_runner.py` | `docs/Obsidian/Server/aggregation-pipeline.md` |
| 6 | `app/services/aggregation/database_aggregation_runner.py` | `docs/Obsidian/Server/aggregation-pipeline.md` |
| 7 | `app/services/capacity/current_aggregation_service.py` | `docs/Obsidian/Server/capacity-current-aggregation-service.md` |
| 8 | `app/services/database_sync/table_size_coordinator.py` | `docs/Obsidian/Server/database-sync-table-sizes.md` |
| 9 | `app/services/accounts_sync/accounts_sync_service.py` | `docs/Obsidian/Server/accounts-sync-overview.md` |
| 10 | `app/services/accounts_sync/adapters/mysql_adapter.py` | `docs/Obsidian/Server/accounts-sync-adapters.md` |
| 11 | `app/services/partition_management_service.py` | `docs/Obsidian/Server/partition-services.md` |
| 12 | `app/services/accounts_sync/coordinator.py` | `docs/Obsidian/Server/accounts-sync-overview.md` |
| 13 | `app/services/accounts_sync/adapters/postgresql_adapter.py` | `docs/Obsidian/Server/accounts-sync-adapters.md` |
| 14 | `app/services/account_classification/orchestrator.py` | `docs/Obsidian/Server/account-classification-orchestrator.md` |
| 15 | `app/services/instances/batch_service.py` | `docs/Obsidian/Server/instances-write-and-batch.md` |
| 16 | `app/services/database_sync/adapters/mysql_adapter.py` | `docs/Obsidian/Server/database-sync-adapters.md` |
| 17 | `app/services/accounts_sync/adapters/oracle_adapter.py` | `docs/Obsidian/Server/accounts-sync-adapters.md` |
| 18 | `app/services/sync_session_service.py` | `docs/Obsidian/Server/sync-session-service.md` |
| 19 | `app/services/database_sync/table_size_adapters/oracle_adapter.py` | `docs/Obsidian/Server/database-sync-table-sizes.md` |
| 20 | `app/services/account_classification/dsl_v4.py` | `docs/Obsidian/Server/account-classification-dsl-v4.md` |
| 21 | `app/services/database_sync/coordinator.py` | `docs/Obsidian/Server/database-sync-overview.md` |
| 22 | `app/services/partition/partition_read_service.py` | `docs/Obsidian/Server/partition-services.md` |
| 23 | `app/services/cache/cache_actions_service.py` | `docs/Obsidian/Server/cache-services.md` |
| 24 | `app/services/tags/tag_write_service.py` | `docs/Obsidian/Server/tags-write-service.md` |
| 25 | `app/services/scheduler/scheduler_job_write_service.py` | `docs/Obsidian/Server/scheduler-job-write-service.md` |
| 26 | `app/services/database_sync/inventory_manager.py` | `docs/Obsidian/Server/database-sync-overview.md` |
| 27 | `app/services/accounts_permissions/facts_builder.py` | `docs/Obsidian/Server/accounts-permissions-facts-builder.md` |
| 28 | `app/services/cache_service.py` | `docs/Obsidian/Server/cache-services.md` |
| 29 | `app/services/connection_adapters/adapters/oracle_adapter.py` | `docs/Obsidian/Server/connection-test-service.md` |
| 30 | `app/services/instances/instance_write_service.py` | `docs/Obsidian/Server/instances-write-and-batch.md` |
| 32 | `app/services/database_sync/adapters/oracle_adapter.py` | `docs/Obsidian/Server/database-sync-adapters.md` |
| 33 | `app/services/credentials/credential_write_service.py` | `docs/Obsidian/Server/credential-write-service.md` |
| 34 | `app/services/connection_adapters/connection_test_service.py` | `docs/Obsidian/Server/connection-test-service.md` |
| 35 | `app/services/users/user_write_service.py` | `docs/Obsidian/Server/user-write-service.md` |
| 36 | `app/services/ledgers/database_ledger_service.py` | `docs/Obsidian/Server/database-ledger-service.md` |
| 37 | `app/services/database_sync/database_filters.py` | `docs/Obsidian/Server/database-sync-overview.md` |
| 38 | `app/services/connection_adapters/adapters/sqlserver_adapter.py` | `docs/Obsidian/Server/connection-test-service.md` |

---

### Task 1: 建立 Server docs 索引页

**Files:**
- Create: `docs/Obsidian/Server/README.md`
- Modify: `docs/plans/README.md`

**Step 1: 输出索引结构**
- 索引页按域分组列出所有 `docs/Obsidian/Server/*.md`（含本文档清单），并链接到 `service-layer-documentation-standards.md`。

**Step 2: 把本计划加入 plans 索引**
- 在 `docs/plans/README.md` 增加本计划与 progress 的入口链接。

---

### Task 2: Accounts Sync 文档组（overview + adapters + facts）

**Files:**
- Create: `docs/Obsidian/Server/accounts-sync-overview.md`
- Create: `docs/Obsidian/Server/accounts-sync-adapters.md`
- Create: `docs/Obsidian/Server/accounts-permissions-facts-builder.md`
- Modify: `docs/Obsidian/Server/accounts-sync-permission-manager.md`

**Step 1: 先写最小可扫描骨架**
- 按 `service-layer-documentation-standards.md` 的“必填结构”建立章节与表格占位。

**Step 2: 按复杂度报告补齐图与表**
- `accounts-sync-overview.md`: 泳道流程图 + Session/Record 状态机。
- `accounts-sync-adapters.md`: 数据流图 + SQL 分支/异常流程（用表格集中差异，避免每个 adapter 重复写）。
- `accounts-permissions-facts-builder.md`: 事实模型 schema + 决策表(事实构建规则)。

**Step 3: 建立 cross-link，避免重复**
- `accounts-sync-permission-manager.md` 只保留 PermissionSync 的 SSOT，facts 细节链接到 `accounts-permissions-facts-builder.md`。

---

### Task 3: Account Classification 文档组（write + orchestrator + DSL v4）

**Files:**
- Create: `docs/Obsidian/Server/accounts-classifications-write-service.md`
- Create: `docs/Obsidian/Server/account-classification-orchestrator.md`
- Create: `docs/Obsidian/Server/account-classification-dsl-v4.md`

**Step 1: 建骨架 + 入口定位**
- 明确入口方法、调用方、DB/Cache/外部依赖、失败语义与事务边界。

**Step 2: 去重分工**
- `dsl-v4` 只写 DSL 语义/AST/错误口径与规则表；`orchestrator` 只写编排与匹配优先级；`write-service` 只写写入边界与校验/归一化。

---

### Task 4: Aggregation / Capacity 文档组

**Files:**
- Create: `docs/Obsidian/Server/aggregation-pipeline.md`
- Create: `docs/Obsidian/Server/capacity-current-aggregation-service.md`

**Step 1: aggregation 以“流水线”为 SSOT**
- 合并覆盖 `aggregation_service.py` + 两个 runner；用数据流图说明采集->聚合->落库->错误路径。

**Step 2: capacity 补齐状态机**
- Session/Record 状态与关键失败语义（重试/部分成功等）写清。

---

### Task 5: Database Sync 文档组（overview + adapters + table sizes）

**Files:**
- Create: `docs/Obsidian/Server/database-sync-overview.md`
- Create: `docs/Obsidian/Server/database-sync-adapters.md`
- Create: `docs/Obsidian/Server/database-sync-table-sizes.md`

**Step 1: overview 聚合 coordinator/filter/inventory**
- 泳道流程图：编排/分发/汇总；决策表：`database_filters.py` 参数->查询片段。

**Step 2: adapters 集中差异**
- 表格列出 MySQL/Oracle 行为差异、异常归一化、SQL 分支与限制。

**Step 3: table sizes 独立成链路**
- 数据流图：采集->upsert->cleanup；列出表结构与清理策略。

---

### Task 6: Others（Partition/Instances/Cache/…）

**Files:**
- Create: `docs/Obsidian/Server/partition-services.md`
- Create: `docs/Obsidian/Server/instances-write-and-batch.md`
- Create: `docs/Obsidian/Server/cache-services.md`
- Create: `docs/Obsidian/Server/tags-write-service.md`
- Create: `docs/Obsidian/Server/scheduler-job-write-service.md`
- Create: `docs/Obsidian/Server/connection-test-service.md`
- Create: `docs/Obsidian/Server/credential-write-service.md`
- Create: `docs/Obsidian/Server/user-write-service.md`
- Create: `docs/Obsidian/Server/database-ledger-service.md`
- Create: `docs/Obsidian/Server/sync-session-service.md`

**Step 1: 每篇都以“失败语义 + 兼容兜底清单”为核心**
- 不追求一次写满：先把入口/调用方/事务边界/失败语义/兼容兜底表写齐，再补图。

---

### Task 7: 全局审查与收口

**Files:**
- Modify: `docs/Obsidian/Server/*.md`

**Step 1: 统一 frontmatter 与相关链接**
- `scope` 必须能定位到主实现文件；`related` 只指向 SSOT（避免引用链爆炸）。

**Step 2: 兼容/防御/回退/适配清单完整**
- 每篇文档的 4.7 表格必须包含：`位置(文件:行号)`、类型、描述、触发条件、清理条件/期限。
