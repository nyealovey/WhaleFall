# 统一搜索与分页重构计划

## 目标
- 统一搜索参数与分页契约，适用于实例、凭据、日志、同步会话等列表。
- 标准化排序与过滤参数，避免 SQL 注入与性能问题。
- 提供一致的响应结构与错误反馈，便于前端复用。

## 现状
- 代码位置：`app/routes/instances.py`、`app/routes/credentials.py`、`app/routes/logs.py`、`app/routes/sync_sessions.py` 等。
- 已有能力：`app/models/unified_log.py` 支持搜索；其他列表在不同路由中各自实现。

## 风险
- 参数命名与行为不一致；分页越界与超大页风险。
- 过滤缺少索引匹配导致慢查询；排序字段未白名单化存在注入风险。

## 优先级与改进
- P0：
  - 统一请求参数：`page`（默认1）、`page_size`（默认20，最大100）、`sort_by`（白名单）、`sort_dir`（`asc|desc`）、`q`（全文或关键字）、`filters`（受控字段）。
  - 统一响应结构：`{items, total, page, page_size, sort}`；错误码 `PAGINATION_INVALID`、`FILTER_UNSUPPORTED`。
- P1：
  - 建立索引与查询优化建议；过滤字段白名单与枚举约束。
- P2：
  - 统一服务端缓存与搜索限流；高成本查询异步化与导出任务化。

## 产出与检查清单
- 搜索/分页契约文档与示例；字段白名单与安全约束。
- 索引与优化建议；慢查询监控与告警策略。