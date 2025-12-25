# GridWrapper 性能与日志

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-23  
> 更新：2025-12-25  
> 范围：所有使用 `GridWrapper` 的列表页与 `app/static/js/common/grid-wrapper.js`

## 目的

- 生产环境默认不输出 GridWrapper 调试日志，避免控制台噪音干扰排障。
- 列表刷新路径稳定可预测，避免依赖 Grid.js 内部实现导致回归。
- 高频筛选/搜索具备防抖/节流，避免频繁请求造成卡顿与资源浪费。

## 适用范围

- `GridWrapper` 相关实现与调用方页面脚本。
- 使用 Grid.js 的列表页（含筛选/分页/排序）。

## 规则（MUST/SHOULD/MAY）

### 1) 日志规范

- MUST NOT：在 GridWrapper 内常驻 `console.log`。
- MUST：调试日志仅允许通过开关输出，且使用 `console.debug`：
  - 开关：`window.DEBUG_GRID_WRAPPER = true`
  - 统一入口：`GridWrapper` 内部 `debugLog(...)`

### 2) 刷新与数据加载

- MUST：刷新使用 `grid.updateConfig(...)` + `grid.forceRender()`。
- MUST NOT：直接操纵 Grid.js 内部 `pipeline/store` 或调用内部方法（例如 `pipeline.process()`）。

### 3) 高频输入防抖（推荐）

- SHOULD：FilterCard 场景优先使用 `UI.createFilterCard({ autoSubmitDebounce: 200~400 })`。
- SHOULD：非 FilterCard 场景在调用 `GridWrapper.setFilters(...)` 前自行做 debounce，避免连发刷新。

## 正反例

### 正例：刷新使用公共 API

- `grid.updateConfig(...)` → `grid.forceRender()`。

### 反例：直接操纵内部实现

- 修改 `grid.config.pipeline`、调用 `pipeline.process()` 等内部方法。

## 门禁/检查方式

- 脚本：`./scripts/ci/grid-wrapper-log-guard.sh`
- 规则：禁止 `app/static/js/common/grid-wrapper.js` 出现 `console.log`

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 补齐标准结构与正反例，明确生产日志与刷新路径约束。
