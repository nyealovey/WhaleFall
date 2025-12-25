# 批量分配标签界面重构方案

## 背景
当前批量分配标签页面沿用两栏 + 底部汇总的布局：左侧为实例选择，右侧为标签选择，所有已选项目与动作按钮堆在底部 `batch-summary-card` 和 `batch-action-bar`。随着实例、标签数量增多，交互存在三点痛点：

1. **模式切换负担**：分配/移除模式使用同一个列表组合，通过隐藏显示达成，但视觉上区别不明显。
2. **空间浪费**：底部汇总+按钮占据大量竖向空间，用户在滚动至列表底部后需要回到顶部操作，体验割裂。
3. **信息聚焦困难**：已选实例、标签的 chips 与操作按钮分离，用户缺乏一目了然的反馈，尤其在移除模式（仅依赖提示卡）时更明显。

## 目标
- **分配模式采用三列布局**：
  - 左列：实例树/列表（保持现有分组结构）。
  - 中列：标签分组列表。
  - 右列：实时汇总所选实例与标签，并内置“清空”“执行分配”动作。
- **移除模式采用两列布局**：
  - 左列：实例选择。
  - 右列：已选实例列表 + 操作按钮（不再展示标签列）。
- 模态切换后不再跳转视角：所有关键操作始终在可视范围内完成。
- 兼顾桌面端要求（AGENTS.md 中已明确“禁止新增移动端适配”），因此仅针对 ≥1200px 的栅格优化。

## 视觉规范
- 组件色彩、按钮语义与状态提示需遵循《docs/standards/ui/color-guidelines.md》中 2-3-4 规则，禁止新增 HEX/RGB。`status-pill`、`chip-outline`、`ledger-chip` 为唯一允许的色彩载体。
- 批量汇总列沿用仪表盘白底卡片：`var(--surface-elevated)` 背景、`color-mix` 描边、`var(--shadow-sm)` 阴影，避免渐变和额外语义色。
- 交互控件（按钮/开关）统一使用 `btn-outline-secondary` 与 `btn-primary` 组合，确保主次 CTA 明确且与筛选卡一致。

## 改动范围
1. **模板结构**（`app/templates/tags/bulk/assign.html`）
   - 使用自定义布局容器替换当前 `row g-4` + `batch-summary-card` 组合。
   - 引入 `assign-mode__grid` 与 `remove-mode__grid` 两套容器，通过 `data-mode` 与 `hidden` 属性控制显示。
   - 将右侧汇总区域内嵌 `selectedInstancesList`、`selectedTagsList`、`clear/execute` 按钮，移除底部 action bar。

2. **样式**（`app/static/css/pages/tags/batch-assign.css`）
   - 新增 `display: grid` 布局：
     - 分配模式：`grid-template-columns: 1fr 1fr 0.9fr;`，列间距 `var(--spacing-lg)`。
     - 移除模式：`grid-template-columns: 1.2fr 0.8fr;`。
   - 调整 `.selection-panel__content` 高度使其与新的列高度一致，并为右侧汇总卡添加粘性顶部 (`position: sticky; top: var(--spacing-lg)`) 方便长列表滚动时仍能操作。

3. **交互脚本**（`app/static/js/modules/views/tags/batch-assign.js`）
   - 在 `BatchAssignManager` 中：
     - `loadData` 后根据 `currentMode` 切换相应容器可见性。
     - `updateUI()` 需根据模式刷新右侧汇总内容（移除模式只显示实例 chips，隐藏标签 chips）。
     - `updateModeDisplay()` 调整 `classList` 控制 `assignLayout` / `removeLayout` 的隐藏与 `aria-hidden`。
   - 移除 `selectionSummary`/`batch-action-bar` DOM 依赖，改为操作新的右侧卡片元素（例如 `#assignSummaryCard`、`#removeSummaryCard`）。

4. **可复用元件**
   - 如需保留 chips 组件，可复用 `.ledger-chip-stack` 与 `.chip-outline`，仅在 CSS 中微调间距与滚动。

## 实施步骤
1. **模板改造**
   - 重构 `assign.html`，拆分为 `assign-layout` 与 `remove-layout` 两段结构，保留现有标识 ID（`instancesContainer`、`tagsContainer` 等），避免破坏 JS 绑定。
   - 将清空/执行按钮移动到对应布局的右列卡片中，按钮 ID 保持 `clearAllSelections`、`executeBatchOperation` 便于 JS 复用。

2. **样式更新**
   - 在 `batch-assign.css` 增补 `.assign-layout-grid`、`.remove-layout-grid`、`.summary-card-sticky` 等类。
   - 调整卡片阴影与分隔线，使右列汇总在视觉上与左/中列一致。

3. **脚本更新**
   - 清理对 `selectionSummary`、`batch-action-bar`、`progressContainer` 等旧结构的查询，替换为新的 ID。
   - `updateActionButton()` 改为直接控制右列按钮状态；`updateSelectionSummary()` 改写为向新的汇总容器写入 HTML。
   - `toggleInstanceGroup` 等函数仍可复用，因为实例/标签列表的 DOM 未改。

4. **验证**
   - 手动测试：
     - 分配模式：选择多个实例+标签，右列 chips 与计数同步更新，点击执行后按钮、进度条正常。
     - 移除模式：切换模式时隐藏标签列，右列仅显示实例 chips + 操作按钮。
   - 运行 `npm run lint` 若项目包含前端检查脚本（无则跳过）。

## 迁移注意事项
- 现有 JS 依赖 `selectionSummary`、`selectedTagsSection` 等 ID，重构时需确保在新的布局中保留/更新这些 ID。
- 若今后需要再次调整布局，建议将列模板拆分为独立宏，避免巨大 HTML 块直接堆在模板中。
- 文档更新后，可在 PR 描述中附带前后对比截图，方便审查。
