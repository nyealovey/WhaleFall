---
title: 结构化日志最小字段 Schema
aliases:
  - structured-logging-minimum-fields
tags:
  - standards
  - standards/backend
status: active
enforcement: guide
created: 2026-01-13
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/utils/structlog_config.py`, `app/utils/logging/handlers.py`, `app/models/unified_log.py`"
related:
  - "[[standards/backend/standard/sensitive-data-handling]]"
  - "[[standards/backend/gate/layer/tasks-layer]]"
  - "[[standards/backend/gate/layer/services-layer]]"
  - "[[standards/backend/guide/structured-logging-context-fields]]"
---

# 结构化日志最小字段 Schema

## 1. 目的

- 固化“写入统一日志中心(UnifiedLog)时”的最小字段集合，避免口径依赖人脑 review。
- 为门禁提供可验证的判据：只要 `_build_log_entry(...)` 输出结构稳定，即可认为“最小字段”满足。

## 2. 适用范围

- 所有通过 structlog -> handler -> worker 写入 `UnifiedLog` 的日志事件。
- 不约束“控制台打印渲染”的字段，但其最终落库必须满足下述最小字段。

## 3. 最小字段定义（落库口径）

单条 `UnifiedLog` 记录的最小字段集合如下（以 `app/models/unified_log.py::LogEntryParams` 为准）：

- `timestamp`: UTC 时间戳（timezone-aware `datetime`）
- `level`: `LogLevel`（`DEBUG` 日志默认不落库）
- `module`: 模块/领域字符串（用于检索与聚合统计）
- `message`: 可读的事件描述（来自 structlog 的 `event`）
- `traceback`: 可选堆栈字符串（仅 error/critical 常见）
- `context`: JSON 上下文字典（包含非系统字段，且必须经过脱敏）

单一真源：

- 结构化事件转换为落库字段：`app/utils/logging/handlers.py::_build_log_entry`
- 脱敏规则：[[standards/backend/standard/sensitive-data-handling|敏感数据处理]]

## 4. 规则（MUST/SHOULD）

- MUST: 落库日志必须满足“最小字段定义”的字段存在性与类型预期（见上节）。
- MUST: `context` 在写入前必须经过脱敏（由 handler 统一调用 `scrub_sensitive_fields(...)`）。
- SHOULD: 关键业务路径（写操作、任务、对外 action）在 `context` 中提供可检索维度，例如 `action`/`task`/`instance_id`/`job_id` 等。

## 5. 门禁/检查方式

- 单元测试（最小字段 schema 门禁）：`uv run pytest -m unit`
  - 覆盖 `_build_log_entry(...)` 对不同输入形态的稳定输出（含缺省 module、非法 level、debug drop）。

> [!note]
> 本标准的“可验证性”依赖于 `_build_log_entry(...)` 的输出结构稳定；如需调整字段，请先更新标准与对应单测，再进行实现变更。
