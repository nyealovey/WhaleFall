# 实例详情页面（Instances Detail）色彩与组件重构方案

## 背景
- 页面：`app/templates/instances/detail.html`、`app/static/js/modules/views/instances/detail.js`、`app/static/css/pages/instances/detail.css`。
- 问题：顶部统计卡与信息块广泛使用 `bg-primary/bg-success/bg-warning/bg-danger`，SQL 配置/监控卡片也有多种色块；实例状态、同步按钮、权限提示仍通过高饱和颜色传达信息，与《界面色彩与视觉疲劳控制指南》冲突。
- 本方案参考账户台账与实例列表重构，统一 chip/pill 组件，减少统计卡颜色（最多 2 种中性色）。

## 目标
1. 将统计卡颜色减至 2 种以内：主色强调关键指标，其余使用白底+阴影+`status-pill` 指示趋势。
2. Instance 状态、同步状态、风险提示全部复用 `status-pill`（`success|warning|danger|muted`），避免硬编码 `bg-*`。
3. 标签、凭据、账号列表等信息使用 `ledger-chip`/`chip-outline`；操作按钮仅保留一个主色 CTA。

## 设计策略
### 1. 统计卡
- 重写 `stats_card` 调用：背景统一白色，四个卡片只通过图标和数值强调，趋势/变化用 `status-pill` 说明（例如“+3 实例”）。
- 若必须使用颜色，限定为主色+浅灰（两种），满足“减少统计卡颜色”要求。

### 2. 信息块 & 标签
- `instance-meta` 区块中的“主从/环境”标签换成 `ledger-chip`；数据库类型使用 `chip-outline--brand`。
- 同步状态/容量状态/监控运行状态使用 `status-pill`。

### 3. 操作面板
- “同步容量”“测试连接”“编辑实例”等按钮遵循单主色：主操作 `btn-primary`，其余 `btn-outline-secondary`。
- 任何危险操作（删除、停用）改为描边+文字提醒，不再通过大面积红色表达。

### 4. 日志/权限/会话列表
- 子表格沿用实例列表列宽策略（状态 70px、标签 220px、操作 90px）；
- 渲染函数复用 `renderChipStack`、`renderStatusPill`，删除 `badge bg-*`。

## 实施步骤
1. **样式**：将 `instances/detail.css` 中的 `bg-*` 色块替换为 token；引入公共 chip/pill 样式。
2. **模板**：更新统计卡 HTML，使用新的 `stats_card` 变体；改写按钮类名。
3. **JS**：在 `instances/detail.js` 中添加 `renderStatusPill/renderChipStack`；调整会话/权限表格的列渲染。
4. **验证**：确认页面非图表色彩 ≤7，统计卡仅使用 1~2 种背景色；运行相关集成测试。

## 风险
- 页面信息密集，颜色减少后需通过图标/排版维持可读性，可增加分隔线或卡片阴影。

## 推广
- 完成后更新 `docs/standards/ui/color-guidelines.md` 的案例，其他详情页（如凭据、账户）应参照执行。
