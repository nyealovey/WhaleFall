# 批量分配标签（Tag Batch Assign）色彩与交互重构方案

## 背景
- 页面与资产：`app/templates/tags/bulk/assign.html`、`app/static/js/modules/views/tags/batch-assign.js`、`app/static/css/pages/tags/batch-assign.css`，以及 `tag_batch_store.js`、`tag_management_service.js`。
- 当前实现沿用了旧版 Flatly 主题：模式切换 `btn-outline-danger`+`btn-outline-primary`、卡片头使用渐变和玻璃拟态阴影、统计/选中区大量 `badge bg-secondary`/`bg-light`，实例/标签列表 hover 也写死 `var(--primary-color)`。单屏非图表颜色超过 10 种，违反《界面色彩与视觉疲劳控制指南》的 2-3-4 规则，并与 Dashboard 重构后的白底卡片 + status-pill 体系不一致。
- 功能痛点：
  1. **模式切换**：`btn-outline-danger` 直接用语义色区分模式，且 Radio 标签字体加粗造成视觉噪点。
  2. **实例/标签卡片**：自定义 `card` 阴影、`color-mix` 背景与原本 `card` 组件冲突，`selected` 状态依赖高饱和底色。
  3. **摘要/提示**：`alert-warning`、`badge bg-secondary` 组合在一屏出现 4+ 个底色，且 `col-6` 固定导致窄屏内容拥挤。
  4. **动作区**：`btn-light`、`btn-outline-secondary`、`btn-primary` 并存，同时进度条使用渐变 `--gradient-primary`，缺乏 token 控制。

## 目标
1. 以 Dashboard 重构文档为基线：整页白底卡片 + `status-pill`/`chip-outline`/`ledger-chip`；单屏非图表色 ≤7，卡片阴影统一 `--shadow-sm`。
2. 模式、实例、标签、摘要、进度等所有状态表达仅使用语义 token（`--success-color` 等）+ 组件；实例/标签列表统一列宽与交互，禁用硬编码渐变/玻璃效果。
3. 操作入口仅保留一个 `btn-primary`（执行操作），其它按钮 `btn-outline-secondary`/`btn-icon`；危险语义通过 `status-pill--danger` 或提示文案呈现，不再使用 `btn-outline-danger`。
4. JS 渲染层抽象 `renderLedgerChipStack`、`renderStatusPill`、`renderSelectionCard`，复用 NumberFormat/ColorTokens，避免内联颜色；`tag_batch_store` 只负责数据，UI token 由 view 定义。

## 设计策略
### 1. 页面框架与页头
- `page_header` 内按钮组：返回按钮改 `btn-outline-secondary` + icon；标题区引用 `text-muted` 副标题，避免 `btn-light` 背景。
- 主体使用 `dashboard layout-shell` 样式，卡片背景 `var(--surface-elevated)` + `var(--gray-200)` 描边 + `--shadow-sm`，删除玻璃模糊与渐变。

### 2. 模式切换与告警
- Mode Switch 改为 `chip-toggle`（`chip-outline` 变体）或 `btn-group btn-outline-secondary`，激活态通过 `chip-outline--brand` + `fw-semibold` + `aria-pressed` 表达；禁用 `btn-outline-danger`。
- “移除模式说明”使用 `status-pill--warning` + 描边卡片（同 Dashboard 的警示卡），不再使用整片 `alert-warning`。

### 3. 实例选择区域
- 两列布局改 `col-lg-6 col-12` 保持桌面优先；卡片 head/body 引用 `dashboard-stat-card` 样式。
- 分组（数据库类型）以 `accordion` + `chip-outline` 表示，组 title 显示 `chip-outline chip-outline--muted` 说明 DB 类型；展开状态 icon 使用 `text-muted`。
- 实例项使用 `ledger-row`：左侧名称/描述，右侧 `status-pill` 表示连接状态；选中通过描边 + `ledger-check` icon + `fw-semibold`，背景保持白。

### 4. 标签选择区域
- 复用《选择标签重构方案》：分类 tabs = `chip-outline`，标签项 = `ledger-chip-stack` + `status-pill`（激活/停用），无彩色背景。滚动容器引用 token 阴影。
- `selectedTagsCount` 使用 `status-pill status-pill--info`，避免 `badge bg-secondary`。

### 5. 选择摘要与统计
- 摘要区转成两张 `summary-card`：顶部 `status-pill--muted` 表示“已选实例/标签”；列表内容使用 `ledger-chip-stack`，溢出显示 `+N`。
- `selection-info` 数字使用 `NumberFormat.formatInteger` 并通过 `data-value-tone` 控制色，保持与 Dashboard Stats 一致。

### 6. 操作按钮与进度
- 操作条为描边卡片：左侧 `chip-outline` 显示选择数量，右侧按钮组（`btn-outline-secondary` 清空、`btn-primary` 执行）。
- 进度条采用标准 `.progress` + `.progress-bar bg-accent`（token），并加 `status-pill--info` 文本说明；隐藏渐变背景。

### 7. JS 与数据交互
- `BatchAssignManager` 输出 DOM 片段时调用共享 helper：`renderInstanceCard(instance)`、`renderTagCard(tag)` 返回无颜色 class；状态 → pill variant 的映射集中在 `STATUS_VARIANTS`。
- Mode 切换时仅更新 `data-mode` 属性，由 CSS 控制选中样式；执行操作按钮 `disabled` 状态使用 `btn-primary disabled` 标准样式。
- `selection-summary` 渲染使用 `renderLedgerChipStack` 并附带 tooltip，删除 `selected-item` 自定义 class。

## 实施步骤
1. **模板**  
   - 重构 `assign.html`：
     - 页头按钮改 `btn-outline-secondary`；mode switch 引入 `chip-outline` 模板或按钮组宏。
     - 实例/标签卡片使用 `components/cards/stat_card.html`（如 Dashboard），`badge` 统计替换为 `status-pill`。
     - 摘要、操作条、进度条均包裹在 `.dashboard-widget` 容器，移除 `bg-light`、`badge bg-secondary`。
2. **CSS**  
   - 删除渐变、玻璃背景，统一引用 `--surface-elevated`、`--gray-200`、`--shadow-sm`。
   - 新增 `.batch-toggle`, `.selection-card`, `.ledger-row` 等 class，全部使用 token；选中样式仅改描边/字重。
   - 滚动容器/空状态沿用 Dashboard 的 `color-mix` 10% hover；`col-6` 等栅格调整为 `col-lg-6 col-12`。
3. **JS**  
   - 在 `batch-assign.js` 中抽离 helper：`createStatusPill(status)`, `createLedgerChip(item)`，替换所有 `badge`/`bg-secondary`。
   - Mode/summary/selection渲染函数只操作数据和 class，禁用 `style="background-color:"`。
   - 统计数字调用 `NumberFormat`，并通过 `setAttribute('data-value-tone', tone)` 控制文本色。
4. **QA**  
   - 自检命令：`./scripts/refactor_naming.sh --dry-run`、`rg -n '#[0-9A-Fa-f]{3,6}' app/templates/tags/bulk app/static/css/pages/tags/batch-assign.css`、`rg -n 'bg-' app/templates/tags/bulk/assign.html`。
   - UI checklist：单屏非图表色 ≤7；mode switch/按钮 CTA 数量符合“单主色”策略；实例/标签列表 hover/选中无硬编码色。
   - 功能：运行 `pytest -k "batch_assign" -m unit`（如有），并在本地 `make dev start` 后走完整批量分配流程。

## 风险与缓解
- **列表性能**：引入更多 DOM 组件可能拖慢渲染，可在 `batch-assign.js` 中加入虚拟滚动或分页；必要时添加 Skeleton。
- **角色/权限差异**：不同权限看到的按钮集合不同，需在模板中保持按钮数量一致，仅在 JS 中控制 `disabled`。
- **与 Tag Selector 重构冲突**：若 Tag Selector 模态与本页同时上线，确保共享 `ledger-chip`/`status-pill` 样式已在公共 CSS 加载，防止重复定义。

## 推广与后续
- 将批量分配页纳入“标签体系”标准：任何涉及实例/标签批量操作的页面需复用本方案的卡片、chip、mode switch。
- 在 PR 模板添加“Batch Assign 视觉治理”检查项：色彩数量、CTA 数量、chip/pill 复用情况、脚本执行截图。
- 视需要把 `BatchAssignManager` 的 UI 渲染函数迁入 `modules/views/components/tags/`，供账户、数据库批量操作页面共享。 
