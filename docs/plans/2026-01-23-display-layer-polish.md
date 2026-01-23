# 显示层小优化 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 继续做显示层小优化：统计/列表里尽量只显示「图标 + 数字」，去掉重复/冗余文案；并统一少量枚举值（周期/来源）的展示口径。

**Architecture:** 仅做展示层改动（Jinja 模板 + 前端 JS 渲染），不引入新的统计语义；尽量复用现有 `status-pill` / `chip-outline` / `ledger-chip` 样式与 `NumberFormat` 格式化。

**Tech Stack:** Flask(Jinja templates), Umbrella.js, Grid.js, 自研 `NumberFormat` / `UI.Terms`.

---

### Task 1: 修复/统一「规则管理」里的计数胶囊文案（仅图标+数字）

**Files:**
- Modify: `app/static/js/modules/views/accounts/account-classification/index.js`
- (Optional) Modify: `app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js`

**Step 1: 写一个最小手工验收清单（无自动化测试）**
- 打开「账户分类管理」页面（规则管理区域）：
  - DB 类型分组右上角：不显示“共 X 条”，只显示图标 + 数字（X）。
  - 单条规则的“命中账号数”胶囊：保持仅图标 + 数字（已符合则不动）。

**Step 2: 实现最小改动**
- 将分组统计 `renderStatusPill(\`共 ${rules.length} 条\`)` 改为 `renderStatusPill(String(rules.length))`。
- 如「规则条件」弹窗里仍显示 `共 X 条条件`，按同样原则改为图标+数字（可选，取决于页面是否被用户点名）。

**Step 3: 基础校验**
- 运行：`node --check app/static/js/modules/views/accounts/account-classification/index.js`

---

### Task 2: 批量分配（标签）页面：去掉“个实例/个标签”，仅保留图标+数字

**Files:**
- Modify: `app/templates/tags/bulk/assign.html`

**Step 1: 手工验收清单**
- 打开「批量分配标签」页面右侧汇总：
  - 顶部汇总计数：不显示“X 个实例 / Y 个标签”，改为「实例图标 + X」与「标签图标 + Y」。

**Step 2: 实现最小改动**
- 将 `summary-count-chip` 内的两段 `<span>` 改成图标+数字结构；保留 `id="totalSelectedInstances"` / `id="totalSelectedTags"` 以兼容现有 JS。

---

### Task 3: 其他列表页的“活跃/绑定实例”等后缀文案清理（仅图标+数字）

**Files:**
- Modify: `app/static/js/modules/views/instances/list.js`（若此页存在“活跃库/活跃账”类似拼接）
- Modify: `app/templates/...`（以实际匹配到的页面为准）

**Step 1: 定位**
- 在代码里全局搜索以下 UI 文案/拼接：
  - “库”、“账”、“个实例”、“无关联”、“实例”（用于统计后缀）
- 确认对应页面与渲染点。

**Step 2: 最小改动**
- 将拼接后的 `12库/12账/12个实例` 改为：图标 + 数字（必要时用 `title/aria-label` 保留语义）。
- 0 值统一显示 `-`（或灰色 `-`）。

**Step 3: 基础校验**
- 对改动到的 JS 文件跑 `node --check ...`。

---

### Task 4: 容量统计页：周期/来源枚举值展示本地化（避免直接露出 raw key）

**Files:**
- Modify: `app/static/js/modules/views/capacity/instances.js`
- Modify: `app/static/js/modules/views/capacity/databases.js`
- Create (or Modify): `app/static/js/common/stat-card-terms.js`（新增一个极小的映射工具，供多页复用）

**Step 1: 手工验收清单**
- 打开容量统计页面：
  - 周期 chip 不显示 raw（如 `daily`），显示 `日/周/月/季/年/全部`。
  - 来源 chip 不显示 raw（如 `instance_size_stats`），显示短中文（如 `采集/聚合/未知`）。

**Step 2: 实现最小改动**
- 新增 `resolvePeriodTypeLabel(periodType)` / `resolveCapacitySourceLabel(source)`。
- 页面渲染 meta 时使用映射后的 label；同时保留 `title` 显示原值（可选）。

**Step 3: 基础校验**
- 运行：`node --check` 校验新增/修改的 JS。

---

### Task 5: 全量检查 removeAttr（避免 Umbrella.js API 误用）

**Files:**
- (Search) `app/static/js`

**Step 1: 全局搜索**
- 运行：`rg -n "\\.removeAttr\\b" app/static/js`

**Step 2: 若发现**
- 改为 `wrapper.attr(name, null)` 并加一行注释说明原因。

