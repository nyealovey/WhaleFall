# Numeral.js 数字格式化迁移方案

## 背景与目标

当前前端页面的数字展示分散在多个脚本中，常见写法包括 `Number(value).toLocaleString()`、`toFixed` 连串字符串拼接，以及重复的 MB/GB/TB 转换逻辑。这些实现存在以下问题：

- **风格不一致**：不同页面的千分位、精度和单位展示各不相同，影响可读性。
- **重复代码难维护**：容量、百分比、时长等格式化逻辑在多个文件中复制，未来调整需要逐个修改。
- **缺乏本地化能力**：大部分写死为英文单位或手动补 `+/-`，难以根据地区策略扩展。

目标是引入 [Numeral.js](https://numeraljs.com/) 作为统一的数字格式化库，通过一个中心化的封装模块，为各页面提供一致的 API，并逐步替换现有的手写逻辑。

## 现状梳理

| 场景 | 文件 | 位置 / 函数 | 当前行为 |
| --- | --- | --- | --- |
| 标签统计 | `app/static/js/components/tag_selector.js` | `formatNumber` | 使用 `Number(value).toLocaleString()` 显示标签数量 |
| Capacity 概览卡片 | `app/static/js/common/capacity_stats/summary_cards.js` | `defaultFormatters.number/sizeFromMB` | 手写 MB/GB/TB 转换与 `toFixed` 精度 |
| Chart tooltip | `app/static/js/common/capacity_stats/chart_renderer.js` | `tooltip.callbacks.label` | 通过 `value.toFixed(2)` 拼接 GB/% |
| 列表容量展示 | `app/static/js/pages/instances/list.js` | `formatSize` | 将字节转 GB，并固定 3 位小数 |
| 实例详情容量 | `app/static/js/pages/instances/detail.js` | `totalSizeGB` 计算、`sizeGB` 渲染 | 多处 `(sizeValue / 1024).toFixed(3)` 重复 |
| 审批统计百分比 | `app/static/js/pages/instances/statistics.js` | `getChartOptions → tooltip.label` | 以 `(parsed / total * 100).toFixed(1)` 拼接 |
| 运行图表 | `app/static/js/pages/dashboard/overview.js` | `updateResourceUsage` | `percent.toFixed(1)` 决定徽章文本 |
| 分区/聚合页面 | `app/static/js/pages/admin/partitions.js`, `pages/admin/aggregations_chart.js` | `formatSize`, `formatSizeFromMB` | 重复的 MB→GB→TB 切换与字符串模板 |
| 历史同步耗时 | `app/static/js/pages/history/sync_sessions.js` | `getDurationBadge` | 以 `sec.toFixed(1)` 拼接“秒/分钟/小时” |
| 容量统计入口 | `app/static/js/pages/capacity_stats/*.js` | `summaryCards` 配置 & `manager.js` | 依赖 `summary_cards.js` 提供的格式化器 |

> 备注：以上仅列出涉及最终用户展示的数字格式化热点，具体实现中还包含若干 `toFixed`/`toLocaleString` 用于中间态文本，后续统一替换时一并纳入。

## 方案设计

### 1. 引入 Numeral.js 依赖

1. 下载官方 `numeral.min.js`（建议版本 `2.0.6`）及 `locales.min.js`，存放至 `app/static/vendor/numeral/`，保持与现有 vendor 目录一致。
2. 在 `app/templates/base.html` 中，于 `axios.min.js` 之前加载 `numeral.min.js` 与 `locales.min.js`，并在加载后设置默认 locale 为 `zh-cn`。
3. 若后续需要精简体积，可考虑只保留必要的 locale 文件，当前阶段以完整 locales 文件确保可扩展性。

### 2. 封装统一的数字工具

新增 `app/static/js/common/number-format.js`（遵守 kebab-case），该模块职责：

- 初始化 Numeral.js（例如设置默认格式、注册常用别名）。
- 提供以下高阶封装，并挂载到 `window.NumberFormat` 供全局调用：
  - `formatInteger(value, { fallback })`：千分位整数。
  - `formatDecimal(value, { precision, trimZero })`：小数控制。
  - `formatBytesFromMB(value, { unit: 'MB' | 'GB' | 'TB' | 'auto' })`：容量转换（内部调用 Numeral 自定义格式 `0,0.00 b`）。
  - `formatPercent(value, { precision, showSign })`：百分比文本。
  - `formatDurationSeconds(value)`：秒数转“秒/分钟/小时”Badge 文本。
  - `formatPlain(value, pattern)`：允许直接传入 Numeral 模式，例如 `0,0.00`、`0.0%`。

模块内部通过 Numeral 提供的 `numeral(value).format(pattern)` 达成展示一致性，同时保留空值 / 非数字容错逻辑，避免页面崩溃。

### 3. 迁移策略

1. **打基础**：引入 vendor 文件、编写 `number-format.js`、在 `base.html` 注册 `window.NumberFormat`，并保持与 `toast` 等全局工具一致的加载顺序。
2. **核心复用点**：先改造 `summary_cards.js` 与 `capacity_stats/chart_renderer.js` 等共享模块，确保后续各页面自动获得统一输出。
3. **页面覆盖**：按照优先级迁移剩余脚本，建议顺序：
   1. `components/tag_selector.js`（影响多处标签弹窗）
   2. `pages/instances/*.js`（管理端访问频繁）
   3. `pages/admin/*.js`（分区/聚合）
   4. `pages/history/sync_sessions.js`
   5. 其他使用 `toFixed`/`toLocaleString` 的散点场景
4. **命名校验**：完成命名/结构调整后运行 `./scripts/refactor_naming.sh --dry-run` 确认未引入禁用命名。
5. **可回滚性**：在迁移关键节点（如 summary 卡片、Chart tooltip）前保留旧函数的单独 commit，若发现问题可以快速回退。

## 测试与验证

1. **手动校验**
   - 仪表盘、实例列表、容量统计、分区管理、历史同步等页面分别检查千分位、单位和符号展示。
   - 模拟 `0 / null / undefined / NaN` 的接口响应，确认 fallback 不报错。
2. **自动化 / 脚本**
   - 运行 `make test`（前端依赖后端 API 数据，重点验证不会破坏后端模板渲染）。
   - 若新增前端单元测试（可选），针对 `number-format.js` 的核心函数编写 Jest/uvu 测试并通过 `npm test` 执行。
3. **Lint / Quality**
   - `make quality` 确认 Python 侧通过。
   - 若引入 Node 工具链，确保 `package-lock` / `pnpm-lock` 等未被误加入。

## 风险与缓解

- **第三方库体积**：Numeral.js + locales 约 40KB gzip，需通过 CDN 缓存或 HTTP/2 复用降低影响；如需更小体积，可只保留 `zh-cn` locale。
- **脚本加载顺序**：必须在任何调用 `NumberFormat` 之前加载 Numeral，否则会出现 `numeral is not defined`；在 `base.html` 中保持 vendor → helper → feature 的顺序并添加守卫。
- **历史数据格式**：部分 API 返回字符串/百分比（如 `"12.3%"`），迁移时需要在封装层处理，避免 numeral 解析失败。
- **多语言支持**：若未来开放英文界面，只需在封装层切换 locale 即可，无需再次批量修改。

## 后续工作

1. 根据上述迁移顺序提交代码，实现 Numeral.js 接入与旧逻辑替换。
2. 在 PR 模板中补充“命名规范”与“数字格式化统一”检查项，提醒评审关注。
3. 根据上线反馈，评估是否将 `numeral` 打包成模块化资产（例如结合 Vite/ESBuild）以便长期维护。

