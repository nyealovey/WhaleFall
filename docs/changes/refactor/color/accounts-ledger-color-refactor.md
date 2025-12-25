# 账户台账页面色彩精简重构方案

## 背景
- 旧版账户台账视图（`app/templates/accounts/ledgers.html` + `app/static/css/pages/accounts/ledgers.css`）存在数据库类型彩色徽章、标签背景色、批量按钮多主色等问题，违背《界面色彩与视觉疲劳控制指南》的“单视区可视色彩 ≤ 7”“语义色 ≤ 4”要求。
- 2025-12 版本已经完成重构，本文记录最终落地方案，作为后续页面对齐的蓝本。

## 改造目标（已完成）
1. 遵循色彩 2-3-4 规则：主色 2（品牌橙 + 中性灰）、辅助色 3（浅灰描边/柔和橙/蓝灰）、语义色 4（成功/警告/危险/信息）。
2. 列表中彩色胶囊数量减少 70% 以上，全部映射到 `app/static/css/variables.css`。
3. 通过描边、字重、留白 + 统一列宽，让用户在 2 分钟内聚焦主要指标（账户、可用性、标签）。

## 设计策略
### 1. 导航与筛选区
- 顶部按钮组：`btn-primary` 仅保留在“同步所有账户”，其他工具使用 `btn-outline-primary` 或 `btn-outline-light`。
- 筛选 chips：使用灰底描边（`border-color: var(--accent-primary)`，`background: var(--surface-elevated)`），选中态只调高字重。
- 过滤 CTA：保持单一实心主色按钮，其余 CTA 采用描边风格，避免双主色并行。

### 2. 表格与徽章
- 状态列（可用性/是否删除/是否超极/操作）统一使用 70px 列宽、图标+文字的 `status-pill`，仅“锁定/删除”使用语义色背景。
- 数据库类型改为描边 chip（`chip-outline--brand`），颜色固定读取 `--accent-primary`。
- 分类与标签列采用 chip stack：白底/灰描边 + 中性的 `·` 分隔符，默认展示全部标签，必要时可折叠。
- 行背景：交替行使用 `color-mix(in srgb, var(--surface-muted) 10%, transparent)`，hover 20%。

### 3. 图标与数字
- 列表中的数量、版本号取消颜色，全部采用 `font-weight: 500` 的文本表现。
- 仅在 hover 或交互态改变描边颜色，禁止引入新背景。

## 实施步骤
1. **样式梳理**
   - 新建 `ledger-chip`、`chip-outline`、`status-pill`、`ledger-chip-stack` 等组件样式，全部引用 `variables.css`。
2. **Grid 渲染更新**
   - `accounts/ledgers.js` 使用 `renderChipStack/renderStatusPill`，所有文案统一中文（例如“锁定”）。
   - 操作列将按钮传递给 `viewAccountPermissions`，固定使用 `/accounts/api/ledgers/<id>/permissions`。
3. **列宽策略**
   - `CHIP_COLUMN_WIDTH=220px`，保证分类与标签列一致；状态列 70px，操作列 70px；数据库类型 120px。
4. **交互验证**
   - 手工检查四个场景（全部/单一 DB/筛选标签/批量导出），并记录色彩计数。
5. **文档与交付**
   - 本文作为复盘材料，引用在后续页面 PR 中。

## 验证指标
- 设计自检：浏览器扩展（如 Color Contrast Analyzer）统计账户台账首屏颜色数 ≤ 7。
- 用户访谈：内部 5 人试用 48 小时后反馈“视觉疲劳”降级为“不明显”。
- 功能无回归：`make test`、`pytest -k accounts_ledgers`（若存在）通过。

## 风险与缓解
- **品牌感下降**：若主色使用过少，可在 header 背景或关键 CTA 保留渐变，但数量不超过 2 处。
- **开发范围扩大**：若其他页面共享组件（如标签 chip），须提前沟通影响面，采用 feature flag（CSS scope）逐页切换。
- **旧截图/文档失真**：同步更新产品手册中的界面截图，避免培训资料与实际 UI 不一致。

## 推广建议
- 将本方案作为“色彩治理试点”；其余列表类页面复用 `ledger-chip` / `status-pill` 组件，并按列宽策略调整布局。
- 若后续页面存在新增语义色，必须先更新 `color-guidelines.md` 并获得 UI 审核。
