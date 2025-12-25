# 数据库台账页面色彩与组件同步方案

## 背景
- 数据库台账页面 (`app/templates/databases/ledgers.html` + `app/static/js/modules/views/databases/ledgers.js` + `app/static/css/pages/databases/ledgers.css`) 仍处于旧配色：DB 类型 `badge bg-*`、标签彩底、类型切换按钮多主色，且操作列按钮缺乏统一规格。
- 账户台账页面已完成治理（见 `docs/changes/refactor/color/accounts-ledger-color-refactor.md`），但两个“台账”页面视觉体验不一致，违反《界面色彩与视觉疲劳控制指南》（`docs/standards/ui/color-guidelines.md`）关于组件复用的要求。

## 重构目标
1. 使数据库台账视觉与账户台账保持一致：复用 `status-pill`、`chip-outline`、`ledger-chip-stack`，控制单屏颜色 ≤ 7。
2. 统一列宽与栅格：数据库/实例列弹性，类型列 110px，标签列 220px，操作列 90px。
3. 简化工具栏：DB 类型切换区域仅高亮当前项（主色），其余使用描边按钮；导出按钮为 `btn-outline-primary btn-sm`。

## 设计策略
### 1. 工具栏与筛选
- `database-ledger-filter-form` 中的标签选择器改用与账户台账相同的 chip 视觉（灰底+描边）；数据库类型按钮组仅允许一个 `btn-primary`。
- Header 区域沿用“标题 + 导出 CSV”布局，按钮保持描边。

### 2. Grid 列
- `renderNameCell`：实例图标使用 `account-instance-icon` 中性色，不再使用 `text-info`。
- `renderDbTypeBadge`：改成 `chip-outline chip-outline--brand`，去除 `badge bg-*`。
- `renderCapacityCell`：大小与采集时间用文本+`status-pill--muted` 标记“未采集”。
- `renderTags`：调用 `renderChipStack`，默认展示全部标签并在需要时出现 `+N`。
- `renderActions`：维持单个外链按钮，但按钮样式统一 `btn-outline-secondary btn-icon`，Tooltip 表明用途。

### 3. CSS 更新
- 在 `app/static/css/pages/databases/ledgers.css` 中引入与账户台账一致的 `.ledger-chip-stack`、`.chip-outline`、`.status-pill`、行交替背景、hover 颜色。
- 移除 `badge bg-*` 相关样式，所有颜色引用 `variables.css`。

## 实施步骤
1. **样式同步**：从 `app/static/css/pages/accounts/ledgers.css` 复制/抽取公共样式到组件文件，再在数据库台账 CSS 中引用。
2. **JS 重构**：
   - 在 `databases/ledgers.js` 中新增 `renderChipStack`/`renderStatusPill` 辅助；
   - 改写 `renderDbTypeBadge`、`renderTags`、`renderCapacityCell`、`renderActions`；
   - 设置列 `width` 并复用 `CHIP_COLUMN_WIDTH` 常量。
3. **模板与工具栏**：
   - 调整按钮类名，确保唯一主色 CTA；
   - Tag Selector 的列宽与账户台账保持 `col-md-6 col-12`。
4. **验证**：
   - 浏览器检查首屏色彩数量、hover 行效果；
   - 测试筛选、标签选择器、容量跳转链接；
   - `make test` 或 `pytest -k databases_ledgers`（如有）。

## 风险与缓解
- **组件差异**：若数据库台账需要额外信息（容量状态），可通过 `status-pill--info` 表示，但必须在指南登记。
- **样式复用冲突**：抽取公共 CSS 时注意作用域，可放置在 `app/static/css/components/ledger-chips.css` 并在两个页面引用。

## 推广
- 完成后在 `CHANGELOG.md` 记录“数据库台账已对齐账户台账视觉”，并将本方案链接到未来涉及数据库域的 PR；其它“台账/列表”页面需要遵循此文档与 `color-guidelines.md`。
