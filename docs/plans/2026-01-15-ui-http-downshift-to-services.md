# UI HTTP Downshift To Services Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 将 `app/static/js/modules/views/**` 中的直连请求（`http.*("/api/...")` / `httpU.*(...)`）与 API path 拼接下沉到 `app/static/js/modules/services/**`，views/controller 只调用 service 方法，并消除 views 中对 `window.httpU`/`global.httpU` 的读取。

**Architecture:** 以 Services 层作为 API path 与网络调用的单一承载点；views/controller 通过 options 注入 service（或注入 Service 类 + httpClient），保留最小必要的兼容（支持旧调用方仍传 `options.http`，但 views 不再默认读取 `window.httpU`）。

**Tech Stack:** Vanilla JS(IIFE + window 挂载), ESLint/espree(AST 校验), 仓库 CI 脚本（`./scripts/ci/eslint-report.sh quick`）。

---

### Task 1: 为缺失的请求下沉补齐/扩展 Services

**Files:**
- Modify: `app/static/js/modules/services/tag_management_service.js`
- Create: `app/static/js/modules/services/accounts_statistics_service.js`

**Step 1: 为 TagManagementService 增加 tags CRUD 方法（get/create/update）**
- 目标：把 `TagModals` 与 `TagsIndex` 中 `/api/v1/tags` 的 get/post/put/delete 全部收敛到 service。

**Step 2: 新增 AccountsStatisticsService**
- 目标：把 `app/static/js/modules/views/accounts/statistics.js` 的 `global.httpU.get('/api/v1/accounts/statistics', ...)` 下沉到 service。

**Step 3: 运行基础校验**
- Run: `rg -n "/api/v1/accounts/statistics" app/static/js/modules/services`
- Expected: 命中 `accounts_statistics_service.js`。

---

### Task 2: UserModals 去 http.*，改为调用 UserService

**Files:**
- Modify: `app/static/js/modules/views/auth/modals/user-modals.js`
- Modify: `app/static/js/modules/views/auth/list.js`

**Step 1: 修改 UserModals 依赖为 userService 注入**
- `createController({ userService, ... })`；保留对旧 `options.http` 的兼容：如提供 `http` 则内部 `new UserService(http)`。

**Step 2: 将 user-modals.js 内的 `http.get/post/put('/api/v1/users...')` 替换为 `userService.getUser/createUser/updateUser`**

**Step 3: 修改调用方 auth/list.js**
- 在 Page Entry 内创建 `userService = new UserService()`（不再读取 `global.httpU`）
- `UserModals.createController({ userService, ... })`

**Step 4: 运行校验**
- Run: `rg -n "\\bhttp\\.(get|post|put|patch|delete)\\(" app/static/js/modules/views/auth/modals/user-modals.js`
- Expected: 0 命中

---

### Task 3: TagModals/TagsIndex 去 http.*，改为调用 TagManagementService

**Files:**
- Modify: `app/static/js/modules/views/tags/modals/tag-modals.js`
- Modify: `app/static/js/modules/views/tags/index.js`

**Step 1: 修改 TagModals 依赖为 tagService 注入**
- `createController({ tagService, ... })`；兼容旧 `options.http`（内部 `new TagManagementService(http)`）。

**Step 2: 将 tag-modals.js 内的 `http.get/post/put('/api/v1/tags...')` 替换为 `tagService.getTag/createTag/updateTag`**

**Step 3: 修改 tags/index.js**
- 创建 `tagService = new TagManagementService()`（不再读取 `global.httpU`）
- 初始化 TagModals 时传入 `tagService`
- 删除标签用 `tagService.deleteTag(tagId)`（替换 `http.delete('/api/v1/tags/...')`）

**Step 4: 运行校验**
- Run: `rg -n "\\bhttp\\.(get|post|put|patch|delete)\\(" app/static/js/modules/views/tags -S`
- Expected: 0 命中

---

### Task 4: 统一移除 views/controller 对 window.httpU/global.httpU 的读取（不改业务）

**Files (modify):**
- `app/static/js/modules/views/accounts/account-classification/index.js`
- `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js`
- `app/static/js/modules/views/admin/scheduler/index.js`
- `app/static/js/modules/views/components/charts/data-source.js`
- `app/static/js/modules/views/components/connection-manager.js`
- `app/static/js/modules/views/components/permissions/permission-viewer.js`
- `app/static/js/modules/views/components/tags/tag-selector-controller.js`
- `app/static/js/modules/views/credentials/list.js`
- `app/static/js/modules/views/credentials/modals/credential-modals.js`
- `app/static/js/modules/views/history/logs/logs.js`
- `app/static/js/modules/views/history/sessions/sync-sessions.js`
- `app/static/js/modules/views/instances/detail.js`
- `app/static/js/modules/views/instances/list.js`
- `app/static/js/modules/views/instances/statistics.js`
- `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js`
- `app/static/js/modules/views/instances/modals/instance-modals.js`
- `app/static/js/modules/views/dashboard/overview.js`
- `app/static/js/modules/views/admin/partitions/index.js`
- `app/static/js/modules/views/admin/partitions/charts/partitions-chart.js`
- `app/static/js/modules/views/tags/batch-assign.js`
- `app/static/js/modules/views/accounts/statistics.js`
- `app/static/js/modules/views/grid-page.js`

**Step 1: 仅做“依赖传递”调整**
- `new XxxService(global.httpU/window.httpU)` → `new XxxService()`（依赖 fallback 由 service 构造函数处理）
- `options.http = window.httpU` 默认值移除；改为（优先）`options.service` 注入；或（兼容）仅在显式传入 `options.http` 时才用它构造 service

**Step 2: PermissionViewer 去 API path 拼接**
- `permissionService.fetchAccountPermissions(accountId)` 取代默认 `/api/v1/...` 模板字符串与 `fetchByUrl`
- 同步修改 `instances/detail.js` 的调用，不再传 `apiUrl`

**Step 3: Accounts statistics refresh 下沉**
- `accounts/statistics.js` 改为调用 `AccountsStatisticsService.fetchStatistics()`（或同名方法）

**Step 4: 运行全局校验**
- Run: `rg -n \"\\bhttpU\\b\" app/static/js/modules/views -S`
- Expected: 0 命中（允许 services 内存在）

---

### Task 5: 运行 AST/门禁校验并收尾

**Files:**
- (no code changes expected)

**Step 1: 运行 ESLint 报告**
- Run: `./scripts/ci/eslint-report.sh quick`
- Expected: 0 error（如有 warning 记录并逐项修复）

**Step 2: 运行自定义 AST 校验（临时命令，不落盘）**
- 目标：
  - `app/static/js/modules/views/**` 中不存在对 `window.httpU`/`global.httpU` 的 MemberExpression
  - `app/static/js/modules/views/**` 中不存在 `http.(get/post/put/patch/delete)(...)` 的直接调用

**Step 3: 汇报变更点与验证结果**

