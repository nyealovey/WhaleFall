# 日志详情页色彩与布局重构方案

## 背景
- 页面与资源：`app/templates/history/logs/detail.html`、`app/static/js/modules/views/history/logs/log-detail.js`、`app/static/css/pages/history/logs-detail.css`（若无，则创建）。
- 现状问题：
  1. 详情侧边卡片依赖 `badge bg-*`、`text-danger`、`bg-light` 等旧式颜色；与仪表盘基线差异巨大，且色彩数量＞10，违背《界面色彩与视觉疲劳控制指南》中的“2-3-4”规则。
  2. JSON 详情通过“一个字段一行”方式拆分，字段名 / 嵌套排版混乱；对多层嵌套日志而言可读性更差。
  3. 异常堆栈、关联实例等信息无统一组件，`btn-outline-danger` 与 `alert-warning` 并存；操作按钮数量多且颜色不一。

## 目标
1. 整体布局与仪表盘保持一致：白底描边卡片 + `status-pill`/`chip-outline`/`ledger-chip` 体系，单屏非图表色≤7。
2. JSON / Payload 信息统一使用 formatted block（`<pre>` with `language=json` or `code`），保留堆栈，禁止“逐字段拆分”；通过折叠/复制按钮辅助阅读。
3. 状态/标签/操作按钮全部复用组件：状态列使用 `status-pill`，标签/实例使用 `ledger-chip-stack`，操作区仅保留 `btn-primary`（导出/复制） + `btn-outline-secondary`。
4. 支持暗/亮模式扩展：所有颜色来源于 token，禁止自定义 HEX。

## 设计策略
### 1. 布局
- 页面分为“基本信息卡”“上下文卡”“JSON 明细”“堆栈信息”四块，参考仪表盘 Stats 卡的留白和阴影。
- 标题行：左侧 `status-pill` 表示日志级别，右侧 `chip-outline` 展示模块/来源；时间、请求ID等使用 `ledger-chip`。

### 2. JSON / Payload
- 使用 `<pre class="log-json-viewer">{{ payload | tojson(indent=2) }}</pre>` 格式化整段 JSON，不再逐行渲染字段；`log-json-viewer` 样式：白底/描边/等宽字体/可横向滚动。
- 提供“复制 JSON”按钮（`btn btn-outline-secondary btn-icon`）。
- 嵌套字段高亮靠 `code` 组件 + `var(--text-primary)`，禁止再设置彩色背景。

### 3. 异常堆栈
- `stacktrace` 区域沿用 JSON 区块样式，标题使用 `status-pill--danger`；保留原始换行，不做拆分。

### 4. 操作区
- 按钮限制：仅保留一个 `btn-primary`（如“重试同步”）与一个 `btn-outline-secondary`（“复制 ID”/“导出 JSON”）。危险性提示通过 `status-pill--warning` 文案写明。

### 5. 筛选 / 面包屑
- 若详情页含筛选返回入口，按钮使用 `btn-outline-secondary` + icon，符合仪表盘行为。

## 实施步骤
1. **模板 (`app/templates/history/logs/detail.html`)**
   - 新建/重构 `capacity` 页面同款卡片结构，移除 `card bg-*`/`badge text-bg-*`。
   - JSON 和堆栈区域使用 `<pre class="log-json-viewer">`。
   - 将状态、模块等信息改为 `chip-outline`、`status-pill`。
2. **CSS (`app/static/css/pages/history/logs-detail.css`)**
   - 引入通用 token：`--surface-elevated`、`--surface-muted` 等；定义 `.log-json-viewer`，`.log-detail-card`，`.log-meta-chip`。
   - 去掉所有硬编码颜色/渐变。
3. **JS (`app/static/js/modules/views/history/logs/log-detail.js`)**
   - 移除手动字段渲染逻辑，改为直接 `JSON.stringify(payload, null, 2)`。
   - 新增复制功能（使用 `navigator.clipboard.writeText`）和折叠控制。
4. **共享宏（可选）**：若其它页面复用 Stats 卡，可新增 `log_detail_stats_card` 宏，确保颜色统一。
5. **QA**
   - `./scripts/refactor_naming.sh --dry-run`
   - `rg -n '#[A-Fa-f0-9]{3,6}' app/templates/history/logs/detail.html app/static/css/pages/history/logs-detail.css` 确认无硬编码颜色。
   - 手动查看 JSON / 堆栈展示效果，确保长文本可滚动、字体可读。

## 注意事项
- JSON 只做格式化，不拆分字段；保留原顺序与堆栈换行。
- 所有新增按钮遵循“单主色 CTA”原则；危险提示通过 `status-pill` 与文字解释，不使用 `btn-danger`。
- 如需新增 token，请先在《color-guidelines》登记后引用。
