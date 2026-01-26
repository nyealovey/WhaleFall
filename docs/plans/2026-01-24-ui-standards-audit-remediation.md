# UI Standards Audit Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按 `docs/reports/2026-01-24-ui-standards-audit-report.md` 的“违规(需要修复)”清单完成整改，并补齐必要的静态契约测试/门禁，避免回归。

**Architecture:**
- 以“最小可证明修复”为原则：每个违规点都对应一个可重复执行的静态契约测试（JS 用 AST，模板用 Jinja2 AST，CSS 用 Token/字面量扫描）。
- 优先修复 P0（影响面大/标准强约束/会持续制造漂移），再处理 P1（可复用组件 scope 与 Grid 封装），最后再做 P2（标准澄清与兜底链治理）。
- 对标准歧义点：先做“决策记录 + 标准补充（如需要）”，再做大规模迁移，避免实现分裂导致兼容链膨胀。

**Tech Stack:** Jinja2 templates, 原生 JS（espree AST 扫描）, CSS variables, pytest(-m unit), scripts/ci guards（可选）。

---

## 0) 参考与范围

**主证据（审计报告）：**
- `docs/reports/2026-01-24-ui-standards-audit-report.md`

**相关 UI 标准（SSOT）：**
- `docs/Obsidian/standards/ui/metric-card-standards.md`
- `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md`
- `docs/Obsidian/standards/ui/grid-standards.md`
- `docs/Obsidian/standards/ui/vendor-library-usage-standards.md`
- `docs/Obsidian/standards/ui/color-guidelines.md`

**整改范围（与审计一致，避免扩范围）：**
- `app/static/js/**/*.js`
- `app/templates/**/*.html`
- `app/static/css/**/*.css`

---

## 1) 进度表（按工作日排期）

> 今天是 2026-01-24（周六）；按工作日从 2026-01-26（周一）开始排期。每个 Task 完成后都应跑 `uv run pytest -m unit`，并保持“小步提交、可回滚”。

| ID | 优先级 | 目标 | 交付物 | 预计 | 计划日期 | 状态 |
|---|---|---|---|---:|---|---|
| T0 | P0 | 建立“违规点 -> 契约测试”骨架 | 新增 `tests/unit/test_ui_standards_audit_regressions.py`（或拆分多个测试文件） | 0.5d | 2026-01-26 | DONE (2026-01-24) |
| T1 | P0 | 移除 JS 硬编码 HEX 颜色 | 修复 `classification_statistics.js` + 追加 AST 扫描测试 | 0.5d | 2026-01-26 | DONE (2026-01-24) |
| T2 | P0 | `instances/detail` 迁移到 `MetricCard` | 模板替换 + 删除 `instance-stat-card*` 视觉 CSS + 追加扫描测试 | 1.0d | 2026-01-27 | DONE (2026-01-24) |
| T3 | P1 | Filters 宏去固定 id（`instance/database`）+ JS 改为 scope 内查询 | 宏签名升级 + capacity 页面改造 + charts filters/manager 适配 + 测试 | 1.0~1.5d | 2026-01-28 | DONE (2026-01-24) |
| T4 | P1 | `danger_confirm_modal` 去固定 id（Portal/scope 化） | 模板改造 + `UI.confirmDanger` 选择器改造 + 测试 | 0.5~1.0d | 2026-01-29 | DONE (2026-01-24) |
| T5 | P1 | Modal 内 Grid.js 使用收敛（禁止直 `new gridjs.Grid`） | 引入/复用封装入口 + `database-table-sizes-modal.js` 迁移 + 测试 | 1.0~2.0d | 2026-01-30 | DONE (2026-01-24) |
| T6 | P2 | 标准歧义澄清（可选，但建议） | 补充“原生 window 豁免/Portal 组件例外/Grid 非列表页封装入口”口径 | 0.5d | 2026-02-02 | TODO |
| T7 | P2 | 兜底链治理（逐步） | 选取 Top 风险点（多段 `||`/模板 `or`）逐步收敛 | 1.0d+ | 2026-02-03+ | TODO |

---

## 2) Done Definition（完成口径）

- `docs/reports/2026-01-24-ui-standards-audit-report.md` 的 4.1~4.4 对应违规点全部清零（或被标准明确豁免且有对应文档与测试）。
- 新增/更新的契约测试在 CI（本地 `uv run pytest -m unit`）稳定通过。
- 不引入新的 “silent fallback / 吞异常继续执行” 行为；若必须兼容，必须 `console.error` 或 emit 可观测事件，并在代码旁注明迁移计划。

---

## 3) 任务拆解（可执行步骤）

### Task T0: 建立“违规点 -> 契约测试”骨架

**Files:**
- Create: `tests/unit/test_ui_standards_audit_regressions.py`
- Reference: `docs/reports/2026-01-24-ui-standards-audit-report.md`

**Step 1: 写会失败的契约测试（先落框架）**
- 断言模板不存在 `instance-stat-card`（对应 T2）。
- 断言 JS 不存在 `#RRGGBB` 字面量（允许 whitelist：`variables.css` 只在 CSS；JS 默认禁止）（对应 T1）。
- 断言 `app/static/js/modules/views/grid-page.js` 之外禁止出现 `new gridjs.Grid(`（对应 T5）。
- 断言 `app/templates/components/**` 内不允许出现固定 `id="..."`（先以 allowlist + TODO 方式落地，避免一次性误伤）（对应 T3/T4）。

**Step 2: 运行确认失败**
- Run: `uv run pytest -m unit tests/unit/test_ui_standards_audit_regressions.py -q`
- Expected: FAIL（至少覆盖 4.1~4.4 中任一当前违规点）

**Step 3: 提交（可选，若团队接受“先测试后实现”的提交）**
- `git commit -m "test(ui): add audit regression contracts"`

---

### Task T1: 移除 JS 硬编码 HEX 颜色（P0）

**Background evidence:**
- 违规点：`app/static/js/modules/views/accounts/classification_statistics.js:994` 使用 `\"#3498db\"`（审计报告 4.4）。

**Files:**
- Modify: `app/static/js/modules/views/accounts/classification_statistics.js`
- Modify: `tests/unit/test_ui_standards_audit_regressions.py`（或拆分成专用测试文件）

**Step 1: 写/补齐会失败的测试**
- 断言 JS AST 字符串字面量中不存在 `^#[0-9a-fA-F]{3,8}$`（可允许极少数明确豁免，但必须注释说明原因）。

**Step 2: 最小修复实现**
- 移除 `|| \"#3498db\"` 兜底。
- 本次决策：**不考虑任何兜底**（取不到就取不到）。
  - 建议实现：取不到时 `console.error`（可观测）并返回空字符串/让调用方接受“不渲染该色彩”的结果；禁止再引入 HEX/RGB/RGBA/其他 Token 兜底链。

**Step 3: 跑测试确认通过**
- `uv run pytest -m unit tests/unit/test_ui_standards_audit_regressions.py -q`
- `uv run pytest -m unit`

**Step 4: 提交**
- `git commit -m "fix(ui): remove hardcoded hex color fallback"`

---

### Task T2: `instances/detail` 迁移到 `MetricCard`（P0）

**Background evidence:**
- 违规点：模板 `app/templates/instances/detail.html:207`/`:270` 与 CSS `app/static/css/pages/instances/detail.css:49`（审计报告 4.1）。

**Files:**
- Modify: `app/templates/instances/detail.html`
- Modify: `app/static/css/pages/instances/detail.css`
- Reference: `app/templates/components/ui/metric_card.html`
- Reference: `app/static/css/components/metric-card.css`
- Modify/Test: `tests/unit/test_ui_standards_audit_regressions.py`

**Step 1: 写/补齐会失败的测试**
- 断言 `app/templates/instances/detail.html` 不包含 `instance-stat-card`/`instance-stat-card__value`。
- 断言 `app/static/css/pages/instances/detail.css` 不包含 `.instance-stat-card` 的“视觉类属性”（允许保留布局类：grid/gap/row 等，但不允许 border/shadow/padding/typography 的私有实现）。

**Step 2: 最小修复实现**
- 使用 `components/ui/macros.html` 的 `metric_card` macro 替换现有 `instance-stat-card` 块：
  - 值节点使用 `data-role=\"metric-value\"`（组件已内置）。
  - 如需要附加维度（在线/删除/容量等），使用 macro 的 `call` slot 输出 meta（推荐复用 `status-pill`/`chip-outline`）。
- `app/static/css/pages/instances/detail.css`：删除 `instance-stat-card*` 的视觉定义；仅保留布局（例如 `.instance-stat-grid` 的 grid/gap）。

**Step 3: 跑测试确认通过**
- `uv run pytest -m unit`

**Step 4: 提交**
- `git commit -m "refactor(ui): migrate instance detail stat cards to MetricCard"`

---

### Task T3: Filters 宏去固定 id + JS 改为 scope 内查询（P1）

**Background evidence:**
- 违规点：`app/templates/components/filters/macros.html:117`（`id=\"instance\"`）、`:136`（`id=\"database\"`）（审计报告 4.2）。

**Files:**
- Modify: `app/templates/components/filters/macros.html`
- Modify: `app/templates/capacity/instances.html`
- Modify: `app/templates/capacity/databases.html`
- Modify: `app/static/js/modules/views/components/charts/manager.js`
- Modify: `app/static/js/modules/views/components/charts/filters.js`
- Test: `tests/unit/test_ui_standards_audit_regressions.py`（或拆分）

**Step 1: 写会失败的测试**
- 断言 `app/templates/components/filters/macros.html` 不包含 `id=\"instance\"`/`id=\"database\"` 的固定字面量。

**Step 2: 设计与实现（先小步）**
- `instance_filter/database_filter` 增加 `scope`（或 `field_id`）参数：  
  - 容器输出 `data-wf-scope=\"<scope>\"`。  
  - `label for` 与 `select id` 改为从 `<scope>` 派生（例如 `<scope>-instance` / `<scope>-database`）。  
- `capacity/*.html` 调用方必须传入页面唯一 scope（kebab-case）。  
- charts 相关 JS 不再写死 `#instance/#database`：改为接收 `scope` 或 `container`，并在容器内 `querySelector` 查找内部节点。

**Step 3: 跑测试 + 页面自测**
- `uv run pytest -m unit`
- 打开容量页面确认：dbType/instance/database 级联选择与图表刷新正常。

**Step 4: 提交**
- `git commit -m "refactor(ui): scope filter macros and query within container"`

---

### Task T4: `danger_confirm_modal` 去固定 id（P1）

**Background evidence:**
- 违规点：`app/templates/components/ui/danger_confirm_modal.html:3`/`:12` 固定 id（审计报告 4.2）。

**Files:**
- Modify: `app/templates/components/ui/danger_confirm_modal.html`
- Modify: `app/static/js/modules/ui/danger-confirm.js`
- Test: `tests/unit/test_ui_standards_audit_regressions.py`（或拆分）

**Step 1: 写会失败的测试**
- 断言 `app/templates/components/ui/danger_confirm_modal.html` 不包含 `id=\"dangerConfirmModal\"`/`id=\"dangerConfirmModalLabel\"` 的固定字面量。

**Step 2: 最小修复实现**
- 模板：使用 `data-wf-scope` + `data-role`（或 `data-danger-confirm-*`）替代 id。
- JS：`UI.confirmDanger` 改为用 `data-wf-scope` 选择 modal 根节点，并在容器内查找标题/内容节点（禁止全局 `#id`）。

**Step 3: 跑测试 + 交互自测**
- `uv run pytest -m unit`
- 手动点一次危险操作（删除/批量操作）确认弹窗：能展示 impacts、loading、会话中心链接等。

**Step 4: 提交**
- `git commit -m "refactor(ui): scope danger confirm modal and selectors"`

---

### Task T5: Modal 内 Grid.js 使用收敛（P1）

**Background evidence:**
- 违规点：`app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:176` 直接 `new gridjs.Grid`（审计报告 4.3）。

**Files:**
- Modify: `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js`
- Create/Modify (二选一，需先决策):  
  - 方案 A：新增封装 `app/static/js/modules/views/components/grid/grid-table.js`（或 `app/static/js/modules/ui/grid-table.js`）并作为唯一 `new gridjs.Grid` 入口；或  
  - 方案 B：将该 modal 表格迁入 `Views.GridPage` 体系（需要确认是否引入过重 wiring）。
- Test: `tests/unit/test_ui_standards_audit_regressions.py`

**Step 1: 写会失败的测试**
- 断言 `app/static/js/modules/views/grid-page.js` 之外不允许出现 `new gridjs.Grid(`。

**Step 2: 选型决策（必须落字面口径，避免反复迁移）**
- 本次决策：选择 **方案 A：新增轻封装 `GridTable`**（统一 new/destroy/默认配置），作为“非列表页表格”的官方入口。

**Step 3: 最小实现**
- 将 `database-table-sizes-modal.js` 改为调用封装入口创建/销毁 grid，并确保重复刷新前 `destroy()`。

**Step 4: 跑测试确认通过**
- `uv run pytest -m unit`

**Step 5: 提交**
- `git commit -m \"refactor(ui): remove direct gridjs usage in database table sizes modal\"`

---

## 4) 需要你确认的决策（避免实现分裂）

已确认：
1) **T1（颜色兜底）**：不考虑兜底（取不到就取不到；禁止任何 HEX/RGB/RGBA/Token fallback 链）。  
2) **T5（modal 表格）**：新增轻封装 `GridTable`（不强行迁入 `GridPage`）。  
3) **T6（标准更新）**：是，将上述决策固化进 `docs/Obsidian/standards/ui/**` 作为后续门禁口径。
