# 会话中心（同步会话）色彩与交互重构方案

## 背景
- 页面：`app/templates/history/sessions/sync-sessions.html`、`app/static/js/modules/views/history/sessions/sync-sessions.js`、`app/static/css/pages/history/sessions.css`。
- 现状：统计卡采用四种不同 `bg-*` 背景；会话状态/类型/操作按钮使用多色 badge；筛选器、模态也存在亮色混搭。需对齐《色彩与视觉疲劳控制指南》和账户台账试点成果。

## 目标
1. 统计卡颜色减至 2 种：保持一个主色强调“总会话数”，其余卡片使用白底 + `status-pill` 提示变化。
2. 列表中所有状态/类型/标签统一用 `status-pill`、`chip-outline`，操作按钮采用描边风格；列宽策略与实例列表一致。
3. 清理筛选卡 & 模态的硬编码颜色，保证单主色 CTA。

## 设计策略
### 1. 页头/统计卡
- `stats_card` 调用传入 `variant='neutral'`（白底）+ `status-pill` 表示“成功/失败/进行中”；主卡 `Total Sessions` 可使用品牌主色描边。
- 在统计卡内部显示趋势（例如“较昨日 +5%”）时使用 `status-pill--success/--danger`。

### 2. 筛选器
- 搜索/实例/数据库/状态筛选统一 `col-md-3 col-12` 栅格；选中的标签用 `ledger-chip`。
- 过滤提交按钮仅保留一个 `btn-primary`，另一个“清空”使用 `btn-outline-secondary`。

### 3. 会话列表
- 列宽：会话 ID 列弹性、类型 110px、状态 90px、标签 220px、操作 90px。
- `renderStatus` 使用 `status-pill`（例如“进行中”“已完成”“失败”）；`renderType` 用 `chip-outline`。
- 操作按钮（查看详情、终止）统一 `btn-outline-secondary btn-icon`；危险操作仅在 icon 或确认阶段提示红色。

### 4. 模态与日志
- 会话详情模态内部的标签、步骤状态同样使用 chip/pill；progress bar 仅保留主色。

## 实施步骤
1. **样式**：引入公共 chip/pill 样式；删除 `.badge-*` 等颜色定义，列表交替行背景与实例页一致。
2. **模板/JS**：重构 `stats_card`、列表列渲染、操作按钮；JS 中抽取 `renderStatusPill`、`renderChipStack`。
3. **验证**：色彩检查工具确认非图表颜色 ≤7；运行会话相关测试。

## 风险与缓解
- 会话状态较多（成功/失败/运行/暂停），必要时可在 `status-pill` 上引入 icon + tooltip，帮助识别。

## 推广
- 完成后将方案链接至其它历史中心页面（如审计日志、变更记录），确保历史模块视觉一致。
