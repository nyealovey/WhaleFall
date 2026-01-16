# UI API URL Downshift To Services Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 将 `app/static/js/modules/views/**` 中所有 `"/api/..."` URL 字符串字面量下沉到 `app/static/js/modules/services/**`，views/page-entry 只通过 service 获取 URL 或发起业务动作；同时顺手把明显“危险兜底”的 `||` 改为更精确的 `??/显式判空`（仅限本次触达文件）。

**Architecture:** 以 services 层作为 API path 与默认 query 的单一承载点；Grid 列表页 `GridWrapper.server.url` 由 service 提供（string 或 resolver function），views 不再出现 `/api` 字面量。

**Tech Stack:** Vanilla JS(IIFE + window 挂载), ESLint/espree(AST 校验), 仓库 CI 脚本（`./scripts/ci/eslint-report.sh quick`）。

---

### Task 1: 为相关 Services 增加 “grid url / endpoint” 入口（承载 API path + 默认 query）

**Files (modify):**
- `app/static/js/modules/services/user_service.js`
- `app/static/js/modules/services/credentials_service.js`
- `app/static/js/modules/services/logs_service.js`
- `app/static/js/modules/services/sync_sessions_service.js`
- `app/static/js/modules/services/partition_service.js`
- `app/static/js/modules/services/instance_service.js`
- `app/static/js/modules/services/tag_management_service.js`
- `app/static/js/modules/services/capacity_stats_service.js`

**Files (create):**
- `app/static/js/modules/services/accounts_ledgers_service.js`

**Step 1: 为每个 service 提供 `getGridUrl()`（或语义更明确的方法名）**
- 目标：把 views 中的默认 `?sort=...&order=...` 也收敛进 service。

**Step 2: capacity stats endpoints 下沉**
- 目标：capacity pages 不再在 views 中写 `summaryEndpoint/trendEndpoint/...` 等 `/api` 字面量。
- 做法：在 `CapacityStatsService` 上暴露静态方法/常量（例如 `CapacityStatsService.buildInstanceApiConfig()` / `CapacityStatsService.buildDatabaseApiConfig()`），返回 `{ summaryEndpoint, trendEndpoint, ... }`。

**Step 3: accounts ledgers 新增 service**
- 目标：提供 `getGridUrl()` 与 `getExportUrl()`（以及必要的 query builder）。

---

### Task 2: 批量替换 views 中的 `/api` 字面量为 service 调用

**Files (modify):**
- `app/static/js/modules/views/accounts/ledgers.js`
- `app/static/js/modules/views/admin/partitions/partition-list.js`
- `app/static/js/modules/views/auth/list.js`
- `app/static/js/modules/views/capacity/databases.js`
- `app/static/js/modules/views/capacity/instances.js`
- `app/static/js/modules/views/components/tags/tag-selector-controller.js`
- `app/static/js/modules/views/credentials/list.js`
- `app/static/js/modules/views/history/logs/logs.js`
- `app/static/js/modules/views/history/sessions/sync-sessions.js`
- `app/static/js/modules/views/instances/list.js`
- `app/static/js/modules/views/tags/index.js`

**Step 1: Grid 列表页 server.url 改为 service 提供**
- `url: \"/api/...\"` → `url: <service>.getGridUrl()`

**Step 2: 组件默认 endpoints 改为 service 默认值**
- TagSelectorController：不再定义 `DEFAULT_ENDPOINTS`；仅对 `options.endpoints` 做安全过滤后传给 `new TagManagementService(..., endpoints)`，由 service 自己合并默认端点。

**Step 3: capacity pages 改为使用 CapacityStatsService 的 api config**
- `api: { summaryEndpoint: \"...\", ... }` → `api: CapacityStatsService.build...ApiConfig()`

---

### Task 3: AST 校验（不落盘脚本）

**Step 1: espree 扫描确认 views 内无 `/api/` 字面量**
- Run: `node - <<'NODE' ... NODE`
- Expected: 0 命中

---

### Task 4: 门禁与 ESLint

**Step 1: ESLint**
- Run: `./scripts/ci/eslint-report.sh quick`
- Expected: 0 error

