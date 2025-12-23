# GridWrapper 表格性能与日志规范

## 目标
1. 生产环境默认不输出 GridWrapper 调试日志，避免控制台噪音干扰排障。
2. 表格刷新必须走 Grid.js 公共 API（`updateConfig` / `forceRender`），禁止直接操纵 `pipeline/store` 等内部实现，保证可预测性与可维护性。
3. 高频筛选/搜索必须具备节流/防抖能力，避免“每次输入都发请求”造成卡顿与资源浪费。

## 日志规范
### 1) 禁止项（默认）
- 禁止在 GridWrapper 内常驻 `console.log`。
- 禁止把请求 URL、filters、大对象在生产环境打印到控制台。

### 2) 允许项（调试开关）
- 仅允许通过调试开关输出，且使用 `console.debug`：
  - 开关：`window.DEBUG_GRID_WRAPPER = true`
  - 统一入口：`GridWrapper` 内部 `debugLog(...)`

## 刷新与数据加载规范
### 1) 刷新路径（必须）
- 必须使用：`grid.updateConfig(...)` + `grid.forceRender()`。
- 禁止：直接调用/修改 `grid.config.pipeline`、`grid.config.store`、`pipeline.process()` 等内部方法。

### 2) 高频输入防抖（推荐）
- FilterCard 场景：优先使用 `UI.createFilterCard({ autoSubmitDebounce: 200~400 })`，只在用户停止输入后触发表格刷新。
- 若页面未使用 FilterCard：调用 `GridWrapper.setFilters(...)` 前自行做 debounce（例如 lodash debounce），避免连发刷新。

## 门禁（禁止回归）
- 运行：`./scripts/code_review/grid_wrapper_log_guard.sh`
- 规则：禁止 `app/static/js/common/grid-wrapper.js` 出现 `console.log`。

