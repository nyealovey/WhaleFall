# Grid.js 列表页迁移标准

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：所有使用 Grid.js 的列表页（含筛选/分页/排序/批量操作）

## 目的

- 列表页交互一致：分页/排序/筛选参数口径统一，URL 可分享，刷新不漂移。
- 后端契约稳定：列表 API 返回结构统一，避免前端写兼容分支。
- 性能可控：高频筛选/搜索有防抖，生产环境无无意义调试日志。

## 适用范围

- 前端：所有列表页（Grid.js）与 `GridWrapper` 封装。
- 后端：所有列表 API（分页/排序/筛选/批量操作依赖的查询接口）。

## 规则（MUST/SHOULD/MAY）

### 1) 前端（必须遵守）

- MUST：使用 `app/static/js/common/grid-wrapper.js` 的 `GridWrapper` 作为统一封装。
- MUST NOT：页面内直接 new `gridjs.Grid` 自行拼分页/排序参数。

#### 分页与排序参数

- MUST：分页使用 `page`（从 1 开始）与 `page_size`。
- SHOULD：仅在兼容旧链接时识别 `limit/pageSize`，并尽早转写为 `page_size`。

详见：[分页与排序参数规范](./pagination-sorting-parameter-guidelines.md)。

#### 刷新与日志

- MUST：刷新使用 `grid.updateConfig(...)` + `grid.forceRender()`。
- MUST NOT：直接操纵 Grid.js 内部 `pipeline/store`。
- MUST：生产环境默认不输出 GridWrapper 调试日志；仅在 `window.DEBUG_GRID_WRAPPER=true` 时允许 `console.debug`。

详见：[GridWrapper 性能与日志](./grid-wrapper-performance-logging-guidelines.md)。

### 2) 后端契约（列表 API）

#### 输入参数

- MUST：支持 `page/page_size`。
- SHOULD：排序支持 `sort/order`（`asc|desc`），不需要排序的接口可以不实现。
- MAY：其余筛选字段按页面需要追加（由 GridWrapper 透传为 query params）。

#### 返回结构（推荐）

- MUST：返回 `items` 与 `total`，且 `total` 为满足当前筛选条件的总数。
- SHOULD：统一走成功封套（例如 `jsonify_unified_success(data=...)`），并把列表数据放在 `data.items/data.total`。

示例：

```json
{
  "success": true,
  "data": {
    "items": [],
    "total": 0
  }
}
```

#### 错误结构

- MUST：避免 `error/message` 字段漂移；统一规范见：[错误消息字段统一](../backend/error-message-schema-unification.md)。

## 正反例

### 正例：迁移完成后只保留统一参数

- URL/请求统一使用 `page/page_size`，兼容字段只存在于解析层。

### 反例：页面自行拼分页字段

- 某些页面继续发送 `limit` 或 `pageSize`，导致后端兼容永远无法清零。

## 门禁/检查方式

- 分页参数门禁：`./scripts/code_review/pagination_param_guard.sh`
- GridWrapper 日志门禁：`./scripts/code_review/grid_wrapper_log_guard.sh`
- 结果结构漂移门禁（如涉及错误字段）：`./scripts/code_review/error_message_drift_guard.sh`

## Checklist（迁移自检）

- [ ] 页面使用 `GridWrapper` 初始化表格。
- [ ] 后端接口支持 `page/page_size`，并返回 `data.items/data.total`。
- [ ] 若启用排序：后端支持 `sort/order`。
- [ ] 筛选输入具备 debounce（FilterCard 或等价实现）。
- [ ] 无新增 GridWrapper 生产环境 `console.log`。

## 变更历史

- 2025-12-25：新增标准文档，统一 GridWrapper 落点、参数口径与门禁入口。
