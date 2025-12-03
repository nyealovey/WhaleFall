# 账户统计页色彩与交互重构方案

## 背景
- 页面：`app/templates/accounts/statistics.html`（若尚未拆分，可复用 `accounts/overview.html`）、`app/static/js/modules/views/accounts/statistics.js`、`app/static/css/pages/accounts/statistics.css` 以及相关 bootstrap 脚本。
- 现状（参考现有账户统计/概览实现）：
  1. 顶部指标卡大量使用 `card bg-*`、`text-success`、`text-danger` 等旧式类，单屏彩色块 > 9，严重违背《界面色彩与视觉疲劳控制指南》的 “2-3-4” 规则。
  2. 状态/风险列表仍用 `badge bg-success`、`badge bg-danger`，不同语义重复占用主色；`btn-outline-danger` 与 `btn-warning` 并存，缺少“单主色 CTA”策略。
  3. 账户标签、所属实例等辅助信息通过 `badge bg-light` 呈现，不利于信息分组；列表 hover 效果随意硬编码 `background: #fef3c7`。
  4. 统计图/表缺少统一组件：环比、同比、状态说明散落在文案中，无法快速识别重要指标。

## 目标
1. 借鉴 Dashboard 重构成果，确保账户统计页单屏非图表色彩 ≤7，主 CTA 仅保留一个 `btn-primary`，其余使用 `btn-outline-secondary/btn-icon`。
2. 所有状态、类别、标签、风险提示统一使用 `status-pill`、`chip-outline`、`ledger-chip-stack`；删除 `badge bg-*`。
3. 统计卡与账户分布列表采用白底描边卡片，进度/趋势通过 `status-pill` 表达，信息层级靠留白与字重区分。
4. JS 渲染逻辑复用 `renderStatusPill`/`renderChipStack`/`renderTrendBadge`，杜绝硬编码颜色和 `class="text-success"`。

## 设计策略
### 1. 页头与操作区
- `page_header` 下方仅保留：`btn-primary`（如“导出账户报表”）+ `btn-outline-secondary`（返回/刷新）+ `btn-icon`（手动刷新）。“新增账户”按钮放在模块外单独 `btn-primary`，避免同屏多个主色。
- 筛选条件（时间、账户类型、风险级）采用 `filter_card` + `col-md-3 col-12`，选中项通过 `chip-outline`/`ledger-chip` 展示。

### 2. 统计卡
- 创建 `account-stat-card` 组件（同 dashboard）：白底、`color-mix(var(--surface-muted) 60%, transparent)` 描边、`--shadow-sm` 阴影。
- 卡片内容 = 数字 + 标签 + `status-pill`（↑/↓/持平）。趋势值用 `status-pill--success/danger/muted` + `fa-arrow-*` 表示，不再给卡片整体上色。

### 3. 账户状态 & 风险列表
- 列表列宽策略：状态列 90px，风险等级列 120px，标签列 ≥200px，操作列 100px。
- 状态值映射：`active`→`status-pill--success`、`locked`→`status-pill--warning`、`deleted`→`status-pill--muted`、`error`→`status-pill--danger`。
- 风险标签/所属实例/部门等元信息通过 `ledger-chip-stack` 呈现，超出用 `+N`。
- 操作按钮统一 `btn-outline-secondary btn-icon`（查看/禁用），危险动作加 `text-danger` 图标而非 `btn-danger`。

### 4. 统计分布与图表
- “账户类型分布、区域分布、风险趋势”使用 `statistics-panel`：标题 + `status-pill`（展示实时告警）+ 表格/图表。
- 进度条/分布条仅使用 `statistics-progress__bar--success/info/warning` 等 token；百分比通过 `chip-outline--muted`。
- Chart.js dataset 颜色取自 `ColorTokens`，legend 使用 `status-pill` 或 `chip-outline`。

### 5. 空态 & Skeleton
- 所有“暂无数据”区域统一 `statistics-empty`（白底、icon `text-muted`、说明文本）。
- 数据加载时可使用通用 skeleton 组件或 `placeholder-card`，避免 `spinner text-primary`。

## 实施步骤
1. **模板 (`app/templates/accounts/statistics.html`)**
   - 重写统计卡结构为 include `components/ui/statistics_card.html`，移除 `bg-*`。
   - 将状态/风险列表列渲染改为 `status-pill` + `ledger-chip-stack`。
   - 使用 `statistics-panel` 包裹所有分布表，progress/百分比列复用新类。
2. **CSS (`app/static/css/pages/accounts/statistics.css`)**
   - 移除 `.card.bg-success`、`.badge` 等旧样式；新增：
     - `.account-stat-card`, `.account-stat-card__value`, `.account-stat-card__meta`；
     - `.account-statistics-panel`, `.account-statistics__table`, `.statistics-progress`；
     - `.account-statistics-empty`、`.account-statistics__chip-stack`。
   - 所有颜色使用 token：`var(--surface-elevated)`、`color-mix` 等。
3. **JS (`app/static/js/modules/views/accounts/statistics.js`)**
   - 抽象 helper：`renderStatCards(data)`、`renderDistributionTable(list, target)`、`renderRiskList()`。
   - 提供 `getStatusMeta(account.status)` 与 `renderStatusPill/ChipStack`，删除 `class="badge bg-success"`。
   - 引入 `ColorTokens` palette 给 Chart.js；legend DOM 化。
4. **服务/Store**
   - 如果后端尚未提供环比/trend 字段，为 `AccountStatisticsService` 增加 `trend_type`, `trend_value`，用于 status-pill。
5. **质检**
   - `./scripts/refactor_naming.sh --dry-run`
   - `rg -n '#[0-9A-Fa-f]{3,6}' app/templates/accounts/statistics.html app/static/css/pages/accounts/statistics.css`
   - 手工确认单屏主色 ≤2、语义色 ≤4，按钮主色仅一处。

## 风险与缓解
- **缺少趋势字段**：无法立即展示 status-pill，可用 `status-pill--muted` + “未采集”占位，并在服务端补数。
- **表格信息过多**：若 `ledger-chip-stack` 超长，可对次要信息折叠或提供 `tooltip`，保持整洁。
- **Chart.js palette 不足**：若品类 >6，可将长尾合并为 `Other` 并在 legend 注明。

## 推广
- 将账户统计卡/面板抽象到 `components/ui/statistics/`，供实例统计、容量统计页面复用。
- 在 PR 模板加入“账户统计色彩治理” checklist（主按钮数量、是否存在 `badge bg-*`、是否使用 `status-pill`）。
- 后续若新增“账户健康分”或“风险趋势”模块，必须在《color-guidelines》登记 token 使用，再扩展本方案。
