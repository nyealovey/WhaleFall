---
title: 调试与排障套路
aliases:
  - debugging
tags:
  - getting-started
  - getting-started/debugging
status: draft
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 从 error envelope / session / logs 快速反查到代码入口, 并给出可复制的自查命令
related:
  - "[[getting-started/local-dev]]"
  - "[[reference/errors/message-code-catalog]]"
  - "[[operations/observability-ops]]"
  - "[[API/api-v1-api-contract]]"
---

# 调试与排障套路

## 1. 先分清问题类型

你遇到的问题通常落在三类入口:

- Web UI: 页面报错/跳转异常/表单提交失败.
- API v1: `/api/v1/**` 返回 JSON envelope 失败.
- 后台任务: scheduler 触发或 action endpoint 触发, 任务跑失败或卡住.

建议先拿到以下 3 个定位锚点(能拿到多少算多少):

- `message_code`(= message_key): 稳定的错误码(可用于检索与归类).
- `context.request_id`: 一次请求链路的关联 id(可用于查日志).
- `session_id`: 同步会话 id(可用于查会话与实例级失败原因).

## 2. 从 API error envelope 反查(最快)

典型错误响应结构(示意, 字段以实际返回为准):

```json
{
  "success": false,
  "error": true,
  "error_id": "a1b2c3d4",
  "category": "authorization",
  "severity": "medium",
  "message_code": "CSRF_MISSING",
  "message": "缺少 CSRF 令牌",
  "timestamp": "2026-01-10T03:12:45+00:00",
  "recoverable": true,
  "suggestions": ["检查输入数据"],
  "context": {
    "request_id": "req_...",
    "user_id": 1,
    "url": "http://localhost:5001/api/v1/instances",
    "method": "POST"
  }
}
```

字段怎么用:

- `message_code`: 优先用它定位"哪类错误"(认证/鉴权/校验/下游连接/业务冲突).
- `context.request_id`: 去日志里做精确过滤.
- `context.url` + `method`: 回到 contract/路由定义确认命中的是哪个 endpoint.
- `error_id`: 一次错误实例的唯一 id; 更适合"复盘/沟通"而非代码检索.

常用反查命令(本地):

```bash
# 1) 先从 message_code 反查抛错位置
rg -n 'message_key=\"CSRF_MISSING\"' app

# 2) 如果 message 具有辨识度, 也可以直接搜文案(注意文案可能会改)
rg -n '缺少 CSRF 令牌' app

# 3) 按 endpoint 反查 namespace/route
rg -n 'ns\\.route\\(\"/actions/sync-accounts\"\\)' app/api/v1
```

## 3. 从 session 反查(同步/任务问题)

当 action endpoint 成功返回 `data.session_id` 后, 后续排障建议始终围绕 session 展开:

- 先查 `sync_sessions`: 这个 session 的 `status`, 以及 `failed_instances` 是否 > 0.
- 再查 `sync_instance_records`: 哪个 instance 失败, `error_message` 是什么, `sync_details` 里是否包含更细粒度上下文.
- 最后查 `unified_logs`: 结合 `session_id`/`instance_id` 过滤日志, 定位到具体 service/task 的 entry.

如果你在本地用 dev compose(PostgreSQL)跑:

```bash
make dev shell
```

PostgreSQL 自查 SQL(示例):

```sql
-- 最近的同步会话
select
  session_id,
  sync_category,
  status,
  started_at,
  completed_at,
  total_instances,
  failed_instances
from sync_sessions
order by created_at desc
limit 20;

-- 某个会话内, 每个实例的执行结果
select
  instance_id,
  instance_name,
  status,
  error_message,
  started_at,
  completed_at
from sync_instance_records
where session_id = '<session_id>'
order by created_at asc;

-- 用 session_id 过滤日志(注意: context 是 JSON)
select
  timestamp,
  level,
  module,
  message,
  context
from unified_logs
where context->>'session_id' = '<session_id>'
order by timestamp asc
limit 200;
```

> [!note]
> SQL 示例以 PostgreSQL 为准; 若你本地用的是 SQLite, 请使用 `sqlite3` 并按 SQLite JSON 查询语法调整.

## 4. 从 request_id 反查(日志 -> 代码入口)

如果 error envelope 给了 `context.request_id`, 这是最稳的链路锚点.

```sql
select
  timestamp,
  level,
  module,
  message,
  context->>'action' as action,
  context->>'session_id' as session_id,
  context->>'instance_id' as instance_id
from unified_logs
where context->>'request_id' = '<request_id>'
order by timestamp asc
limit 500;
```

拿到 `module`/`action` 后:

```bash
rg -n \"action=\\\"<action>\\\"\" app
rg -n \"module=\\\"<module>\\\"\" app
```

## 5. 常用 rg 自查套路

按入口找代码:

- 找 API v1 endpoint: `rg -n 'ns\\.route\\(\"/path\"' app/api/v1/namespaces`
- 找 Web route: `rg -n 'Blueprint\\(\"' app/routes && rg -n 'add_url_rule\\(' app/routes`
- 找 service: `rg -n 'class .*Service' app/services`

按错误码找触发点:

```bash
rg -n 'message_key=\"DATABASE_CONNECTION_ERROR\"' app
rg -n 'message_key=\"SYNC_DATA_ERROR\"' app
rg -n 'message_key=\"CLASSIFICATION_IN_USE\"' app
rg -n 'message_key=\"INVALID_DSL_EXPRESSION\"' app
```

按日志字段找入口(比如 session_id/instance_id):

```bash
rg -n 'session_id=' app
rg -n 'instance_id=' app
```

## 6. 推荐入口文档(更完整的 SOP)

- 可观测与排障 Runbook: [[operations/observability-ops]]
- API contract 索引: [[API/api-v1-api-contract]]
- 错误封套与失败语义:
  - [[standards/backend/hard/error-message-schema-unification]]
  - [[standards/backend/hard/action-endpoint-failure-semantics]]
