# 需统一分页的 API 审核与建议

目标
- 为返回大列表的接口统一分页策略，避免 `all()` 全量返回导致前端渲染与网络压力。
- 保持一个标准：`page` + `per_page`（默认 1 和 20），响应统一提供 `meta`。

建议的统一响应
```json
{
  "success": true,
  "data": [ /* items */ ],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 123,
    "pages": 7
  }
}
```

已发现的未分页/可能需要分页的端点（样例）
- `instances.py`：`/api` 列表（当前 `query.order_by(Instance.id).all()`）。
- `tags.py`：`/api/all_tags`, `/api/instances`, `/api/all`（聚合列表）。
- `credentials.py`：`/api/list`（若存在分页参数，需统一到标准响应）。
- `account.py`：`/api/list` 与按实例检索账户的列表接口（数据量可能较大）。
- `sync_sessions.py`：会话历史列表与状态查询（长时间运行会膨胀）。
- `aggregations.py`：聚合输出如为列表，需分页或后台聚合后按页取数。
- `partition.py` / `database_stats.py`：分区或统计列表接口。
- 其他：任何 `/api/*` 返回可变长数组的 GET 路由。

落地建议
1) 统一参数解析：`page = max(int(request.args.get("page", 1)), 1)`, `per_page = min(max(int(..., 20), 1), 100)`。
2) 统一 ORM 查询：`query.paginate(page=page, per_page=per_page, error_out=False)`。
3) 统一响应：使用 `APIResponse.success_response(data=items, meta=pagination_meta)`。
4) 前端统一：组件层支持 `page/per_page` 与 `meta.total/pages`，避免各接口自定义字段。

注意事项
- 日志与错误：分页入参非法，统一使用 `APIResponse.error_response` 返回 `VALIDATION_ERROR`。
- 大数据场景：分页并不替代筛选与排序，建议配合统一的过滤参数（`q`, `sort_by`, `order`）。