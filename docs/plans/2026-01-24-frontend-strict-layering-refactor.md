# 前端全站严格分层重构 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 全站前端严格遵循 `Page Entry -> Views -> Stores -> Services`；页面不自维护业务 state；Views/Components 不私自 `new *Service()`；删除确定未使用的“状态/模块/兜底分支/迁移期兼容逻辑”。

**Architecture:** 以每个 `page_id` 的页面脚本作为 Page Entry（wiring only）：创建 service/store、订阅 store 事件、触发首屏 actions；Views/Components 只做 DOM/交互与渲染；Stores 维护业务状态与 actions（内部调用 services 并通过 mitt 广播）；Services 只做 API client 封装。全局/组件脚本同样适用：必须支持依赖注入（`configure(...)` 或 `createX({ store/service })`），禁止组件内部私自实例化业务 service。

**Tech Stack:** Flask(Jinja templates), 原生 JS modules(挂载 `window.*`), `mitt`, Grid.js + `Views.GridPage`, pytest(静态扫描类前端契约测试), ESLint(可选门禁)。

---

## 单一真源（SSOT）

- 迁移清单/状态：`docs/changes/refactor/layer/state-layer-inventory.md`
- 分层标准：
  - `docs/Obsidian/standards/ui/layer/README.md`
  - `docs/Obsidian/standards/ui/layer/views-layer-standards.md`
  - `docs/Obsidian/standards/ui/layer/stores-layer-standards.md`

---

## 当前状态（截至 2026-01-24）

### DONE（已严格落到 store/actions 或无需 store）

- 详见 `docs/changes/refactor/layer/state-layer-inventory.md` 的 `DONE` 行（多数页面已完成迁移）。

### 本日进展（已提交）

- `AdminPartitionsPage`：
  - `app/static/js/modules/views/admin/partitions/partition-list.js`：改为注入 `gridUrl`（组件不再 `new PartitionService()`）
  - `app/static/js/modules/views/admin/partitions/charts/partitions-chart.js`：删除 direct request fallback，强制依赖 `PartitionStoreInstance`
  - 新增前端契约单测（静态扫描）：`tests/unit/test_frontend_partition_list_injection_contracts.py`、`tests/unit/test_frontend_partitions_chart_requires_store.py`
- `TagSelector`：
  - `app/static/js/modules/views/components/tags/tag-selector-controller.js`：改为 DI-only（必须注入 store）
  - 页面入口注入 store：`accounts/ledgers.js`、`databases/ledgers.js`、`instances/list.js`
  - 新增前端契约单测：`tests/unit/test_frontend_tag_selector_injection_contracts.py`
- `CapacityStatsDataSource`：
  - `app/static/js/modules/views/components/charts/data-source.js`：改为 `createCapacityStatsDataSource({ service })` 工厂
  - `CapacityStats.Manager`：强制注入 `dataSource`，不再读全局单例
  - 新增前端契约单测：`tests/unit/test_frontend_capacity_data_source_injection_contracts.py`
- `CredentialsListPage`：
  - `credential-modals.js`：改为注入 store/actions；移除内部 service 构造
  - `credentials/list.js`：移除迁移期兜底，统一由 store 提供 gridUrl；保存后刷新 grid（不再 reload）
  - 新增前端契约单测：`tests/unit/test_frontend_credentials_strict_layering.py`
- `InstanceModals`：
  - 新增 `instance_crud_store.js`（InstanceService -> store/actions）
  - `instance-modals.js`：改为 DI-only（必须注入 store/actions），移除内部 `new InstanceService()` 与 `window.location.reload()`
  - 更新注入点：`instances/list.js`、`instances/detail.js`（list 刷新 grid；detail 保存后 reload）
  - 新增前端契约单测：`tests/unit/test_frontend_instance_modals_strict_injection_contracts.py`

### 收口状态（截至 2026-01-24）

- Pages：
  - `InstancesListPage` / `InstanceDetailPage` / `InstanceStatisticsPage`：已收口为 store/actions 驱动（移除 service 兜底）；新增契约单测 `tests/unit/test_frontend_instances_strict_layering_contracts.py`
  - `SchedulerPage`：SchedulerModals 改为 DI-only 注入 store；Page Entry 移除 try/catch 兜底；新增契约单测 `tests/unit/test_frontend_scheduler_strict_layering_contracts.py`

---

## 里程碑（Milestones）

- M0：SSOT 完整且可审查（inventory 持续更新 + 基础契约测试覆盖）
- M1：共享组件严格注入（tag-selector / capacity data-source / 各类 modals）+ 删除兼容/兜底
- M2：PARTIAL 页面收口为 DONE（Credentials / Scheduler / Capacity / Accounts&DB ledgers）
- M3：实例相关页面深水区（InstancesList/Statistics/Detail）按“状态下沉 + 组件注入”逐块收敛
- M4：门禁收口：Views/Components 禁止 `new *Service()`；禁止 fallback；全量扫描通过

---

## 进度表（建议：5~8 个工作日 + 缓冲）

> 今天是 2026-01-24（周六）；按工作日从 2026-01-26（周一）开始排期。每个单元完成后都要跑 `uv run pytest -m unit`，保持“小步提交、随时可合并”。

| 日期 | 目标 | 交付物（示例） | 验证 |
|---|---|---|---|
| 2026-01-26 | M0：补齐契约测试（Components 注入/禁 new Service） | 新增 `tests/unit/test_frontend_components_no_service_construction.py` 等 | `uv run pytest -m unit` |
| 2026-01-27 ~ 2026-01-28 | M1：TagSelector 组件严格注入 | `tag-selector-controller.js` 改为 DI-only；更新 3 个页面入口注入 store | `pytest -m unit` |
| 2026-01-29 | M1：CapacityStatsDataSource 严格注入 | `data-source.js` 改为 factory；capacity 页面入口注入 | `pytest -m unit` |
| 2026-01-30 | M2：CredentialsListPage 收口 | 移除 try/catch 兜底；credential-modals 改为注入 store/actions | `pytest -m unit` |
| 2026-02-02 | M2：SchedulerPage 收口 | 统一注入 + 去除兼容支路 | `pytest -m unit` |
| 2026-02-03 ~ 2026-02-06 | M3：Instances 系列收口（分块） | instance-modals DI-only；逐步把业务 state 下沉 store；删兜底 | `pytest -m unit` |
| 2026-02-09 | M4：全量扫描 + 删除确定未使用模块 | `rg` 扫描 0 命中；删文件后全量单测绿 | `uv run pytest -m unit` |

---

## 任务拆解（可直接执行）

### Task 1: Shared - TagSelector 改为严格注入（优先）

**Files:**
- Modify: `app/static/js/modules/views/components/tags/tag-selector-controller.js`
- Modify: `app/static/js/modules/views/accounts/ledgers.js`
- Modify: `app/static/js/modules/views/databases/ledgers.js`
- Modify: `app/static/js/modules/views/instances/list.js`
- Test: `tests/unit/test_frontend_tag_selector_injection_contracts.py`

**Step 1: 写会失败的契约测试**
- 断言 `tag-selector-controller.js` 不包含 `new TagManagementService`/`createTagManagementStore`。
- 断言 `TagSelectorHelper.setupForForm/setupForFilter` 必须接收 `store`（或 `getStore`）注入。

**Step 2: 跑测试确认失败**
- `uv run pytest -m unit tests/unit/test_frontend_tag_selector_injection_contracts.py -q`

**Step 3: 最小实现**
- `tag-selector-controller.js`：
  - 删除内部 `new TagManagementService(...)` 与 `createTagManagementStore(...)`。
  - options 必须传入 `store`（或 `getStore()`），缺依赖直接 throw（fail fast）。
  - 删除/最小化 `this.state`：优先从 `store.getState()` 取快照渲染；仅保留 UI 临时态（如 modal 打开/关闭）在 controller 内。
- 页面入口脚本：
  - 在调用 `TagSelectorHelper.setupForForm(...)` 前创建 `TagManagementStore` 并注入：
    - `createTagManagementStore({ service: new TagManagementService(), emitter: mitt() })`

**Step 4: 跑测试确认通过**
- `uv run pytest -m unit tests/unit/test_frontend_tag_selector_injection_contracts.py -q`
- `uv run pytest -m unit`

**Step 5: 提交**
- `git commit -m "refactor(ui): make tag selector DI-only"`

---

### Task 2: Shared - CapacityStatsDataSource 改为严格注入

**Files:**
- Modify: `app/static/js/modules/views/components/charts/data-source.js`
- Modify: `app/static/js/modules/views/components/charts/manager.js`
- Modify: `app/static/js/modules/views/capacity/databases.js`
- Modify: `app/static/js/modules/views/capacity/instances.js`
- Test: `tests/unit/test_frontend_capacity_data_source_injection_contracts.py`

**Step 1: 写会失败的契约测试**
- 断言 `data-source.js` 不包含 `new CapacityStatsService()`。

**Step 2: 跑测试确认失败**
- `uv run pytest -m unit tests/unit/test_frontend_capacity_data_source_injection_contracts.py -q`

**Step 3: 最小实现**
- `data-source.js` 改为 `createCapacityStatsDataSource({ service })`，并挂载到 `window.createCapacityStatsDataSource`。
- `manager.js` 改为接收 `dataSource`（构造参数或 `configure({ dataSource })`），不再直接读 `window.CapacityStatsDataSource`。
- capacity 页面入口创建 `service + dataSource` 并注入 manager。

**Step 4: 跑测试确认通过**
- `uv run pytest -m unit`

**Step 5: 提交**
- `git commit -m "refactor(ui): make capacity charts data source DI-only"`

---

### Task 3: CredentialsListPage 去兜底 + Modals 注入收口

**Files:**
- Modify: `app/static/js/modules/views/credentials/list.js`
- Modify: `app/static/js/modules/views/credentials/modals/credential-modals.js`
- Modify: `app/static/js/modules/stores/credentials_store.js`（如需补齐 create/update actions）
- Test: `tests/unit/test_frontend_credentials_page_strict_wiring.py`

**Step 1: 写会失败的契约测试**
- 断言 `credential-modals.js` 不包含 `new CredentialsService` 分支（或必须由 options 注入）。
- 断言 `list.js` 不包含“吞异常继续运行”的兜底初始化逻辑（例如创建失败后仍继续 mount）。

**Step 2: 实现**
- Page Entry（list.js）fail fast：依赖缺失直接 return。
- Modals 改为注入 `store/actions`（或注入 `credentialService` 且不允许内部 new）。
- 删除 `window.location.reload()`（如可行，改为触发 grid refresh；否则在 plan 中明确仍保留 reload 的原因）。

**Step 3: 测试 + 提交**
- `uv run pytest -m unit`
- `git commit -m "refactor(ui): make credentials page strict layering"`

---

### Task 4: Instances 系列页面收口（分批）

**Files:**
- Modify: `app/static/js/modules/views/instances/modals/instance-modals.js`
- Modify: `app/static/js/modules/views/instances/list.js`
- Modify: `app/static/js/modules/views/instances/statistics.js`
- Modify: `app/static/js/modules/views/instances/detail.js`
- Test: 追加静态契约测试（按页面拆）

**策略：**
- 先做“注入收口”（instance-modals DI-only），再做“业务 state 下沉”（页面拆大 store/actions）。
- 每次只推进一个页面/一个模块，确保可回滚、可提交。

---

### Task 5: 最终收口（门禁 + 清理）

**Step 1: 全量扫描**
```bash
rg -n \"\\bwindow\\.httpU\\b\" app/static/js/modules/views app/static/js/modules/stores
rg -n \"\\bnew\\s+[A-Za-z0-9]+Service\\b\" app/static/js/modules/views/components app/static/js/modules/views/**/modals
```

**Step 2: 删除“确定未使用”的模块**
- 以“模板无引用”为准（禁止猜测）。示例：
```bash
find app/static/js/modules -type f -name \"*.js\" | sed \"s|^app/static/||\" | sort > /tmp/all_modules_js.txt
rg -o \"filename=\\x27(js/(?:modules|common|core)/[^\\x27]+\\\\.js)\\x27\" -r '$1' app/templates -S --no-filename | sort -u > /tmp/referenced_js.txt
comm -23 /tmp/all_modules_js.txt /tmp/referenced_js.txt
```
- 删完跑：`uv run pytest -m unit`
