# 日志中心（History Logs）色彩收敛方案

## 背景
- 页面：`app/templates/history/logs/logs.html`、`app/static/js/modules/views/history/logs.js`、`app/static/css/pages/history/logs.css`。
- 页头统计卡目前使用四种不同背景色（主/红/黄/灰），列表中的日志级别 badge 也沿用 `badge bg-*`，导致色彩噪声。需按《color-guidelines》与账户台账经验进行重构。

## 目标
1. 统计卡颜色减至 2 种以内：总日志数使用主色描边，其余（错误、警告）在白底卡片中通过 `status-pill--danger/warning` 展示数字，避免整块红黄背景。
2. 列表列宽与 chip/pill 组件统一：日志级别列 90px，来源列 150px，标签列 220px，操作列 90px。
3. 筛选器、图表、详情模态遵循单主色 CTA 规则，清除硬编码颜色。

## 设计策略
### 1. 统计卡
- 使用卡片组件 + `status-pill`：例如“错误日志 120” -> 白底卡片 + `status-pill--danger` 标记数值；“警告日志”使用 `status-pill--warning`。此举满足“统计卡颜色减少”要求。

### 2. 列表
- `renderLogLevel` 改为 `status-pill`（`INFO|WARN|ERROR` -> `muted|warning|danger`），包含图标辅助识别。
- 标签/模块列采用 `ledger-chip-stack`；时间列使用中性文本。
- 操作按钮 `btn-outline-secondary btn-icon`。

### 3. 筛选与模态
- 筛选卡片列宽 `col-md-3 col-12`；筛选结果 summary 使用 `ledger-chip`。
- 日志详情模态内的字段标签使用 `chip-outline` 或 `status-pill--muted`，避免大面积色块。

## 实施步骤
1. **CSS**：从实例/台账页面复用 chip/pill 样式；去掉 `.badge-*`。统计卡组件增加 `--card-muted` variant。
2. **模板**：更新 `stats_card` 和筛选按钮样式。
3. **JS**：在 `history/logs.js` 中实现 `renderStatusPill`、`renderChipStack`；重写列宽与渲染函数。
4. **验证**：色彩检查 ≤7；运行日志筛选/详情的自动化脚本或手工测试。

## 风险
- 如果用户依赖颜色快速区分级别，可在 `status-pill` 中保留图标（如 `fa-exclamation-triangle`），同时提供 legend 说明。

## 推广
- 方案可复用到其它历史审计类页面（如操作审计、调度日志），形成统一视觉系统。
