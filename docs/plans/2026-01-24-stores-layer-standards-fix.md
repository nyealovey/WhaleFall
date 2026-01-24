# Stores Layer Standards Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 `app/static/js/modules/stores/**` 全量满足 `docs/Obsidian/standards/ui/layer/stores-layer-standards.md` 的 MUST 约束(错误口径 + destroy 清理), 并落实 PartitionStore "refresh 失败允许 resolve 但必须 emit error" 的策略B.

**Architecture:** 针对每个 store 做最小改动: 补齐缺失的 `.catch(handleError)+throw` 路径, 并将 `destroy()` 重置为接近初始态. PartitionStore 的后置 refresh 保持 resolve, 但通过 `partitions:error` 事件暴露 refresh 失败(含 meta 标记 nonBlocking).

**Tech Stack:** Vanilla JS(IIFE) + mitt + eslint

参考:

- 标准(SSOT): `docs/Obsidian/standards/ui/layer/stores-layer-standards.md`
- 审计/进度表: `docs/changes/refactor/layer/001-stores-layer-standards-progress.md`

### Task 1: 补齐 logs/accountChangeLogs 详情 actions 的错误口径

**Files:**
- Modify: `app/static/js/modules/stores/logs_store.js:181`
- Modify: `app/static/js/modules/stores/account_change_logs_store.js:189`

**Step 1: 写入最小实现(仅补 catch)**

- `logs_store.js`:
  - `actions.loadLogDetail()` 增加 `.catch(...)`:
    - 调用 `handleError(error, { action: "loadLogDetail", logId: id })`
    - `throw error`
- `account_change_logs_store.js`:
  - `actions.loadDetail()` 增加 `.catch(...)`:
    - 调用 `handleError(error, { action: "loadDetail", logId: id })`
    - `throw error`

**Step 2: 运行 lint**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: exit 0

### Task 2: 补齐 accountClassification store 的 actions 错误口径

**Files:**
- Modify: `app/static/js/modules/stores/account_classification_store.js:275`
- Modify: `app/static/js/modules/stores/account_classification_store.js:326`
- Modify: `app/static/js/modules/stores/account_classification_store.js:377`
- Modify: `app/static/js/modules/stores/account_classification_store.js:383`

**Step 1: 写入最小实现(仅补 catch + 成功清 lastError)**

- 为以下 actions 增加 `.catch(...)` 并 rethrow:
  - `fetchClassificationDetail`
  - `fetchRuleDetail`
  - `triggerAutomation`
  - `fetchPermissions`
- catch 内统一:
  - `handleError(error, { action: "<actionName>", ... })`
  - `throw error`
- then 成功路径补:
  - `state.lastError = null`

**Step 2: 运行 lint**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: exit 0

### Task 3: 补齐 destroy() 的内部状态清理

**Files:**
- Modify: `app/static/js/modules/stores/scheduler_store.js:335`
- Modify: `app/static/js/modules/stores/partition_store.js:460`
- Modify: `app/static/js/modules/stores/instance_store.js:815`
- Modify: `app/static/js/modules/stores/account_classification_store.js:401`
- Modify: `app/static/js/modules/stores/tag_batch_store.js:450`
- Modify: `app/static/js/modules/stores/tag_management_store.js:573`

**Step 1: 写入最小实现(不引入新行为, 仅重置字段)**

- `scheduler_store.js` destroy:
  - 清 jobs, reset stats/loading/lastError
- `partition_store.js` destroy:
  - 清 partitions, reset stats/metrics/loading/lastError
- `instance_store.js` destroy:
  - 清 selection/instances/availableInstanceIds
  - reset filters/stats/loading/operations/uploadResult/lastError
- `account_classification_store.js` destroy:
  - reset classifications/rulesByDbType/loading/lastError
- `tag_batch_store.js` destroy:
  - reset mode/instancesByDbType/tagsByCategory/selected*/loading/lastError/lastResult
- `tag_management_store.js` destroy:
  - reset categories/tags/filteredTags/filters/selection/stats/loading/lastError, 并清 pendingSelection

**Step 2: 运行 lint**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: exit 0

### Task 4: PartitionStore 后置 refresh 失败策略B落地

**Files:**
- Modify: `app/static/js/modules/stores/partition_store.js:326`
- Modify: `app/static/js/modules/stores/partition_store.js:384`

**Step 1: 调整 createPartition/cleanupPartitions 的 refresh 调用**

- 保持主动作失败仍 reject.
- 主动作成功后:
  - 调用 `actions.loadInfo({ silent: true, nonBlocking: true, step: "refreshInfo", action: "<caller>" })`
  - `.catch(() => result)` 允许 resolve
- 确保 refresh 失败时会 emit `partitions:error`:
  - 在 `loadInfo` catch 的 meta 中带上 `nonBlocking: true` 与 `step: "refreshInfo"`

**Step 2: 运行 lint**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: exit 0

### Task 5: 最终复核(回归扫描)

**Files:**
- Modify: `docs/changes/refactor/layer/001-stores-layer-standards-progress.md`(勾选已完成项, 可选)

**Step 1: 复核 grep**

Run: `rg -n "document\\.|DOMHelpers|toast\\.|\\bhttpU\\." app/static/js/modules/stores`
Expected: 无输出

Run: `rg -n "partitions:error" app/static/js/modules/stores/partition_store.js`
Expected: 至少存在一个 emit 点

**Step 2: 更新进度表(可选)**

- 将本次修复的 store 标为 PASS 或在表格中勾选 DONE.

**Step 3: 运行 lint(最终一次)**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: exit 0

