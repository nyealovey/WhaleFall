# Grid.js 迁移标准（列表页）

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：所有使用 Grid.js 的列表页（含筛选/分页/排序/批量操作）

## 1. 目标

- 列表页交互一致：分页/排序/筛选参数口径统一，URL 可分享，刷新不漂移。
- 后端契约稳定：列表 API 返回结构统一，避免前端写兼容分支。
- 性能可控：高频筛选/搜索有防抖，生产环境无无意义调试日志。

## 2. 前端标准（必须遵守）

### 2.1 必须使用 GridWrapper

- MUST：使用 `app/static/js/common/grid-wrapper.js` 的 `GridWrapper` 作为统一封装。
- MUST NOT：页面内直接 new `gridjs.Grid` 自行拼分页/排序参数。

### 2.2 分页与排序参数

- MUST：分页使用 `page`（从 1 开始）与 `page_size`。
- SHOULD：仅在兼容旧链接时识别 `limit/pageSize`，并尽早转写为 `page_size`。

规范详见：`docs/standards/ui/pagination-sorting-parameter-guidelines.md`。

### 2.3 刷新与日志

- MUST：刷新使用 `grid.updateConfig(...)` + `grid.forceRender()`。
- MUST NOT：直接操纵 Grid.js 内部 `pipeline/store`。
- MUST：生产环境默认不输出 GridWrapper 调试日志；仅在 `window.DEBUG_GRID_WRAPPER=true` 时允许 `console.debug`。

规范详见：`docs/standards/ui/grid-wrapper-performance-logging-guidelines.md`。

## 3. 后端契约（列表 API）

### 3.1 输入参数

列表接口必须支持：

- `page`：页码，从 1 开始
- `page_size`：每页数量
- `sort`：排序字段（可选）
- `order`：`asc|desc`（可选）
- 其余筛选字段：允许按页面需要追加（由 GridWrapper `setFilters(...)` 透传为 query params）

### 3.2 返回结构（统一）

- MUST：返回 `items` 与 `total`，且 `total` 为满足当前筛选条件的总数。
- SHOULD：统一走项目的成功封套（例如 `jsonify_unified_success(data=...)`）。

推荐示例：

```json
{
  "success": true,
  "data": {
    "items": [],
    "total": 0
  }
}
```

> 说明：前端 GridWrapper 的 `server.then`/`server.total` 默认会优先读取 `response.data`，因此 `data.items/data.total` 为推荐口径。

### 3.3 错误结构

- MUST：避免 `error/message` 字段漂移；统一规范见：`docs/standards/backend/error-message-schema-unification.md`。

## 4. 迁移检查清单（Checklist）

- [ ] 页面使用 `GridWrapper` 初始化表格。
- [ ] 后端接口支持 `page/page_size`，并返回 `data.items/data.total`。
- [ ] 若启用排序：后端支持 `sort/order`。
- [ ] 筛选输入具备 debounce（FilterCard 或等价实现）。
- [ ] 无新增 GridWrapper 生产环境 `console.log`。
- [ ] 迁移完成后更新：`docs/README.md` 与对应目录索引（如需要）。
