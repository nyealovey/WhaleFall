# 色彩收敛专项实施手册（2025-11-27）

## 背景与目标
- 参考《docs/refactoring/ui/color-system-unification.md》已经完成变量/token 级别的“橙色主色 + 单色层级”改造，但界面仍存在大量页面私有色和多彩卡片（见最新仪表盘/实例列表截图），导致整体感不足、维护色值困难。
- 本专项目标是在 2025-12-15 前，将除状态语义需要外的所有自定义颜色收敛到“单一主色 + 中性灰阶”，并为状态语义建立受控色板（成功/警告/错误/信息各 1 色）。
- 验收要求：`rg "#[0-9a-fA-F]{3,6}" app/static/css app/static/js` 仅输出 `variables.css`、`theme-orange.css` 两个文件；页面截图中除状态徽章/图表外不再出现多彩卡片。

## 现状扫描（2025-11-27）
### 1. Token 层（`app/static/css/variables.css:5-44`）
| 分类 | Token | 当前值 | 备注 |
| --- | --- | --- | --- |
| 主背景 | `--surface-base` | `#f4f6fb` | 期望保留。
| 提升层 | `--surface-elevated` | `#ffffff` | 期望保留。
| 主色 | `--accent-primary` | `#f97316` | 所有按钮/卡片默认色。
| 中性色 | `--gray-050` ~ `--gray-900` | `#f8f9fa`~`#212529` | 作为唯一灰阶来源。
| 语义色 | `--success-color` 等 | 绿色/红色/黄色/蓝色 | 允许存在，但仅供状态徽章/图表语义使用。
| 渐变 | `--gradient-*` | 多条线性渐变 | 仍保留，计划阶段移除。

### 2. CSS 硬编码颜色（节选）
| 模块 | 文件 (行) | 颜色 | 用途 | 问题 |
| --- | --- | --- | --- | --- |
| 定时任务 | `app/static/css/pages/admin/scheduler.css:13-216` | `#18bc9c/#f39c12/#e74c3c/#495057/#6c757d` | 徽章、卡片阴影、进度边 | 沿用 Flatly 绿色/橙色/红色，未走变量体系。
| 凭据详情 | `pages/credentials/detail.css:7-77` | `#18bc9c/#e9ecef/#f8f9fa` 等 | 提示块边框、徽章文字 | 与全局 token 重复，完全可使用变量。
| 凭据列表 | `pages/credentials/list.css:69-91` | `#0d6efd/#198754/#dc3545/#f5c518/#2f2f2f` | 列表中的状态徽章 | 混入 Bootstrap 默认蓝/绿/红，与橙色主色冲突。
| 标签弹窗 | `components/tag-selector.css:23-40` | `#0d6efd/#e9f3ff/#fff` | 选中态背景/文字 | 未使用 token，且默认蓝色又回来了。
| 日志中心 | `pages/history/logs.css:171-196` | `#f8f9fa/#e9ecef/#495057/#000` | 代码块 & json block | 中性灰可改为变量，黑色可用 `var(--text-primary)`。
| 历史同步 | `pages/history/sync-sessions.css:97` | `#f8fbfd` | 背景 | 接近 `--surface-base`，应复用变量。

> 统计命令：`rg -n "#[0-9a-fA-F]{3,6}" app/static/css > /tmp/css_colors_detail.txt`。

### 3. JS/图表直接写色值
| 区域 | 文件 | 颜色集合 | 用途 | 建议 |
| --- | --- | --- | --- | --- |
| 容量/分区图表 | `app/static/js/modules/views/admin/partitions/charts/partitions-chart.js:78-195` | `#FF6384/#36A2EB/#4BC0C0/...` 16+ 种 | Grid/Chart.js 数据列 | 建立 `chart_palette` 模块，统一映射到主色/语义色。
| 图表通用 | `modules/views/components/charts/transformers.js` | 与上相同 | 图例与系列颜色工厂 | 换成 token 驱动 `CSS custom properties` 或单色 + 透明度梯度。
| 图表 Tooltip | `components/charts/chart-renderer.js:15-175` | `#f8f9fa/#dee2e6/#212529` | Tooltip 背景、边框、文字 | 替换为 `var(--surface-elevated)` 等。
| 标签徽章 | `modules/views/accounts/list.js:309-311` | `#fff`（文字） | 自定义标签 | 文本色可改 `var(--surface-elevated)` 并结合 `mix-blend`。

### 4. `rgba()/linear-gradient` 仍存留
- `app/static/css/pages/history/logs.css`：多处 `rgba(231, 76, 60, 0.05)` 等；建议统一改为 `color-mix(in srgb, var(--danger-color) 5%, transparent)`，便于主色切换。
- `app/static/css/pages/history/sync-sessions.css`、`pages/tags/batch-assign.css`：使用 `rgba(24, 188, 156, X)`，这是 Flatly 的绿色，需替换成橙色/灰阶。
- `app/static/css/variables.css:39-43` 仍定义多条渐变，后续阶段决定是否保留在图表或进度条中。

### 5. 第三方依赖
- Bootstrap Flatly、Tom Select、gridjs、nprogress 等 vendor CSS 自带色值。短期不改 vendor，但需要在自定义覆盖中抹平（例如 `theme-orange.css` 已改 primary；针对 gridjs legend 需额外覆盖）。

## 问题总结
1. **主色回退**：凭据/标签/图表中依旧使用 Flatly 默认蓝 (`#0d6efd`) 或绿 (`#18bc9c`)；造成页面出现 5+ 基础色。
2. **语义色泛滥**：状态徽章使用“红/绿/黄/蓝 + 各种饱和度”而非受控 token，难以与浅背景融合。
3. **数据可视化色板失控**：Chart.js 直接塞入 16 种对比色，破坏“单色 + 层次”策略。
4. **灰阶重复**：大量 `#f8f9fa/#e9ecef/#495057` 等重复手写，既和 token 相同又难以统一。
5. **透明度写死**：`rgba(231, 76, 60, 0.05)` 等不便随主题调整。

## 重构目标
- 只保留以下色板：
  - `accent`: `--accent-primary`（橙）+ `--accent-primary-hover`。
  - `neutrals`: `--surface-*`、`--gray-*`。
  - `status`: `--success-color`、`--warning-color`、`--danger-color`、`--info-color`。
- 封装以下能力：
  1. `@mixin apply-status($status)` 或 CSS 工具类，集中控制徽章背景/描边/文字。
  2. `chartPalette.get(n)` JavaScript 模块，通过 `CSS custom properties` 派生单色序列（主色不同透明度 + 灰阶辅助）。
  3. `tone(var(--accent-primary), opacity)` 工具，替换所有 `rgba` 手写值。

## 执行计划
### Phase 0（本周）— 自动巡检管线
1. 新增 `scripts/audit_colors.py`：扫描 `app/static/{css,js}` 中的 HEX/RGBA，输出 CSV；CI 中 `make quality` 调用，若检测到 `variables.css` 以外文件含硬编码色则失败。
2. 将现有 `docs/refactoring/ui/color-system-unification.md` 中的巡检步骤升级为 checklist，并同步到 PR 模板。

### Phase 1（12/02 前）— CSS 层归一
1. 替换所有 `app/static/css/pages/**` 中的 HEX 为变量：
   - 定时任务/凭据/标签/日志历史/同步等页面，统一引用 `var(--surface-*)`、`var(--text-*)`、`var(--status-*)`。
   - 删除 `--gradient-*` 依赖：保留 `chart` 类组件可用 `linear-gradient`，其余卡片改为纯色 + 阴影。
2. 为状态徽章引入 `badge-status--success` 等类（或基于 data-attribute），只允许引用 4 个语义色。

### Phase 2（12/05 前）— JS & 图表统一
1. 新建 `app/static/js/modules/theme/color-tokens.js`：读取 `getComputedStyle(document.documentElement)` 中的 token，暴露 `getAccent(alpha)`、`getStatus('warning', alpha)`。
2. 更新所有 Chart.js 配置：
   - 折线仅使用 `accent` 不同透明度 (`accent-90/60/30`)；
   - 堆叠/饼图最多 4 色，对应状态语义；
   - Tooltip/legend 背景走 `var(--surface-elevated)`。
3. 标签/分类颜色若需要用户自定义，则在保存时做合法性校验，默认仍走 token。

### Phase 3（12/10 前）— 页面验收与截图
1. 覆盖关键页面（仪表盘、日志中心、实例/账户列表、凭据、任务调度、标签、历史记录），按 1280px/1440px 截屏。
2. 对比截图 + DevTools 取色结果附到文档，确认“除状态/图表外卡片仅使用橙/灰阶”。

### Phase 4（12/15 前）— 固化机制
1. 在 `make quality` 中加入 `scripts/audit_colors.py`；CI 不允许新增硬编码色。
2. 在组件库中补充 `README`，明确“新增组件若需色彩，请先增加 token 再引用”。
3. 归档本手册到 `docs/refactoring/ui/`，并在 `CHANGELOG` 中记录完成。

## 验收清单
- [ ] `rg "#[0-9a-fA-F]{3,6}" app/static/css app/static/js` 仅输出 `variables.css`、`theme-orange.css`、`vendor/**`。
- [ ] `rg -n "rgba" app/static/css` 中只剩 `variables.css` 或工具类中的 `color-mix`。
- [ ] `pages/**` 模板中所有卡片类使用 `bg-primary`（映射橙色）或 `bg-surface`，无手动 `style="color:#..."`。
- [ ] Chart/legend 色板统一由 `color-tokens.js` 导出。
- [ ] `docs/refactoring/ui/color-system-unification.md` 附录中新增本次截图对比。

## 附录：扫描命令
```bash
# CSS/JS 中的 HEX
rg -n "#[0-9a-fA-F]{3,6}(?![0-9a-zA-Z_])" app/static/css app/static/js > tmp/hex_colors.txt
# CSS 中的 rgba/渐变
rg -n "rgba\(" app/static/css > tmp/rgba.txt
rg -n "linear-gradient" app/static/css > tmp/gradient.txt
```

> 以上命令输出样例见 `/tmp/css_colors_detail.txt`，建议纳入脚本并在 PR 模板中上传最新结果。
