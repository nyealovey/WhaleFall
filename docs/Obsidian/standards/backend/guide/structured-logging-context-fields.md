---
title: 结构化日志上下文字段规范(Logging Context Fields)
aliases:
  - structured-logging-context-fields
  - logging-context-fields
tags:
  - standards
  - standards/backend
status: active
enforcement: guide
created: 2026-01-13
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/utils/structlog_config.py`, `app/infra/route_safety.py`, `app/utils/logging/handlers.py` 相关日志字段口径"
related:
  - "[[standards/backend/guide/structured-logging-minimum-fields]]"
  - "[[standards/backend/standard/sensitive-data-handling]]"
  - "[[standards/backend/gate/layer/tasks-layer]]"
  - "[[standards/backend/gate/layer/services-layer]]"
---

# 结构化日志上下文字段规范(Logging Context Fields)

## 1. 目的

- 在“最小字段 schema”（见 [[standards/backend/guide/structured-logging-minimum-fields]]）之上，补齐可检索的业务维度口径，减少日志字段依赖人脑随意拼装。
- 降低排障成本：同类操作必须能用同一组键检索（例如 `action`、`instance_id`、`job_id`）。

## 2. 适用范围

- 所有写入 unified logs 的结构化日志（不区分 API/Routes/Tasks/Services）。

## 3. 基本约束（MUST）

### 3.1 命名与类型

- MUST: 上下文字段 key 使用 `snake_case`。
- MUST: 上下文字段 value 必须是 JSON 可序列化类型（`str/int/bool/float/None/list/dict`），禁止把 ORM/model/异常对象直接塞进 context（必要时提取 `id`/`name`/`error_type` 等标量）。

### 3.2 敏感数据

- MUST: 上下文字段必须遵循 [[standards/backend/standard/sensitive-data-handling]]，禁止把口令/令牌/连接串等敏感信息写入日志。

## 4. 推荐维度（SHOULD）

> [!note]
> 以下维度用于“可检索性”，不是业务协议；允许按场景选取，但同一类操作应保持一致。

### 4.1 请求/动作维度

- SHOULD: `action`：当前操作名称（建议与 handler/service 方法名或 endpoint 动作一致）。
  - Web 请求优先通过 `safe_route_call`/`log_with_context` 自动写入。
- SHOULD: `actor_id`：操作人 ID（如存在）。
- SHOULD: `request_id`：请求链路 id（由 handler 自动注入；业务代码不应手写）。

### 4.2 资源定位维度

- SHOULD: `instance_id` / `database_id` / `user_id` / `credential_id`：与当前操作强相关的资源标识。
- SHOULD: `target_*`：当存在“操作者/被操作对象”二者时，使用 `target_user_id`、`target_instance_id` 等区分。

### 4.3 任务/调度维度

- SHOULD: `task`：任务名称（函数名或 job id）。
- SHOULD: `job_id`：调度器 job id（如存在）。
- SHOULD: `run_id`：一次执行的唯一标识（如有批处理/长任务可用）。

### 4.4 错误维度

- SHOULD: `error_type`：异常类型名（`exc.__class__.__name__`）。
- SHOULD: `error_message`：异常消息摘要（注意脱敏）。
- SHOULD: `recoverable`：是否可重试（当对外返回 error envelope 时与错误口径保持一致）。

### 4.5 环境/部署维度

> [!note]
> 该类字段用于把问题与“发布版本/节点/机房”关联，通常由日志基础设施自动注入，业务代码不应手写。

- SHOULD: `environment`：环境名（development/staging/production 等）。
- SHOULD: `app_name` / `app_version`：应用标识与版本。
- SHOULD: `build_hash`：构建/提交 hash（用于关联某次发布）。
- SHOULD: `region`：部署区域/机房/region。
- SHOULD: `runtime_instance_id`：运行时实例标识（如 hostname / k8s pod name），避免与业务域的 `instance_id` 冲突。

## 5. 门禁/检查方式（建议）

- 单元测试：优先用“入口函数门禁”固化字段结构，而不是对全量调用点做 fragile 的 grep：
  - `_build_log_entry(...)` 的最小字段结构见 `tests/unit/utils/test_structlog_log_entry_schema.py`。

## 6. 变更历史

- 2026-01-13：新增标准，补齐结构化日志 `context` 字段命名与推荐维度口径。
