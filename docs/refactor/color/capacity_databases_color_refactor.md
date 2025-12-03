# 数据库容量统计视图重构方案

## 背景
- 页面位置：`app/templates/capacity/databases.html` + `app/static/js/modules/views/capacity/databases.js` + `app/static/css/pages/capacity/databases.css`。
- 现状：顶部按钮使用 `btn-outline-light/btn-light` 等混色，筛选卡片仍是多列浅色输入框；统计卡片全部采用高饱和 `bg-primary/bg-success/bg-info/bg-warning`；趋势图控制组使用多套不同颜色按钮；列表和图表均存在硬编码颜色，严重违背《界面色彩与视觉疲劳控制指南》中“单视区可视色彩 ≤ 7、语义色 ≤ 4、复用 status-pill/chip 组件”的约束。

## 改造目标
1. 复用账户台账的色彩体系：主色只保留品牌橙 + 中性灰，语义色仅在必要时出现。
2. 将统计卡、趋势图控制、筛选器、结果表中的所有彩色块替换为 `status-pill`、`chip-outline`、中性按钮，避免柱状图之外的多色干扰。
3. 保持列宽与布局一致：状态/操作列 70~90px，芯片列 ≥220px；趋势图控制按钮同一时间仅 1 个主色。

## 设计策略
### 1. 页头与按钮
- `刷新数据/统计当前周期`：改为 `btn-outline-primary` + `btn-primary` 组合；动作用图标+文字区分危险性，不再通过颜色。
- 若需要提醒“统计中”，使用 `status-pill--info` 与 loading 文案。

### 2. 筛选器
- `filter_card` 内加入标签/分类时采用 `ledger-chip` 样式；表单控件统一 `col-md-3 col-12` 栅格，减少拥挤。
- 清除 `btn-outline-*` 多色按钮，仅在提交按钮上使用主色。

### 3. 统计卡片
- 重写 `stats_card` 宏的颜色参数，使用中性色背景（白底 + 阴影），数值通过字重区分；语义变化（如“容量增长”）以 `status-pill` 展示。
- 卡片内图标颜色为 `--text-muted`，避免彩色图标。

### 4. 趋势图控制面板
- 所有单选按钮组（图表类型、TOP、周期）统一区分：主选项 `btn-outline-primary` + 激活态主色填充；其余仅用描边。
- 引入 `legend-chip`（等同 `ledger-chip`）显示筛选状态，颜色来自 token。

### 5. 表格/列表
- 如果页面底部含数据库列表或表格，列宽/视觉对齐账户台账：数据库列弹性，类型列 110px，标签列 220px，操作列 90px。
- 标签/分类列使用 `renderChipStack`；状态列（如容量采集状态）采用 `status-pill`。

## 实施步骤
1. **样式沉淀**：将 `ledger-chip`/`status-pill` 等公共样式抽到组件 CSS，并在 `capacity/databases.css` 中引用；删除 `bg-*`、`text-*` 自定义配色。
2. **模板更新**：
   - 调整页头按钮类名；
   - 修改 `stats_card` 调用参数，传入新的 `variant='muted'` 等；
   - 优化筛选卡片的列宽、按钮样式。
3. **JavaScript 重构**：
   - 在 `capacity/databases.js` 中新增 `renderChipStack`、`renderStatusBadge` 等辅助函数；
   - 趋势图图例/筛选状态使用 chip 组件；
   - 若有 Grid 列渲染，参照实例/台账页面输出。
4. **验证**：刷新页面，使用色彩检查工具确认非图表色彩 ≤7；确保不同主题下亮/暗模式表现一致。

## 风险与缓解
- **信息密度高**：统计卡减少颜色可能导致用户不适，可通过增加小型图标/趋势箭头（中性色）来维持可读性。
- **图表颜色限制**：趋势图本身可继续使用多色，但需限制在图表区域；其他 UI 元素保持中性色即可。
- **自定义主题**：若未来引入暗色主题，chip/status-pill 已支持 token，保持一致即可。

## 推广
- 完成后在 `CHANGELOG.md` 记录“数据库容量统计页面色彩收敛”，并引用本方案；其他统计页面（如实例容量、账号统计）应复制该布局与色彩策略。
