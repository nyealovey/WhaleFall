# 会话中心详情页色彩与布局重构方案

## 背景
- 页面：`app/templates/history/sessions/detail.html`、`app/static/js/modules/views/history/sessions/session-detail.js`、`app/static/css/pages/history/session-detail.css`（若缺则新增）。
- 当前问题：
  1. 详情卡片仍使用 `badge bg-*`、`alert-warning`、渐变背景等过时样式，单屏可视颜色远超《color-guidelines》要求。
  2. 状态、阶段、统计信息在多个卡片中重复出现，按钮/标签色彩混乱，堆叠信息难以快速定位。
  3. 实例执行列表/日志 JSON 采用表格拆分方式，影响可读性；堆栈信息没有统一的“白底 + 描边”容器，视觉噪点大。

## 目标
1. 与仪表盘视觉基线保持一致：白底描边卡片 + `status-pill`/`chip-outline`/`ledger-chip` 体系，单屏非图表颜色 ≤ 7。
2. 详情中的状态/阶段采用 Timeline + pill 组合，所有操作按钮遵循“单主色 CTA”策略。
3. JSON 与堆栈信息使用格式化 `<pre>` 展示，保留原顺序，不再拆分字段；实例列表采用统一列宽和 `ledger-row` 风格。
4. 提升可读性与一致性，为后续会话中心改造提供标准模板。

## 设计策略
### 1. 页头与操作
- 使用仪表盘 page header：图标 + 主标题 +副标题，右侧按钮仅保留 `btn-primary`（例如“重试同步”）与 `btn-outline-secondary`（返回/复制链接）。
- 当前会话状态以 `status-pill` 展示（`success|warning|danger|info`），放在标题下方。

### 2. 基本信息卡
- 白底 `session-detail-card` 包含：会话 ID、操作方式、同步分类、触发时间、发起人等；每个字段使用 `chip-outline` 或 `ledger-chip`，禁止 `badge bg-*`。
- 需要重点信息（例如手动/定时）通过 `status-pill` 或图标 + 文案体现，不加彩色背景。

### 3. 阶段/进度
- 采用垂直 Timeline：每个阶段条目包含状态 pill（完成/执行中/失败）、文本说明、耗时；不再使用彩色进度条。
- “执行进度”数值仍可保留百分比，但使用 `chip-outline` 和 `progress`（浅灰背景 + 主色进度条）。

### 4. 实例执行列表
- 列宽参考账户台账：实例列弹性，数据库类型 120px，状态列 90px，耗时列 110px，操作列 90px。
- 状态列统一 `status-pill`，标签/分类用 `ledger-chip-stack`。

### 5. 日志/JSON/堆栈
- 采用 `session-detail__code-block`：白底、1px 描边、等宽字体、可滚动；JSON 使用 `JSON.stringify(payload, null, 2)` 全量展示（不拆字段）。
- 堆栈信息同样使用 `pre`，顶部 `status-pill--danger` 标记“错误堆栈”。

## 实施步骤
1. **模板更新**
   - 重写 `history/sessions/detail.html`，引入 page header、信息卡、Timeline、实例列表、代码块。
   - 替换所有 `badge bg-*`、`alert-*` 等 class；按钮仅保留主色/描边组合。
2. **CSS 建设**
   - 新建 `session-detail-card`、`session-detail__timeline`、`session-detail__code-block` 等样式，引用 `variables.css` token。
   - 删除硬编码颜色/阴影，使用 `--surface-elevated`、`--surface-muted`、`--shadow-sm` 等变量。
3. **JS 调整**
   - 在 `session-detail.js` 中使用 helper（ `renderStatusPill`, `renderChipStack`, `formatDuration`）渲染实例列表与 Timeline。
   - JSON/堆栈渲染改为 `pre.textContent = JSON.stringify(...)`；添加“复制 JSON”“复制堆栈”按钮（描边 icon）。
4. **QA**
   - 自检色彩数量，确保非图表元素 ≤7；对比仪表盘 Stats 卡，验证阴影/留白一致。
   - 运行 `./scripts/refactor_naming.sh --dry-run` 与 `rg -n '#[0-9A-Fa-f]{3,6}' ...` 确认无硬编码颜色。
   - 手工验证：成功/失败/进行中会话的详情状态、Timeline、实例列表、JSON 显示。

## 风险与缓解
- **Timeline 信息过长**：必要时折叠历史阶段，仅展开当前阶段及前一阶段；新增“展开全部”链接。
- **JSON 体积大**：提供“折叠/展开”“复制”按钮，并启用 `max-height` + 滚动条，防止页面撑高。
- **旧样式残留**：清理 `session-detail` 相关 CSS 文件，确保只保留新 token；如其它页面引用旧 class，需要同步迁移或增加 feature flag。

## 推广
- 本方案可复用到“日志详情”、“调度任务详情”等，需要 Timeline + JSON 的页面。
- 新增组件（卡片、Timeline、code block）应沉淀到 `components/ui/`，减少重复开发。
