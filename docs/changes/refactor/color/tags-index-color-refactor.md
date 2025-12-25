# 标签管理（Tags Index）色彩与交互重构方案

## 背景
- 页面：`app/templates/tags/index.html`、`app/static/js/modules/views/tags/index.js`、`app/static/css/pages/tags/index.css`。
- 当前标签列表存在旧式 `badge bg-*`、多色按钮和并列主色 CTA；筛选器仍使用 `col-md-2` 栅格且未复用 `ledger-chip` 选中态。整体与仪表盘最新的白底卡片 + pill/chip 体系不一致，违背《色彩与视觉疲劳控制指南》中的“2-3-4 规则”。

## 目标
1. **统计卡/页头工具**：按仪表盘基线输出白底描边卡片，主数值使用 `var(--text-primary)`，状态或趋势通过 `status-pill`/`chip-outline` 呈现，单屏色彩 ≤7，按钮仅保留一个 `btn-primary`。
2. **列表**：所有状态/分类/颜色列统一使用 `status-pill`、`chip-outline`、`ledger-chip-stack`；列宽遵循指南：标签名弹性、分类 110px、颜色 110px、状态 90px、操作 90px。
3. **筛选器与模态**：筛选表单列宽 `col-md-3 col-12`，选中态走 `ledger-chip`；模态、批量操作按钮遵循“单主色 CTA”。
4. **JS 渲染**：复用 `renderStatusPill`/`renderChipOutline`/`renderChipStack` helper，清除硬编码颜色，并在统计卡中动态写入 `data-value-tone` 以改变字体颜色。

## 设计策略
### 1. 统计卡
- 参考 `dashboard/overview.html` 的结构：`<div class="tags-stat-card">`，内部包含 `__label`、`__value`、可选 `__meta`。
- 不再绘制彩色背景，取而代之的是 `color-mix` 描边 + `--shadow-sm`。
- 错误/未启用等数值通过 `data-value-tone="danger|warning|info"` 控制字色；任何补充信息（如“共 X 个分类”）使用 `chip-outline chip-outline--muted`。

### 2. 列表
- `renderTagName`：加粗主名称，副文案（描述）用 `text-muted`。
- `renderTagColor`：展示 token 名称，`chip-outline--brand` 表示系统 token，`chip-outline--muted` 表示自定义。
- `renderStatus`：`status-pill--success/danger/muted` 对应启用/停用/草稿，图标与状态文本保持中文短语。
- `renderBindings`：通过 `ledger-chip-stack` 展示关联对象（例如“实例 12/凭据 4”），超出改用 `+N`。
- 操作列统一 `btn-outline-secondary btn-icon`，危险动作仅在 icon 上添加 `text-danger`。

### 3. 筛选器 & 模态
- `filter_card` 中的搜索/分类/状态列均传 `col-md-3 col-12`；选中项在 JS 中用 `chip-outline` 显示。
- 模态按钮：主操作 `btn-primary`，取消/辅助操作 `btn-outline-secondary`，禁止 `btn-danger` 的整块背景，危险提示改为模态正文 `status-pill--danger`。

### 4. JS 实施要点
- 在 `tags/index.js` 新增 `renderStatusPill`、`renderChipOutline`、`renderChipStack`、`setTagStats`，与仪表盘一致处理 `data-value-tone`。
- 列定义更新后记得同步 `gridWrapper` 的列宽配置，并移除 `class="badge bg-..."` 字符串。
- 统计卡数据来源（总标签、启用/停用数、分类数）写入 `setTagStats`，保持与仪表盘相同的 DOM 结构。

## 实施步骤
1. **模板**
   - 重写统计卡 DOM，加入 `tags-stat-card` 样式和 `data-value-tone` 属性。
   - 调整筛选器列宽；页头按钮保留一个 `btn-primary`（例如“新建标签”），其余使用 `btn-outline-secondary` 或 `btn-icon`。
2. **CSS**
   - 创建/更新 `app/static/css/pages/tags/index.css`，包含 `tags-stat-card`、`status-pill`、`chip-outline`、`ledger-chip-stack`、`btn-icon` 等定义，可直接复用仪表盘/日志中心样式。
   - 列表交替行、hover 背景使用 `color-mix(in srgb, var(--surface-muted) 10%, transparent)` 和 20%。
3. **JS**
   - 在 `tags/index.js` 中重写 `buildColumns()`，渲染函数全部使用新的 helper，并删除硬编码颜色。
   - 新增 `updateTagStats()` 用于刷新顶部统计卡。
   - 保持筛选器 `col-md-3` 栅格，并在 `handleFilterChange` 后调用 `updateTagStats`。
4. **QA**
   - 检查单屏内非图表颜色 ≤7；抓取 `./scripts/refactor_naming.sh --dry-run` 和 `rg "#" app/templates/tags` 确认无硬编码。
   - 手测筛选/模态流程，确保新按钮/样式与仪表盘一致。

## 风险与缓解
- **标签颜色不可视**：chip 仅显示 token 名称，需确保 hover 提示显示颜色示例，可在 chip 上添加 `title="#Hex"`。
- **批量操作反馈不足**：描边按钮可能不够醒目，点击后应结合 toast 或二次确认提示。

## 推广
- 完成后将 `tags/index` 作为“标签/分类类页面”的参考，实现任何新标签面板时必须复用 `tags-stat-card`、`status-pill`、`chip-outline`，并在 PR 模板中附上 color guideline checklist。
