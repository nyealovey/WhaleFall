---
title: 日志设计审计（Wide Events / Canonical Log Lines）
status: draft
created: 2026-01-23
scope: app/**（后端）+ app/static/js/**（前端 console 日志，附带观察）
method: 静态代码审计 + 本地最小化运行验证（不含线上日志抽样）
---

# 日志设计审计（Wide Events / Canonical Log Lines）

本报告以 `logging-best-practices`（wide events / canonical log lines）为评价基线，对当前仓库的日志“设计与落地一致性”进行审计，并给出按优先级排序的整改建议。

## 0. 2026-01-23 修复状态（已落地整改）

以下 P0/P1 项已在仓库中落地（对应实现/门禁已加入）：

- request correlation：为每个请求注入 `request_id`（支持入站 `X-Request-ID`）并写入 contextvars；同时在响应头回传 `X-Request-ID`。
  - 实现：`app/infra/logging/request_middleware.py:49`
  - 注册顺序：在 CSRF 等早期 `before_request` 之前注册，确保“早期拒绝请求”也有 request_id。`app/__init__.py:109`
- wide event：请求完成时发射 `http_request_completed`（含 `status_code/outcome/duration_ms/route/endpoint` 等）。为避免日志中心被请求日志淹没，默认仅记录“慢请求或错误请求”，可通过配置切换为记录全部/仅错误/关闭。
  - 实现：`app/infra/logging/request_middleware.py`
  - 配置：`LOG_HTTP_REQUEST_COMPLETED_MODE`、`LOG_HTTP_REQUEST_COMPLETED_SLOW_MS`（见 `env.example`）
- 环境特征字段：为所有日志注入 `build_hash/region/runtime_instance_id`（Settings 缺省从 `.last_build_hash`/hostname 填充），并把 `environment` 扩展为“有 app_context 即写入”。
  - 实现：`app/settings.py`、`app/utils/structlog_config.py:185`
  - env.example：`env.example`
- stdout/stderr renderer：移除“双 renderer”链路，非 TTY 环境输出 JSON 行，避免“JSON string 套娃”。
  - 实现：`app/utils/structlog_config.py:216`
- 单测门禁：增加 request_id 注入、wide event 存在性、错误封套包含 request_id 的单测。
  - `tests/unit/utils/test_request_logging_wide_events.py:1`

## 0. 审计结论（Executive Summary）

- 当前系统已经具备“结构化日志 + 统一落库（UnifiedLog）+ 异步批量写入 + 脱敏 + 最小字段门禁测试”的完整骨架，属于很好的基础设施起点。
- 但与 wide events 的关键目标（“每个请求/服务一次、上下文丰富、可关联、可统计”）相比，审计时发现 3 个会直接影响排障与分析的 P0 问题（已整改，见上节）：
  - `request_id` / `user_id` 的 contextvars **从未被 set**，导致“链路关联字段”在绝大多数日志中为空（与运维/标准文档口径不一致）。
  - `g.url/method/ip/user_agent/host` 等 request 维度 **从未被写入**，导致日志中心无法按请求维度回溯。
  - structlog processor 链同时包含 `ConsoleRenderer` 与 `JSONRenderer`，会把“控制台字符串”再 JSON dump 成“JSON string 字面量”，使 stdout/stderr 日志不再是 JSON object（也降低可读性）。
- 审计时也缺少“每请求一次”的完成态日志（wide event）（已整改）：`safe_route_call` 只在异常时记录，成功请求往往没有稳定可查询的行为记录与性能维度（status/duration）。

## 1. 现状架构概览（你现在的日志系统在做什么）

### 1.1 日志落库（UnifiedLog）

- 统一表：`app/models/unified_log.py`（字段：`timestamp/level/module/message/traceback/context`）。`app/models/unified_log.py:27`、`app/models/unified_log.py:39`
- 写入链路：structlog -> `DatabaseLogHandler` -> `LogQueueWorker` 批量写 DB。`app/utils/structlog_config.py:79`、`app/utils/logging/handlers.py:100`、`app/infra/logging/queue_worker.py:49`
- 最小字段门禁：`tests/unit/utils/test_structlog_log_entry_schema.py:1`（验证 `_build_log_entry` 的稳定输出）。

### 1.2 结构化字段注入（processors + handler）

- structlog processors 注入：timestamp / level / request context / user context / global context / handler 等。`app/utils/structlog_config.py:79`
- handler 负责把 structlog 的事件字典标准化成 UnifiedLog 的 payload，并统一脱敏。`app/utils/logging/handlers.py:150`、`app/utils/sensitive_data.py:28`

### 1.3 路由层异常口径（RouteSafety + Error Envelope）

- 视图层复用日志字段与异常捕获：`log_with_context` / `safe_route_call`。`app/infra/route_safety.py:36`、`app/infra/route_safety.py:109`
- 全局错误处理与增强错误载荷：`enhanced_error_handler` + `ErrorContext`。`app/utils/structlog_config.py:478`、`app/utils/logging/error_adapter.py:32`

## 2. 与 Wide Events 最佳实践对照（差距在哪里）

> Wide events 的核心：**每个请求/服务一次**，把该请求最关键的维度聚合在一条结构化事件里（method/path/status/duration/user/request_id/业务关键字段），并可跨服务用 `request_id` 关联。

### 2.1 Wide events（CRITICAL）

审计时现状（整改前）：

- 代码里没有 `after_request`/`teardown_request` 的“完成态日志”埋点；只有 `_register_protocol_detector` 这种协议检测钩子。`app/__init__.py:208`
- `safe_route_call` 仅在异常路径记录 warning/error（成功路径不记录）。`app/infra/route_safety.py:149`

影响：

- 无法稳定回答：某段时间某 endpoint 的请求量、错误率、P95 延迟、某用户在某天做了哪些动作（成功的动作尤其缺失）。
- 只能靠散落日志“碰运气”拼上下文，且字段不完整（见 P0）。

建议（目标态）：

- 引入一个 request middleware：`before_request` 采集/生成维度，`after_request` emit `http_request_completed` wide event（可配置为全量/仅慢或错/仅错/关闭）。
- handler/业务代码只负责“补充业务维度”，而不是承担 request 基础字段与发射逻辑（符合 skill 的 “Middleware Pattern”）。

已整改：
- 通过 request middleware 在 `after_request` 统一发射 `http_request_completed`。`app/infra/logging/request_middleware.py:78`

### 2.2 高基数 & 高维度字段（CRITICAL）

优点：

- UnifiedLog 的 `context` 会吸收大量非系统字段，天然支持“高维度”（many fields per event）。`app/utils/logging/handlers.py:232`
- 有敏感字段脱敏入口且覆盖常见 token/header。`app/utils/logging/handlers.py:21`、`app/utils/sensitive_data.py:28`

关键缺口（P0）：

- `request_id_var` / `user_id_var` 仅定义与读取，**没有任何 set 的调用点**，导致 request correlation 字段长期为 `None`。定义：`app/utils/logging/context_vars.py:5`；读取：`app/utils/structlog_config.py:156`、`app/utils/logging/handlers.py:252`、`app/utils/logging/error_adapter.py:53`

### 2.3 业务上下文（CRITICAL）

优点：

- `log_with_context` 强制 `module/action`，是很好的“可检索口径”。`app/infra/route_safety.py:36`
- 多处任务/同步场景会写入 `run_id/session_id/instance_id` 等域字段（示例：`app/services/accounts_sync/accounts_sync_actions_service.py:95`）。

待加强：

- 成功路径缺乏统一“动作完成”事件，导致业务链路只能在失败时被看见（与 wide events 背道而驰）。
- 错误字段命名存在分叉：如 `error`/`error_message`/`exception` 混用（会降低可查询性；建议统一在 wide event 和错误事件中使用 `error.type`、`error.message` 或 `error_type`/`error_message` 一致口径）。

### 2.4 环境特征字段（CRITICAL）

审计时现状（整改前）：

- global context 注入 `app_name/app_version`，并在 request context 下尝试注入 `environment/host`。`app/utils/structlog_config.py:185`

缺口（已整改）：

- 缺少 commit hash/build id、region、runtime instance id 等“部署维度”，难以把问题与特定发布/节点/机房关联（wide events 的关键维度之一）。
- `environment` 仅在 `has_request_context()` 时写入，后台任务/worker 日志缺少同等环境维度。`app/utils/structlog_config.py:208`

已整改：
- `build_hash/region/runtime_instance_id/environment` 在 app_context 下统一写入 global context。`app/utils/structlog_config.py:185`

### 2.5 结构 & 一致性（HIGH）

关键问题（P0）：

- processors 同时包含 `ConsoleRenderer` 与 `JSONRenderer`：stdout/stderr 的最终 message 不是 JSON object，而是“JSON string（里面包着 console 渲染的字符串）”。`app/utils/structlog_config.py:79`

本地复现（最小化验证）：

```bash
./.venv/bin/python -c "import logging; logging.basicConfig(level=logging.INFO); from app.utils.structlog_config import get_logger; logger=get_logger('demo'); logger.info('hello', module='demo', action='test', foo=1)"
```

输出形态示例（注意整行 message 外层的引号，且 Unicode 被转义）：

```
INFO:demo:"2026-01-23T05:59:29.779878Z [info     ] hello [demo] action=test app_name=\u9cb8\u843d app_version=1.4.0 foo=1 module=demo"
```

这会让：

- 采集系统若按“JSON 行日志”解析，会得到字符串而不是对象；
- 人读也更困难（双重渲染）。

建议：

- renderer 二选一：TTY 用 `ConsoleRenderer`，非 TTY 用 `JSONRenderer`（或反之）；不要同时存在两种 renderer。

## 3. 关键发现清单（按优先级）

### P0（必须优先）

1) Request correlation 不生效：`request_id_var/user_id_var` 从未 set

- 证据：`app/utils/logging/context_vars.py:5` 定义后，全仓库无 `.set(...)` 调用（静态检索）。
- 影响：日志中心/错误封套无法稳定按 `request_id` 关联；运维 SOP 与标准文档中“按 request_id 检索”不可落地。`docs/Obsidian/operations/observability-ops.md:73`

2) Request 维度字段采集缺失：`g.url/method/ip/user_agent` 未写入

- 证据：handler 读取：`app/utils/logging/handlers.py:249`；全仓库无 `g.url = ...` 等赋值（静态检索）。
- 影响：无法按 endpoint/方法/ip 等定位问题；wide event 也无基础数据可填充。

3) stdout/stderr 日志渲染链错误：ConsoleRenderer + JSONRenderer 双 renderer

- 证据：`app/utils/structlog_config.py:79`
- 影响：外部日志管道很难做结构化解析；降低可读性。

### P1（高优先）

4) 缺少“每请求一次”的完成态 wide event

- 证据：无 `after_request/teardown_request` 发射日志。`app/__init__.py:219` 仅协议检测。
- 影响：成功请求不可见；无法做请求级统计与回溯。

### P2（中优先）

5) 环境/部署维度不足（build hash/region/runtime_instance_id）

- 证据：仅 `app_name/app_version/environment/host`。`app/utils/structlog_config.py:185`
- 影响：定位“某次发布引入的问题”“某节点异常”时缺少维度。

6) 多套 logging 并存且落库不一致（structlog vs stdlib logging）

- 证据：`app/infra/logging/queue_worker.py:26`、`app/settings.py:26` 使用 stdlib logging；这些日志默认不会进入 UnifiedLog（除非额外桥接）。
- 影响：关键基础设施错误（如 worker 写库失败/队列满）可能只在文件/控制台出现，不在日志中心出现。

## 4. 建议的 Wide Event Schema（落库/分析友好）

建议把“每个请求一条”的事件命名为 `http_request_completed`，字段尽量稳定且可聚合：

```json
{
  "event": "http_request_completed",
  "module": "http",
  "action": "GET /api/v1/...",
  "request_id": "req_...",
  "actor_id": 123,
  "user_id": 123,
  "http": {
    "method": "GET",
    "path": "/api/v1/history_logs",
    "status_code": 200,
    "duration_ms": 37,
    "ip": "x.x.x.x",
    "user_agent": "..."
  },
  "outcome": "success|error",
  "error_type": "...",
  "error_message": "...",
  "env": {
    "environment": "production",
    "app_version": "1.4.0",
    "build_hash": "...",
    "region": "...",
    "runtime_instance_id": "..."
  }
}
```

注意：

- `module` 列仍可用于“粗粒度过滤”（建议 `http`）。
- 业务侧补充的维度（如 `instance_id/session_id/run_id`）应该放到同一条 wide event 的 `context` 或顶层字段中，保证可检索性。
- 严禁把请求 body / Authorization / Cookie 原样写入（只记录白名单字段或脱敏后摘要）。

## 5. 建议落地步骤（最小风险路径）

1) 修正 structlog renderer（二选一），确保 stdout/stderr 日志为可解析 JSON object 或清晰的人类可读格式。`app/utils/structlog_config.py:79`
2) 引入 request middleware：
   - `before_request`：生成 `request_id`，写入 `request_id_var.set(...)`，并把 method/path/ip/ua 写入 `g`（或直接写入 structlog contextvars）
   - `after_request`：发射 `http_request_completed` wide event（填 `status_code/duration_ms/outcome`）
3) 让 `user_id_var` 在可用时写入（例如认证后从 `current_user.id` 设置；匿名则 None）。
4) 补齐环境维度（build hash/region/runtime_instance_id），优先从 env var 获取（也可读 `.last_build_hash` 作为 fallback）。
5) 增补单测：
   - request middleware 能写入 request_id，并出现在 handler 落库 payload 的 `context.request_id`（或你的最终字段口径里）。

---

如你希望我直接落地整改（P0+P1），我可以按上面的步骤提交一个最小 PR：先修 renderer + request middleware + 单测，保证行为可验证，再讨论字段/表结构的进一步增强（如 request_id 列索引化）。
