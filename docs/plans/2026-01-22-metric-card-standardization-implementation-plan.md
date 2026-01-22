# Metric Card Standardization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 统一全站“统计/指标卡片”的结构与样式，建立可复用的 `MetricCard` 标准，并清理页面私有卡片样式分叉。

**Architecture:**
- 新增单一真源组件：`app/templates/components/ui/metric_card.html` + `metric_card` macro（支持 `icon`/`meta` slot/`tone`）。
- 新增组件样式：`app/static/css/components/metric-card.css`，使用局部 CSS 变量定义卡片基线（border/shadow/padding/typography），并通过 `data-tone` / modifier class 做可控变体。
- 页面 CSS 只保留布局（grid/row/间距），不再定义卡片视觉（border/shadow/padding/value 字体）。
- 为防止回归：新增 unit test 扫描模板/JS，确保不再出现 `*-stat-card` 的“私有体系”，并强制使用 `MetricCard`。

**Tech Stack:** Flask(Jinja templates) + Bootstrap grid/utilities + CSS Variables(`app/static/css/variables.css`) + 自定义组件 CSS + FontAwesome + 原生 JS modules.

---

## 现状问题（基于截图与代码审计）

同一类“顶部指标卡片”在不同页面存在多套实现：

- 仪表盘：`app/templates/dashboard/overview.html` 使用 `.dashboard-stat-card`（`app/static/css/pages/dashboard/overview.css` 自定义 border/shadow/value 字体）。
- 容量统计：通过 `stats_card` macro/模板 `app/templates/components/ui/stats_card.html` + `app/static/css/components/stats-card.css`，并在 `app/static/css/pages/capacity/databases.css` 覆盖局部视觉。
- 标签管理：`app/templates/tags/index.html` 使用 `.tags-stat-card`（`app/static/css/pages/tags/index.css`），且 `app/static/js/modules/views/tags/index.js` 依赖 `.tags-stat-card__value` 做动态更新。
- 日志中心：`app/templates/history/logs/logs.html` 使用 `.log-stats-card`（`app/static/css/pages/history/logs.css`）。
- 运行中心：`app/templates/history/sessions/sync-sessions.html` 使用 `.session-stats-card`（`app/static/css/pages/history/sync-sessions.css`）。
- 定时任务管理：`app/templates/admin/scheduler/index.html` 使用 `.scheduler-stat-card`（`app/static/css/pages/admin/scheduler.css`）。

这些实现主要差异集中在：
- 容器语义不一致（有的用 `.card`，有的用纯 `div/article`）。
- 阴影/边框/圆角/hover 规则不一致（`shadow-sm`/`shadow-md`/无阴影混用）。
- padding 与字体层级不一致（`spacing-md/lg`、value 2rem/2.2rem 混用）。
- icon 是否存在、icon 尺寸与颜色不一致。

根因：样式“散落在页面 CSS”，组件层缺少一个可覆盖全部页面场景的单一指标卡片标准。

---

## 目标标准（提案）

### 1) 统一 HTML 结构（单一真源）

统一为 `MetricCard`：
- label
- value（可 `id` 以便 JS 更新）
- 可选 icon
- 可选 meta（chip/pill 区域）

推荐结构（示意）：

```html
<article class="card wf-metric-card" data-variant="stat">
  <div class="wf-metric-card__header">
    <div>
      <p class="wf-metric-card__label">总日志数</p>
      <div class="wf-metric-card__value" id="totalLogs" data-tone="muted">0</div>
    </div>
    <div class="wf-metric-card__icon" aria-hidden="true"><i class="fas fa-chart-line"></i></div>
  </div>
  <div class="wf-metric-card__meta">
    <!-- status-pill / chip-outline -->
  </div>
</article>
```

### 2) 统一视觉基线（组件 CSS）

- background：`var(--surface-elevated)`
- border：`1px solid color-mix(in srgb, var(--surface-muted) 65%, transparent)`
- radius：`var(--border-radius-lg)`
- shadow：默认 `var(--shadow-sm)`（顶部指标卡片更“轻”），hover 不做位移（避免“数据卡片抖动”）。
- label/value/meta 的字号与间距固定化（value 建议统一 2rem；compact 页面可通过 modifier 降低 padding）。
- tone：统一使用 `data-tone="success|warning|danger|info|muted"` 映射 `--status-* / --text-primary`。

### 3) 统一布局方式（页面只管排版）

- 顶部 4 卡：统一使用 `row row-cols-1 row-cols-md-2 row-cols-xl-4 g-3`。
- 页面 CSS 不再写 `.xxx-stat-card { border/shadow/padding/... }`，仅保留 `.xxx-stats-row` / `.xxx-stats-grid` 的布局差异（如需要）。

---

## 实施计划（分阶段，保证可回滚/可门禁）

### Task 1: 建立 MetricCard 组件（模板 + CSS）

**Files:**
- Create: `app/templates/components/ui/metric_card.html`
- Modify: `app/templates/components/ui/macros.html:1`
- Create: `app/static/css/components/metric-card.css`
- Modify: `app/templates/base.html:44-46`
- Test: `tests/unit/test_frontend_metric_card_contract.py`

**Step 1: Write the failing test**
- 新增 `tests/unit/test_frontend_metric_card_contract.py`：
  - 断言 `app/templates/components/ui/metric_card.html` 存在。
  - 断言 `app/templates/base.html` 引入 `css/components/metric-card.css`。
  - 断言 `MetricCard` class 名（如 `wf-metric-card`）在模板中存在。

**Step 2: Run test to verify it fails**
Run: `uv run pytest -m unit tests/unit/test_frontend_metric_card_contract.py -q`
Expected: FAIL（文件不存在/未引入 CSS）。

**Step 3: Write minimal implementation**
- 实现 `metric_card` 模板与 macro：支持
  - `title`
  - `value_id` / `value_text`
  - `icon_class`（可选）
  - `tone`（可选）
  - `caller()` meta slot（可选）
- 新增 `metric-card.css`：落地“视觉基线”。
- 在 `app/templates/base.html:44-46` 附近引入 `metric-card.css`。

**Step 4: Run test to verify it passes**
Run: `uv run pytest -m unit tests/unit/test_frontend_metric_card_contract.py -q`
Expected: PASS。

**Step 5: Commit**
```bash
git add app/templates/base.html app/templates/components/ui/macros.html app/templates/components/ui/metric_card.html app/static/css/components/metric-card.css tests/unit/test_frontend_metric_card_contract.py
git commit -m "feat: add MetricCard component (template + css)"
```

### Task 2: 迁移容量统计页（替换 stats_card 为 MetricCard）

**Files:**
- Modify: `app/templates/capacity/databases.html`
- Modify: `app/templates/capacity/instances.html`
- Modify: `app/templates/components/ui/stats_card.html` (deprecate or refactor wrapper)
- Modify: `app/static/css/pages/capacity/databases.css`
- Test: `tests/unit/test_frontend_capacity_uses_metric_card.py`

**Step 1: Write the failing test**
- 新增测试断言容量页不再依赖 `stats_card.html` 的固定列布局/旧 class（或至少：模板中出现 `wf-metric-card`）。

**Step 2: Run test to verify it fails**
Run: `uv run pytest -m unit tests/unit/test_frontend_capacity_uses_metric_card.py -q`
Expected: FAIL。

**Step 3: Write minimal implementation**
- 容量页改为直接使用 `metric_card` macro + Bootstrap `col` 包裹。
- `databases.css` 中移除/收敛 `.capacity-stats .stats-card { ... }` 这类“卡片视觉”覆盖，保留布局与业务专属控件（toggle group 等）。

**Step 4: Run test to verify it passes**
Run: `uv run pytest -m unit tests/unit/test_frontend_capacity_uses_metric_card.py -q`
Expected: PASS。

**Step 5: Commit**
```bash
git add app/templates/capacity/databases.html app/templates/capacity/instances.html app/templates/components/ui/stats_card.html app/static/css/pages/capacity/databases.css tests/unit/test_frontend_capacity_uses_metric_card.py
git commit -m "refactor: migrate capacity stats cards to MetricCard"
```

### Task 3: 迁移仪表盘（dashboard-stat-card -> MetricCard）

**Files:**
- Modify: `app/templates/dashboard/overview.html`
- Modify: `app/static/css/pages/dashboard/overview.css`
- Test: `tests/unit/test_frontend_dashboard_uses_metric_card.py`

**Step 1: Write the failing test**
- 断言 `overview.html` 不再出现 `dashboard-stat-card`，并出现 `wf-metric-card`。

**Step 2: Run test to verify it fails**
Run: `uv run pytest -m unit tests/unit/test_frontend_dashboard_uses_metric_card.py -q`
Expected: FAIL。

**Step 3: Write minimal implementation**
- 将四个指标卡替换为 MetricCard。
- `overview.css` 中删除 `.dashboard-stat-card*` 的视觉定义，仅保留 dashboard 业务相关样式（resource usage、chart 等）。

**Step 4: Run test to verify it passes**
Run: `uv run pytest -m unit tests/unit/test_frontend_dashboard_uses_metric_card.py -q`
Expected: PASS。

**Step 5: Commit**
```bash
git add app/templates/dashboard/overview.html app/static/css/pages/dashboard/overview.css tests/unit/test_frontend_dashboard_uses_metric_card.py
git commit -m "refactor: migrate dashboard stat cards to MetricCard"
```

### Task 4: 迁移日志中心/运行中心/定时任务管理（log/session/scheduler -> MetricCard）

**Files:**
- Modify: `app/templates/history/logs/logs.html`
- Modify: `app/static/css/pages/history/logs.css`
- Modify: `app/templates/history/sessions/sync-sessions.html`
- Modify: `app/static/css/pages/history/sync-sessions.css`
- Modify: `app/templates/admin/scheduler/index.html`
- Modify: `app/static/css/pages/admin/scheduler.css`
- Test: `tests/unit/test_frontend_history_scheduler_metric_cards.py`

**Step 1: Write the failing test**
- 断言以上模板不再出现 `log-stats-card/session-stats-card/scheduler-stat-card`，并出现 `wf-metric-card`。

**Step 2: Run test to verify it fails**
Run: `uv run pytest -m unit tests/unit/test_frontend_history_scheduler_metric_cards.py -q`
Expected: FAIL。

**Step 3: Write minimal implementation**
- 替换顶部指标卡 markup 为 MetricCard。
- 各页面 CSS 删除对应 `*-stats-card*` 视觉样式，仅保留 grid/table/交互相关。

**Step 4: Run test to verify it passes**
Run: `uv run pytest -m unit tests/unit/test_frontend_history_scheduler_metric_cards.py -q`
Expected: PASS。

**Step 5: Commit**
```bash
git add app/templates/history/logs/logs.html app/static/css/pages/history/logs.css app/templates/history/sessions/sync-sessions.html app/static/css/pages/history/sync-sessions.css app/templates/admin/scheduler/index.html app/static/css/pages/admin/scheduler.css tests/unit/test_frontend_history_scheduler_metric_cards.py
git commit -m "refactor: migrate history/scheduler metric cards to MetricCard"
```

### Task 5: 迁移标签管理（tags-stat-card + JS 依赖）

**Files:**
- Modify: `app/templates/tags/index.html`
- Modify: `app/static/css/pages/tags/index.css`
- Modify: `app/static/js/modules/views/tags/index.js:468-490`
- Test: `tests/unit/test_frontend_tags_uses_metric_card.py`

**Step 1: Write the failing test**
- 断言 `index.html` 不再出现 `tags-stat-card`，并出现 `wf-metric-card`。
- 断言 `tags/index.js` 不再依赖 `.tags-stat-card__value`，改为新 selector（例如 `.wf-metric-card__value` 或 `[data-role="metric-value"]`）。

**Step 2: Run test to verify it fails**
Run: `uv run pytest -m unit tests/unit/test_frontend_tags_uses_metric_card.py -q`
Expected: FAIL。

**Step 3: Write minimal implementation**
- tags 顶部四卡替换为 MetricCard（保留 `data-stat-key` 作为定位锚点）。
- `tags/index.js:468-490` 更新 selector，确保 `updateTagStats` 仍能更新值。
- 删除 `index.css` 中 `.tags-stat-card*` 视觉样式，仅保留 table 行 hover 等。

**Step 4: Run test to verify it passes**
Run: `uv run pytest -m unit tests/unit/test_frontend_tags_uses_metric_card.py -q`
Expected: PASS。

**Step 5: Commit**
```bash
git add app/templates/tags/index.html app/static/css/pages/tags/index.css app/static/js/modules/views/tags/index.js tests/unit/test_frontend_tags_uses_metric_card.py
git commit -m "refactor: migrate tags stats cards to MetricCard"
```

### Task 6: 建立标准文档 + 清理遗留（防止再次分叉）

**Files:**
- Create: `docs/Obsidian/standards/ui/metric-card-standards.md`
- Modify: `docs/Obsidian/standards/ui/README.md`（增加入口链接）
- Modify/Delete: `app/templates/components/ui/stats_card.html`（若完全弃用）
- Modify: `app/static/css/components/stats-card.css`（若弃用则移除引用，或降级为兼容层）
- Test: `tests/unit/test_frontend_no_legacy_stat_card_classes.py`

**Step 1: Write the failing test**
- 新增扫描测试：禁止在 `app/templates/**`/`app/static/css/pages/**` 中出现 `*-stat-card`/`*-stats-card` 这类新体系；新增需走 `MetricCard`。

**Step 2: Run test to verify it fails**
Run: `uv run pytest -m unit tests/unit/test_frontend_no_legacy_stat_card_classes.py -q`
Expected: FAIL（若还有残留）。

**Step 3: Write minimal implementation**
- 写标准文档（MUST/SHOULD/MAY + 示例）。
- 清理残留 class 与旧组件（确保 base.html 不再引入无用 css）。

**Step 4: Run test to verify it passes**
Run: `uv run pytest -m unit`
Expected: PASS。

**Step 5: Commit**
```bash
git add docs/Obsidian/standards/ui/metric-card-standards.md docs/Obsidian/standards/ui/README.md app/templates/components/ui/stats_card.html app/static/css/components/stats-card.css tests/unit/test_frontend_no_legacy_stat_card_classes.py
git commit -m "docs: add MetricCard standards and remove legacy stat card styles"
```

---

## 验证清单（最终）

- CSS token 门禁：`./scripts/ci/css-token-guard.sh`
- 命名巡检（可选）：`./scripts/ci/refactor-naming.sh --dry-run`
- 单元测试：`uv run pytest -m unit`

## 风险与回滚

- 视觉回归风险：主要集中在“页面顶部四卡”。回滚点清晰（每个页面的模板 + 页面 CSS）。
- JS 依赖：目前已确认 tags 页面 JS 依赖旧 selector，需要同步迁移（其余页面主要靠 `id/data-*`，风险较小）。

