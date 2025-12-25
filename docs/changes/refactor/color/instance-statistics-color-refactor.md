# 实例统计页色彩与交互重构方案

## 背景
- 页面与资源：`app/templates/instances/statistics.html`、`app/static/js/modules/views/instances/statistics.js`、`app/static/css/pages/instances/statistics.css`、`app/static/js/bootstrap/instances/statistics.js`。
- 现状问题（对照《界面色彩与视觉疲劳控制指南》与 Dashboard 重构基线）：
  1. 顶部四张统计卡直接使用 `card bg-primary/bg-success/...`，并叠加 4 种语义底色与白字，多于“主色 ≤2”限制；同一卡片体系中同时出现 ico 彩色与数字高亮，视觉噪声大。
  2. 各统计表格内仍使用 `badge bg-*`、彩色 `progress-bar` 与 `text-primary` 图标，导致单屏彩色块＞10，且语义与颜色绑定不一致（例如端口分布全部使用 `bg-info`）。
  3. 表头/表格留白不统一，hover 使用 `success-color` 叠加导致状态色被滥用；空状态与加载占位均未复用组件。
  4. JS 中绘制版本分布时依赖 Chart.js 默认调色板，与页面 token 体系脱节；表格渲染逻辑散落在模板，缺少统一的 `status-pill`/`ledger-chip` helper，后续无法复用。
  5. 页头返回按钮仍是 `btn-outline-light`，未遵循“单主色 CTA + 描边按钮”策略；筛选/导出能力缺失，后续扩展困难。

## 目标
1. 单屏非图表可视色彩 ≤ 7，统计卡、表格、按钮全部引用公共 token 与组件，彻底移除 `badge bg-*`、硬编码 `bg-*` 样式。
2. 实例画像模块（数据库类型/端口/版本）统一使用“白底描边卡 + status-pill/chip-outline/ledger-chip-stack”表达语义，并在同一表格中复用列宽策略（状态列 90px、标签列 ≥200px）。
3. JS 渲染层抽离 `renderStatusPill`、`renderChipOutline`、`renderProgressBar` 等 helper，并为 Chart.js 传入 `ColorTokens` 颜色，保持 Dashboard 同款视觉。
4. 页头及操作按钮遵循“单主色 CTA”原则：仅保留一个 `btn-primary`（如“导出统计”或“刷新数据”），其余为 `btn-outline-secondary/btn-icon`。

## 设计策略
### 1. 页头与操作区
- `page_header` 内的按钮组改为：左侧 `btn-outline-secondary` 返回实例列表，右侧提供 `btn-primary`（触发重新计算/导出）+ `btn-icon`（刷新）。
- 在页头下方增加可选的周期/类型筛选，沿用 `col-md-3 col-12` 栅格，所有选择结果通过 `chip-outline` 展示。

### 2. 统计卡
- 采用 Dashboard Stats 卡结构：白底、描边 `color-mix(var(--surface-muted) 60%, transparent)`、`--shadow-sm` 阴影。
- 卡片内容 = 数值 + 标签 + `status-pill`（表示环比/告警），图标可选且使用 `--text-muted`；禁止再使用彩色背景或大面积图标。

### 3. 分布表与进度条
- “数据库类型 / 端口 / 版本”三块使用统一的 `statistics-panel` 容器：标题行 + 表格 + 空态。
- 表格列：`类型` 列使用 `chip-outline`（brand 变体表示主推类型），`数量` 使用等宽字体，`百分比` 与 `progress` 组合（背景浅灰、前景 `status-pill` 同色）。
- 进度条仅使用主/辅 token：完成度高的用 `--success-color`，其余用 `--info-color`，禁止按 DB 类型硬编码颜色。

### 4. 图表与数据洞察
- Chart.js 数据集颜色来自 `ColorTokens.get('accent-primary')` 等统一 token，并在 legend 中复用 `status-pill`。
- 在图表下方补充 `ledger-chip-stack` 提示（Top N 版本/类型），与表格保持一致的语义色。

### 5. 空态与加载
- 定义 `.statistics-empty` 模块（白底、描边、icon `text-muted`），所有“暂无数据”区域复用；loading 状态使用 skeleton 或 `placeholder-card`。

## 实施步骤
1. **模板 (`app/templates/instances/statistics.html`)**
   - 重构页头按钮组与（可选）筛选区，统一使用 `btn-outline-secondary`、`btn-primary`。 
   - 引入 `statistics-card`、`statistics-panel` 结构，顶部四张卡重新使用 `status-pill`/`chip-outline`，删除 `bg-*`。
   - 表格中将 `badge`、彩色 `<i>` 改为 `chip-outline`、`ledger-chip`，进度条 `<div class="progress">` 使用新类 `progress-bar--accent`。
   - 空态区域改为 include `components/ui/empty_state.html`（若已有）或新增局部宏。
2. **CSS (`app/static/css/pages/instances/statistics.css`)**
   - 移除 `.card bg-*`、`.db-type-badge.*` 等旧规则，改为：
     - `.instance-stat-card`：白底、描边、阴影、数字/副标题样式。
     - `.statistics-panel` 与 `.statistics-panel__table`：控制留白、表头背景、hover 色（`color-mix(var(--surface-muted) 10%, transparent)`）。
     - `.statistics-progress`：统一高度 8px，前景类 `.statistics-progress__bar--success/info/warning` 对应 token。
     - `.statistics-empty` `.statistics-meta` `.statistics-chip-stack` 等辅助类。
   - 引入 `variables.css` token，不允许出现 HEX/RGB。
3. **JS (`app/static/js/modules/views/instances/statistics.js`)**
   - 抽象 `renderStatCards(stats)`、`renderDistributionTable(stats, target)`、`renderVersionChart(data)` 等函数，内部使用 `renderStatusPill/renderChipOutline/renderProgressBar`。
   - 将 Chart.js 调色盘替换为 `ColorTokens` 提供的 `getPalette('sequential')` 或静态 token，并在 legend 中使用 DOM 组件，不再依赖 canvas 默认图例。
   - 增加 `applyFilters(values)`、`refreshStats()`，按钮点击后触发 store `loadStats`。
4. **服务与 Store**
   - `InstanceStatisticsService` 若需扩展返回更多字段（如活跃率、Top N），在响应中加入 `trend`、`diff`，供前端 status-pill 使用。
5. **QA**
   - `./scripts/refactor_naming.sh --dry-run`、`rg -n '#[0-9A-Fa-f]{3,6}' app/templates/instances/statistics.html app/static/css/pages/instances/statistics.css`。
   - 手动核对单屏色彩数量（建议截图 + token 清单）以及 `btn-primary` 是否仅出现一次。
   - 运行 `npm run lint`（若有前端 lint）或最少 `pytest -m unit instances` 以验证服务端改动未破坏接口。

## 风险与缓解
- **数据字段不足以支撑 pill 文案**：若后端没有“环比/分类”指标，可先显示 `status-pill--muted` + “未采集”提示，同时排期补数。
- **Chart.js 颜色与 token 不匹配**：需要在 `ColorTokens` 中预留最多 6 种 sequential token，若不足则退化为灰阶 + tooltip。
- **页面信息层级过多**：如分布表仍显 crowded，可将 Top N/长尾拆为折叠卡或 `ledger-row` 列表，保持同屏 ≤4 张卡。

## 推广
- 将统计卡与分布表组件沉淀为 `components/ui/statistics_card.html`、`statistics_panel.html`，供“容量统计”“账户概览”等页面直接 include，减少重复劳动。
- 在 PR 模板中新增“色彩治理”勾选项：确认实例统计页是否复用 `status-pill`、`chip-outline`、`ledger-chip-stack`，并附上 `rg` 检查截图。
- 未来如需新增“异常实例趋势”“区域分布”等 Widget，必须先在《color-guidelines》登记颜色使用，再在本方案的“推广”章节补充。
