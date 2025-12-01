# ColorTokens 调色盘重构方案

## 背景
当前 `ColorTokens` 仅暴露了 5 个 `--chart-color-*` 变量，图表 TOP20 数据系列会循环使用有限色值，导致视觉重复与可读性下降。此外，橙色系只能通过单一 CSS 变量获取，不支持透明度或亮度衍生，限制了告警/容量等模块的渐层表现力。

## 问题
1. **色值数量不足**：前端图表工具（ECharts/Grid.js 插件）在展示 10+ 数据列时出现颜色重复，用户难以区分系列。
2. **色彩一致性难维护**：页面局部编码临时 HEX/RGB 颜色，违背“禁止手写颜色值”的规范。
3. **橙色调无法调节**：没有提供包含透明度、对比度参数的橙色 token，强调态/背景态/边框态只能手写 `rgba()`。

## 目标
1. 将 `ColorTokens` 扩展为可产出 ≥ 24 种稳定色值的调色盘，确保 TOP20 系列无重复。
2. 在 CSS variable 层定义橙色系的多档强度（含透明度、hover/active），供 JS 直接引用。
3. 提供统一的取色工具（JS + CSS），支持 `withAlpha`、亮度/饱和度偏移等参数化调用，减少手写颜色。

## 重构方案
### 1. 扩展 CSS 变量
- 在 `app/static/css/variables.css` 中新增 `--chart-color-*` 至少 12 条基础色（含冷暖调），再通过程序组合生成 24 条序列。
- 为橙色系定义：
  - `--orange-base`：主色。
  - `--orange-muted`：背景/填充（使用 `color-mix` 淡化 70%）。
  - `--orange-strong`：强调/边框。
  - `--orange-alpha-20`、`--orange-alpha-40`：通过 `color-mix` 预计算透明度，保证 CSS 与 JS 引用一致。

### 2. JS 侧调色算法
- 在 `color-tokens.js` 中缓存 CSS palette 数组，若长度 < 20，则使用算法生成补充色：
  - 对每个基础色生成 `lighten`、`darken`、`alpha` 变体。
  - 采用 HSL 转换（可借助 `CSSColorValue` polyfill 或自实现）实现亮度偏移 ±15%。
- 新增 `getSequentialPalette(size, { strategy })` API，默认返回 size 长度的无重复色列表。
- `getChartColor` 改为优先使用扩展 palette，若仍不足则退化到 accent 渐变。

### 3. 橙色透明参数入口
- 新增 `getOrangeColor({ alpha = 1, tone = 'base' })` 方法，内部基于 `--orange-*` 变量和 `withAlpha` 组合。
- 在需要橙色渐层（如 TOP20 柱状 hover）处调用该方法，禁止再写死 RGBA。

### 4. 清理与兼容
- 搜索所有 `#ffa500`、`rgba(255, 165, 0` 等硬编码值，替换为 `ColorTokens.getOrangeColor` 或 CSS token。
- 对旧的 5 色 palette 使用 `console.warn` 标记，指导同事迁移。
- 编写文档/示例演示如何在 echarts/Chart.js/Gridwrapper 中注入扩展 palette。

## 交付物
1. `variables.css`：新增 chart/橙色变量与注释。
2. `color-tokens.js`：
   - `getChartPalette` 支持动态补全。
   - 新增 `getSequentialPalette`、`getOrangeColor`、`generateVariants` 等工具。
3. `docs/frontend/theme_guidelines.md`：更新取色规范与代码片段。
4. 覆盖 TOP20 用例的单元测试（可借 Jest/Playwright 截屏 diff）。

## 验证
1. 运行 `npm run test:colors`（新增脚本）验证 JS palette 生成逻辑。
2. 在数据库/实例 TOP20 报表中截屏比对，确认 20 条曲线颜色互异，图例文字清晰。
3. Lighthouse 对比色彩对比度（WCAG AA ≥ 4.5:1）。

## 风险与缓解
- **浏览器兼容**：`color-mix` 在旧版 Safari 需降级。方案：提供 fallback（直接写 RGB），发布前在 BrowserStack 验证。
- **主题切换影响**：扩展变量需在暗色/橙色主题各自维护。方案：同步更新 `theme-orange.css` 等文件，确保 token 全部存在。
- **性能**：生成 palette 时避免每次调用都解析 CSS，可缓存并监听 `themechange` 事件刷新。

## 实施步骤
1. 定义 CSS token 并发布 PR，确保命名通过 `refactor_naming.sh`。
2. 重构 `color-tokens.js`，补充单元测试。
3. 替换现有模块的硬编码颜色，重点检查图表、告警标签、TOP20 页面。
4. 更新文档 + 截图，执行回归。
5. 发布并在下个迭代跟踪反馈。
