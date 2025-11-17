# Day.js 时间处理重构方案

## 背景与目标

当前前端依赖 `app/static/js/common/time-utils.js` 手写实现日期解析、格式化与相对时间逻辑，虽然与后端 `time_utils.py` 大体保持一致，但存在下列问题：

- **功能分散且难扩展**：自定义代码仅覆盖有限格式，新增需求（例如毫秒精度、UTC 处理、时区切换）需要手工拼接。
- **维护成本高**：与后端保持同构需要人工比对，缺乏成熟库的测试与生态支持。
- **缺乏链式 API**：复杂计算（如加减日期、获取区间）只能手写辅助函数，易引入偏差。

目标是以 [Day.js](https://day.js.org/) 为核心，替换前端 `time-utils.js` 的实现，同时保持现有 API 行为不变，逐步释放 Day.js 的插件能力（timezone、relativeTime、duration 等），为后续需求提供统一基础。

## 现状梳理

| 场景 | 文件/函数 | 行为 |
| --- | --- | --- |
| 通用格式化 | `TimeUtils.formatDateTime/formatDate/formatTimeOnly` | 手动拼接 `YYYY-MM-DD HH:mm:ss` 等字符串 |
| 中文格式 | `formatChineseDateTimeString` | 写死 “年/月/日” 模版 |
| 相对时间 | `formatRelativeTime` | 通过 `Date` 差值计算 “刚刚/分钟前/小时前...” |
| 智能区间 | `formatSmartTime`, `getRangeLabel` 等（文件后半段） | 多处使用 `new Date()`、`Intl` |
| 全局暴露 | `window.formatTime`, `window.formatDateTime`... | 模板和脚本直接依赖 |

> 备注：文件还包含 `parseTime`, `toChinaTime`, `formatDuration`, `buildTimeRange` 等辅助方法，同样需要兼容看齐。

## Day.js 方案

1. **依赖选择**
   - 核心 `dayjs.min.js`
   - 插件：`utc`, `timezone`, `localizedFormat`, `relativeTime`, `duration`, `customParseFormat`
   - 体积约 20 KB gzip，可接受，并支持按需扩展其他插件。
2. **加载方式**
   - 与 Numeral.js 类似，放入 `app/static/vendor/dayjs/`（含插件文件）。
   - 在 `base.html` 中引入：`dayjs.min.js` → 插件 → `time-utils.js`（重写后作为封装层）。
3. **封装策略**
   - 保持 `TimeUtils` 对外 API 不变，但内部调用 Day.js。
   - 在初始化阶段设置 `dayjs.extend(...)`、`dayjs.locale('zh-cn')`、`dayjs.tz.setDefault('Asia/Shanghai')`。
   - 新增 `createSafeDayjs(input)` 帮助函数，统一处理字符串、时间戳、Date。
   - 导出 `window.dayjs` 供调试/高级场景使用，但仍建议通过 `TimeUtils` 访问。

## 重构步骤

1. **依赖落地**
   - 下载 `dayjs.min.js` 与所需插件（可来自 CDN 或 pnpm vendor），存放 `app/static/vendor/dayjs/`。
   - 更新 `base.html`：在 `axios` 之后加载 Day.js，确保所有页面可用。
2. **重写 `time-utils.js`**
   - 保留现有 API 名称与导出（包括 `window.formatDateTime` 等别名）。
   - 内部实现替换为 Day.js：`dayjs(value).tz().format('YYYY-MM-DD HH:mm:ss')`。
   - 使用 `dayjs().fromNow()` 实现相对时间，保持“刚刚/分钟前/小时前”中文输出。
   - 用 `dayjs.duration`、`dayjs.range`（自实现）处理时间区间。
3. **兼容校验**
   - 对照后端 `time_utils.py` 的格式定义，确保格式字符串一致。
   - 为无法直接匹配的函数（例如 `formatSmartTime`）编写单元测试或示例数据。
4. **应用侧验证**
   - 关注使用 `window.format*` 的模板/脚本（grep 搜索 `formatTime(` 等），确保函数签名无变化。
   - 对比关键页面：仪表盘、实例详情、历史同步、批量任务等时间展示。
5. **脚本检查**
   - 运行 `./scripts/refactor_naming.sh --dry-run` 确保未触发命名规范。
   - 若新增 npm 资源或脚本，更新 `docs/` 指南（必要时）。

## API 映射示例

| 现有函数 | Day.js 实现思路 |
| --- | --- |
| `formatDateTime(timestamp)` | `createSafeDayjs(timestamp)?.format('YYYY-MM-DD HH:mm:ss') || '-'` |
| `formatRelativeTime(timestamp)` | `createSafeDayjs(timestamp)?.fromNow() || '-'` |
| `formatSmartTime(timestamp)` | 根据当前时间差和 Day.js 判断返回日期/时间 |
| `parseTime(value)` | `dayjs(value).isValid() ? dayjs(value).toDate() : null` |
| `buildTimeRange(rangeType)` | 使用 `dayjs().startOf(...)` / `endOf(...)` |

## 测试与验证

1. **自动化/脚本**
   - 运行 `pytest` 关注前端模板渲染。
   - 若添加前端测试，可考虑简单的 `vitest`/`uvu` 针对 `time-utils.js` 核心函数。
2. **手工走查**
   - 核对关键页面（已登录仪表盘、历史页面、容量统计等）的时间展示。
   - 验证相对时间、区间计算在跨天/跨月场景下的表现（可临时修改系统时间或 mock）。
3. **回归对比**
   - 采样一批真实 API 响应（含 UTC/本地时间），确保与旧逻辑输出一致。

## 风险与缓解

- **体积增加**：避免引入不必要插件；如体积敏感可只包含 `zh-cn` locale。
- **时区差异**：Day.js 默认使用浏览器时区，必须在初始化后调用 `dayjs.tz.setDefault('Asia/Shanghai')`。
- **旧代码直接操作 Date**：若有脚本直接使用 `new Date()` 与 `TimeUtils` 混用，需确认不会造成重复转换。
- **迁移跨度大**：建议先上线 Day.js 版本的 `TimeUtils`，观察日志/反馈后再逐步开放 Day.js 其它 API。

## 后续工作

1. 按本方案实施时间工具重写，并提交 `feat: adopt dayjs time utils` 类别的 commit。
2. 在 `docs/development/STYLE_GUIDE.md` 或相关章节补充“统一使用 Day.js，通过 `TimeUtils` 出口”的约束。
3. 评估是否在 `make quality` 中加入简单的时间函数 smoke test，确保未来改动可快速发现问题。
