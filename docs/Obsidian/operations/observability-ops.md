---
title: 可观测与排障(Observability Ops)
aliases:
  - observability-ops
  - logs-ops
tags:
  - operations
  - operations/observability
  - logs
  - troubleshooting
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 日志字段, 定位路径, 会话/任务排障 SOP, 以及关键自查命令
related:
  - "[[operations/README|operations]]"
  - "[[architecture/developer-entrypoint]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/action-endpoint-failure-semantics]]"
  - "[[standards/backend/write-operation-boundary]]"
  - "[[reference/service/sync-session-service]]"
---

# 可观测与排障(Observability Ops)

> [!note] 目标
> 给出一条可复制执行的定位路径: 从用户反馈 -> 找到 session/log -> 复现与根因 -> 验证修复.

## 1. 适用场景

- 用户反馈 "同步失败/卡住/无提示/unknown".
- 后台任务执行异常, 需要定位失败实例与失败原因.
- API 返回错误封套, 需要快速关联到日志与上下文.

## 2. 前置条件

- 有权限访问:
  - 会话中心: `/history/sessions`(已登录 + view 权限).
  - 日志中心: `/history/logs`(admin).
- 如需直接查 DB: 具备数据库只读权限(生产环境强制走审计流程).

## 3. 日志字段(统一口径)

### 3.1 存储位置

- 结构化日志落库表: `UnifiedLog`(`app/models/unified_log.py`).
- 写入方式: structlog -> `DatabaseLogHandler` -> `LogQueueWorker` 批量写入(`app/utils/logging/handlers.py`, `app/utils/logging/queue_worker.py`).
- 额外输出: 非 testing 环境会写入 `LOG_FILE`(默认 `userdata/logs/app.log`, 见 `app/settings.py`).

### 3.2 常见字段

UnifiedLog 的 schema:
- `timestamp`, `level`, `module`, `message`, `traceback`, `context`.

`context` 常见键(按来源归类):
- Request: `url`, `method`, `ip_address`, `user_agent`
- Actor: `current_user_id`, `current_username`, `current_user_role`, `is_admin`
- RouteSafety: `module`, `action`, `actor_id`, `error_type`, `error_message`, `commit_failed`, `unexpected`
- Domain: `session_id`, `instance_id`, `db_type`, `credential_id`, `task_name`(建议按业务补齐)

> [!important] 敏感字段
> 日志 handler 会对 `access_token/refresh_token/authorization/cookie/x-csrf-token` 等字段做 scrub, 但仍建议不要主动写入敏感数据.

## 4. 定位路径(推荐 SOP)

### 4.1 从 API 错误封套开始

当拿到错误响应(JSON envelope)时:
- 先记录 `message_code` 与 `message`, 判断是 "业务失败" 还是 "异常"(见 [[standards/backend/action-endpoint-failure-semantics]]).
- `message_code` 的对外语义与常见触发点见: [[reference/errors/message-code-catalog]].
- 如果响应包含 `context.session_id`, 直接进入 [[#4.2 会话排障 SOP]].
- 如果响应包含 `context.request_id`, 在日志中心按 request_id 过滤(如果为空, 走时间窗口 + module/action 搜索).

### 4.2 会话排障 SOP(同步/批量/任务)

1) 打开会话中心 `/history/sessions`, 按时间范围与类型筛选.
2) 获取 `session_id`, 关注:
   - `status`: running/completed/failed/cancelled
   - `failed_instances` 是否为 0
3) 查看会话详情/错误摘要(如页面支持), 记录失败实例 id 与失败原因.
4) 到日志中心 `/history/logs`:
   - level: ERROR/WARNING
   - module: 先选 `sync`/`task`/对应业务模块, 再用 `session_id` 关键字检索 `context`.
5) 回到代码:
   - 入口 service/task: 看 log_with_context 的 `module/action` 与 `context` 填充是否足够.
   - 数据一致性: 对照 [[standards/backend/write-operation-boundary]] 判断 commit/rollback 预期是否正确.

### 4.3 后台任务排障 SOP(scheduler)

1) 先确认触发入口:
   - 手动触发: 对应 API/action endpoint 的返回是否为 "started".
   - 定时触发: 查看 scheduler 页面与 job 配置.
2) 按时间窗口在日志中心过滤 `module=scheduler`/`module=task`, 检索 `action/task_name`.
3) 如果出现重复执行/漏执行:
   - 检查是否存在异常导致事务回滚(look for `commit_failed`/`unexpected`).
   - 检查任务是否在 `app.app_context()` 内运行(见 [[standards/backend/task-and-scheduler]]).

## 5. 关键自查命令(本地/CI)

- 单测: `uv run pytest -m unit`
- Ruff: `./scripts/ci/ruff-report.sh style`
- Pyright: `./scripts/ci/pyright-report.sh`
- ESLint(改动 JS 时): `./scripts/ci/eslint-report.sh quick`
- 命名巡检: `./scripts/ci/refactor-naming.sh --dry-run`

## 6. 故障排查(常见问题)

### 6.1 只看到 "unknown" 或无提示

- 先看前端是否走了 async outcome helper(见 [[standards/ui/async-task-feedback-guidelines]]).
- 后端是否返回标准 envelope 与 `message_code`(见 [[standards/backend/error-message-schema-unification]]).

### 6.2 日志中心无记录

- 确认当前环境是否启用 DB log worker(非 testing 环境才会启动 worker).
- 检查 `LOG_FILE` 是否有写入(默认 `userdata/logs/app.log`).
