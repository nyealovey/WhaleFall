# 前端全站严格分层重构 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 全站前端严格遵循 `Page Entry -> Views -> Stores -> Services`；页面不自维护业务 state；Views 不直连 `httpU`/不自行 `new *Service()`；删除确定未使用的“状态/模块/兜底分支”。

**Architecture:** 以 `page_id + page-loader` 为唯一入口：Page Entry 只做 wiring（组装 service/store/view，订阅 store 事件，触发首屏 actions）；Store 维护业务状态与 actions（内部调用 service，发 mitt 事件）；View 只做 DOM 与交互（订阅 store，渲染 UI）。全局/组件脚本同样适用：必须支持依赖注入（`configure(...)` 或 `createX({ store/service })`），禁止在组件内部私自实例化 service。

**Tech Stack:** Flask(Jinja templates), 原生 JS modules(挂载 `window.*`), `mitt`, Grid.js + `Views.GridPage`, pytest(静态扫描类前端契约测试), ESLint(可选门禁)。

---

## 现状清单（基于 2026-01-24 的仓库扫描）

### P0（硬违例，必须优先清掉）

- Views 直接访问 `httpU`：
  - `app/static/js/modules/views/accounts/classification_statistics.js:310`
  - `app/static/js/modules/views/auth/modals/change-password-modals.js:57`（由 `app/templates/base.html:310` 全局加载）

### P1（缺 Store：page_id 页面直连 Service）

- `LogsPage` → `app/static/js/modules/views/history/logs/logs.js:65`（`new global.LogsService()`）
- `AccountChangeLogsPage` → `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:49`
- `SyncSessionsPage` → `app/static/js/modules/views/history/sessions/sync-sessions.js:90`
- `AuthListPage` → `app/static/js/modules/views/auth/list.js:72`
- `TagsIndexPage` → `app/static/js/modules/views/tags/index.js:58`
- `DashboardOverviewPage` → `app/static/js/modules/views/dashboard/overview.js:40`
- `AccountsStatisticsPage` → `app/static/js/modules/views/accounts/statistics.js:32`
- `AccountClassificationStatisticsPage` → `app/static/js/modules/views/accounts/classification_statistics.js:26`（同时命中 P0）

### P2（已有 Store/模板已加载 Store，但仍存在“直连 service / fallback / 自维护业务 state”）

- 组件内私自 `new *Service()`（应改为注入 store/actions 或注入 service）：
  - `app/static/js/modules/views/admin/partitions/partition-list.js:71`（模板已加载 `partition_store.js`）
  - `app/static/js/modules/views/components/permissions/permission-viewer.js:22`（模板已加载 `instance_store.js` + `permission_service.js`）
  - `app/static/js/modules/views/components/charts/data-source.js:8`（容量统计页面共用）
- 明确的“无 store fallback”（与“全站严格”冲突，应删除）：
  - `app/static/js/modules/views/admin/partitions/charts/partitions-chart.js:621`（`createPartitionStore 未初始化，使用直接请求模式`）
- 组件/页面自维护业务 state（示例）：
  - `app/static/js/modules/views/components/tags/tag-selector-controller.js:199`（`this.state = ...` + 内部 `new TagManagementService`）
  - `app/static/js/modules/views/tags/index.js` 内直接用接口响应更新统计（应下沉 store）

---

## 里程碑（Milestones）

- M0：建立迁移进度 SSOT（inventory + 基础守护测试）
- M1：清理 P0（Views 不再出现 `httpU`）
- M2：补齐 P1 页面 store，并迁移页面逻辑到 store/actions
- M3：组件脚本严格依赖注入（P2），删除 fallback
- M4：收口门禁：无 `new *Service()` 出现在 Views/Components（允许存在于 Page Entry wiring）

---

## 进度表（建议：两周完成，含缓冲）

> 说明：今天是 2026-01-24（周六）；按工作日从 2026-01-26（周一）开始排期。每个单元完成后都要跑 `uv run pytest -m unit`，并保持“可随时合并”的干净状态（小步提交）。

| 日期 | 目标 | 交付物（示例） | 验证 |
|---|---|---|---|
| 2026-01-26 | M0：落地 inventory + 基础脚手架 | `docs/changes/refactor/layer/state-layer-inventory.md` | `uv run pytest -m unit` |
| 2026-01-27 | M1：干掉 change-password 的 `httpU` | 新 `auth_service.js`/`auth_store.js`；`change-password-modals.js` 只 wiring | `pytest -m unit` + `node --check` |
| 2026-01-28 | M1：干掉 classification_statistics 的 `httpU` | `account_classification_statistics_store.js` + service 注入/实例 options 下沉 | 同上 |
| 2026-01-29 | M2：LogsPage store 化 | `logs_store.js` + `logs.js` 迁移 | 同上 |
| 2026-01-30 | M2：AccountChangeLogsPage store 化 | `account_change_logs_store.js` + 页面迁移 | 同上 |
| 2026-02-02 | M2：SyncSessionsPage store 化 | `task_runs_store.js` + 页面迁移 | 同上 |
| 2026-02-03 | M2：AuthListPage store 化 | `users_store.js` + `auth/list.js` + `user-modals` 注入改造 | 同上 |
| 2026-02-04 | M2：TagsIndexPage store 化 | `tag_list_store.js` + `tags/index.js` + `tag-modals` 注入改造 | 同上 |
| 2026-02-05 | M2：Dashboard + AccountsStatistics store 化 | `dashboard_store.js` + `accounts_statistics_store.js` | 同上 |
| 2026-02-06 ~ 2026-02-10 | M3：组件注入 + 删 fallback + 收口门禁 | permission-viewer/partition-list/data-source/tag-selector 重构 | `pytest -m unit` + ESLint(可选) |
| 2026-02-11 ~ 2026-02-13 | M4：全量收口/清理 | 移除遗留“兜底/直连/重复状态”，更新文档 | 全量门禁 |

---

## 实施任务（Task Breakdown）

### Task 1: 建立迁移进度 SSOT（inventory）

**Files:**
- Create: `docs/changes/refactor/layer/state-layer-inventory.md`
- (Optional) Create: `docs/changes/refactor/layer/README.md`

**Step 1: 创建目录与 inventory 文档**
- 内容建议包含一张表：`page_id`、入口脚本、store 文件、是否已迁移、剩余违例（P0/P1/P2）。

**Step 2: 在每次页面迁移后更新 inventory**
- 每完成一个页面/组件：把状态从 `TODO` 改为 `DONE`，并记录关键文件路径。

**Step 3: 基础校验**
- 运行：`uv run pytest -m unit`

---

### Task 2: P0-1 修复（全局 change-password-modals 禁止 httpU）

**Files:**
- Create: `app/static/js/modules/services/auth_service.js`
- Create: `app/static/js/modules/stores/auth_store.js`
- Modify: `app/static/js/modules/views/auth/modals/change-password-modals.js`
- (Optional) Modify: `app/templates/base.html:310`（如需补脚本加载顺序）
- Test: `tests/unit/test_frontend_no_httpu_in_views.py`

**Step 1: 写一个会失败的契约测试（先锁定问题点）**
```python
from pathlib import Path

import pytest


@pytest.mark.unit
def test_change_password_modals_must_not_use_httpu() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/auth/modals/change-password-modals.js"
    content = path.read_text(encoding="utf-8", errors="ignore")
    assert "httpU" not in content, "change-password-modals.js 不得直接访问 window.httpU"
```

**Step 2: 跑测试确认失败**
- 运行：`uv run pytest -m unit tests/unit/test_frontend_no_httpu_in_views.py -q`
- 期望：FAIL，命中 `httpU`

**Step 3: 最小实现（按分层拆开）**
- `AuthService`：封装 `/api/v1/auth/change-password`、`/api/v1/auth/logout`（构造函数允许注入 httpClient，迁移期可 fallback 到 `window.httpU`）。
- `AuthStore`：只暴露 `actions.changePassword(payload)` / `actions.logout()`，内部调用 `AuthService`，并发 mitt 事件（`auth:loading`/`auth:error`/`auth:changed`）。
- `change-password-modals.js`：只做 wiring + DOM 交互，调用 store actions，不再读 `window.httpU`。

**Step 4: 跑测试确认通过**
- 运行：`uv run pytest -m unit tests/unit/test_frontend_no_httpu_in_views.py -q`
- 期望：PASS

**Step 5: 基础语法校验**
- 运行：`node --check app/static/js/modules/views/auth/modals/change-password-modals.js`

**Step 6: 提交**
```bash
git add tests/unit/test_frontend_no_httpu_in_views.py app/static/js/modules/services/auth_service.js app/static/js/modules/stores/auth_store.js app/static/js/modules/views/auth/modals/change-password-modals.js
git commit -m "refactor(ui): remove httpU from change-password modal via service/store"
```

---

### Task 3: P0-2 修复（AccountClassificationStatisticsPage 禁止 httpU + 页面 store 化）

**Files:**
- Create: `app/static/js/modules/stores/account_classification_statistics_store.js`
- Modify: `app/static/js/modules/services/instance_management_service.js`（新增 `fetchInstanceOptions` 或同等方法）
- Modify: `app/static/js/modules/views/accounts/classification_statistics.js`
- Modify: `app/templates/accounts/classification_statistics.html`（补 store 脚本加载顺序）
- Test: `tests/unit/test_frontend_no_httpu_in_views.py`

**Step 1: 追加一个会失败的契约测试（锁定 httpU）**
- 在 `tests/unit/test_frontend_no_httpu_in_views.py` 追加对 `classification_statistics.js` 的断言（同 Task 2 思路）。

**Step 2: 跑测试确认失败**
- 运行：`uv run pytest -m unit tests/unit/test_frontend_no_httpu_in_views.py -q`

**Step 3: 最小实现**
- `InstanceManagementService.fetchInstanceOptions({ dbType })`：封装 `/api/v1/instances/options`。
- `AccountClassificationStatisticsStore`：
  - state：`filters`（classificationId/periodType/dbType/instanceId/ruleId）、`instanceOptions`、`rulesCache`（如确认为业务态）、`loading/error`
  - actions：`loadInstanceOptions(dbType)`、`refreshAll(filters)`、`selectDbType(...)` 等
- 页面 `classification_statistics.js`：
  - 只读/写 UI（读取表单、绑定事件）
  - 所有请求/缓存/编排迁入 store actions
  - 通过 subscribe 驱动渲染（图表、规则列表、下拉选项）

**Step 4: 跑测试确认通过 + node check**
- `uv run pytest -m unit tests/unit/test_frontend_no_httpu_in_views.py -q`
- `node --check app/static/js/modules/views/accounts/classification_statistics.js`

**Step 5: 提交**
```bash
git add app/static/js/modules/stores/account_classification_statistics_store.js app/static/js/modules/services/instance_management_service.js app/static/js/modules/views/accounts/classification_statistics.js app/templates/accounts/classification_statistics.html tests/unit/test_frontend_no_httpu_in_views.py
git commit -m "refactor(ui): move account classification statistics to store and remove httpU"
```

---

### Task 4: Grid 列表页“通用迁移模板”（P1 多页面复用）

> 适用页面：`LogsPage`、`AccountChangeLogsPage`、`SyncSessionsPage`、`AuthListPage`、`TagsIndexPage`

**目标形态（统一约束）：**
- Page Entry：只创建 `service + store`，初始化 `GridPage.mount({...})`，把“动作按钮/模态/统计刷新”等绑定到 store actions。
- Store：提供：
  - `getGridUrl()`（或暴露 `gridUrl` 常量）
  - `actions.fetchDetail(id)`（如有详情弹窗）
  - `actions.fetchStats(filters)`（如页面顶部有统计卡/计数）
  - `actions.create/update/delete`（如页面有 CRUD）
  - `subscribe(event, handler)`（mitt 事件）
- View：不出现 `new *Service()`；不自维护“接口响应形成的业务状态”（例如 stats、详情 cache）。

**每个页面的执行步骤（重复执行即可）：**

**Step 1: 写一个会失败的契约测试**
- 断言该页面入口脚本不包含 `new .*Service(`（精准到具体 service 名称）。
- 断言模板引入对应 `js/modules/stores/<x>_store.js`。

**Step 2: 跑测试确认失败**
- `uv run pytest -m unit tests/unit/<your-test>.py -q`

**Step 3: 创建 store（最小可用）**
- 在 `app/static/js/modules/stores/<x>_store.js` 提供 `window.createXStore = function ({ service, emitter }) { ... }`。
- Store 内部只做：
  - `getState()` 返回快照
  - `actions.*` 包装 service
  - `emit('<domain>:updated')` 通知 view

**Step 4: 改页面入口脚本（只 wiring）**
- 在 `app/static/js/modules/views/...` 内删除 `new *Service()`，改为：
  - `const service = new XService()`
  - `const store = createXStore({ service })`
  - 订阅 store 事件更新 UI
  - 触发 `store.actions.init/load(...)`

**Step 5: 跑测试通过 + node check**
- `uv run pytest -m unit -q`
- `node --check <modified-js>`

**Step 6: 小步提交**
- `git commit -m "refactor(ui): <page> move service calls into store"`

---

### Task 5: Dashboard / 统计类页面迁移模板（P1 的非 GridPage 页面）

> 适用页面：`DashboardOverviewPage`、`AccountsStatisticsPage`

**执行要点：**
- Store 负责所有请求与数据规整（例如 `dashboardStore.actions.fetchCharts()` / `accountsStatisticsStore.actions.refresh()`）。
- 页面只订阅 store 的 `*:updated` 事件并渲染。

---

### Task 6: P2 组件脚本严格注入（permission-viewer / partition-list / capacity data-source / tag-selector）

**Files (representative):**
- Modify: `app/static/js/modules/views/components/permissions/permission-viewer.js`
- Modify: `app/static/js/modules/views/admin/partitions/partition-list.js`
- Modify: `app/static/js/modules/views/components/charts/data-source.js`
- Modify: `app/static/js/modules/views/components/tags/tag-selector-controller.js`
- Modify templates that include these scripts (按实际引用点)
- Test: 新增/扩展静态契约测试（禁止组件内 `new *Service()`；禁止 fallback 分支）

**原则：**
- 组件必须提供 `configure({ ...deps })` 或 `createX({ store/service })`。
- 禁止在组件内部实例化 service。
- 禁止“无 store fallback”（直接请求模式/静默降级）。

---

### Task 7: 最终收口（门禁与清理）

**Step 1: 全量扫描确认无残留**
- `rg -n "\\bhttpU\\b" app/static/js/modules/views`
- `rg -n "new\\s+[A-Za-z0-9]+Service\\(" app/static/js/modules/views`

**Step 2: 删除确定未使用模块**
- 以“无引用”为准（模板/入口/require 关系），再删文件；删除后跑 `uv run pytest -m unit`。

**Step 3: ESLint（可选但推荐）**
- 修复 `./scripts/ci/eslint-report.sh quick` 所需依赖后，把它纳入日常门禁。

---

## 执行方式（你确认后我就开始按任务推进）

计划已落盘到 `docs/plans/2026-01-24-frontend-strict-layering-refactor.md`。

你可以选：
1) 我按进度表从 2026-01-26 开始逐任务执行（每个任务一个小提交 + 跑 `uv run pytest -m unit`）。
2) 你指定优先级（例如先把 P0+LogsPage 完成），我按你的顺序推进。

