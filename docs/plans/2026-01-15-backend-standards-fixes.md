# Backend Standards Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按 `docs/reports/2026-01-15-backend-standards-audit-report.md` 的 `## 7. 修复优先级建议` 修复 MUST 级违规点（fallback 可观测性 + silent fallback），并补齐 P1 标准缺口（`parse_payload` 单次门禁、`category/severity` 单一真源引用、action-endpoint scope 澄清）。

**Architecture:** 优先做最小侵入修改：不改变主业务语义/事务边界，只在“异常→继续执行/兜底值”分支补齐 `fallback=true/fallback_reason`；对 silent fallback 增加低噪音结构化日志；对 `parse_payload` 通过 request-scope marker 增加可验证门禁，并收敛双重解析到单入口。

**Tech Stack:** Flask, SQLAlchemy, structlog, Ruff, Pyright, pytest

### Task 1: P0 - fallback 可观测性字段补齐 + 消除 silent fallback

**Files:**
- Modify: `app/__init__.py`
- Modify: `app/infra/logging/queue_worker.py`
- Modify: `app/services/capacity/instance_capacity_sync_actions_service.py`
- Modify: `app/infra/database_batch_manager.py`
- Modify: `app/models/account_permission.py`
- Modify: `app/services/database_sync/table_size_adapters/oracle_adapter.py`

**Step 1: 为“异常→继续执行/兜底值”分支补齐字段**
- 对齐 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:46`：至少写入 `fallback=true` 与 `fallback_reason="<stable_code>"`，并追加关键维度（例如 `instance_id`/`action`/`component`）。
- 优先使用 `app/infra/route_safety.py::log_fallback(...)`；若存在循环依赖风险，则在现有 logger 调用中补齐 `fallback/fallback_reason`。

**Step 2: 消除 silent fallback**
- 对齐 `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:50`：`except Exception: return default` 必须记录低噪音结构化日志（避免包含敏感信息）。
- 规则：日志中仅记录 `fallback_reason=exc.__class__.__name__` 与必要维度，避免输出凭据/SQL。

**Step 3: 静态验证**
- Run: `uv run ruff check app`
- Run: `uv run pyright app`

### Task 2: P1 - 标准澄清与单一真源引用（category/severity + action-endpoint scope）

**Files:**
- Modify: `docs/Obsidian/standards/backend/layer/api-layer-standards.md`
- Modify: `docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md`

**Step 1: `category/severity` 的枚举来源声明**
- 在 API 标准中明确：`category`/`severity` 的取值必须来自 `app/core/constants/system_constants.py` 的 `ErrorCategory/ErrorSeverity`（单一真源），禁止业务侧“凭感觉”造字符串。

**Step 2: 澄清 `(Response, status_code)` 禁止项的 scope**
- 在 `action-endpoint-failure-semantics.md` 中明确该约束是否仅针对 Flask-RESTX `Resource` 方法；对 blueprint routes（如 `openapi.json`）增加例外说明与理由，避免误读与评审漂移。

### Task 3: P1 - `parse_payload` 单次门禁（可验证）+ 收敛双重解析

**Files:**
- Modify: `app/utils/request_payload.py`
- Modify: `app/views/form_handlers/account_classification_form_handler.py`
- Modify: `app/views/form_handlers/account_classification_rule_form_handler.py`
- Modify: `app/services/accounts/account_classifications_write_service.py`
- Modify: `tests/unit/types/test_request_payload.py`

**Step 1: 增加 request-scope marker**
- 在 `parse_payload(...)` 内（仅在 request context 下）写入 marker，二次调用明确策略（抛 `RuntimeError` 或写结构化 warning）。

**Step 2: 收敛双重解析**
- 将 view form handler 的 `parse_payload(...)` 去除，改为把 raw payload 直接交给 service（保证链路内只 parse 一次）。
- 对需要 MultiDict checkbox 语义的写路径（如 `is_active`）把 `boolean_fields_default_false` 的处理移动到 service 的唯一入口。

**Step 3: 单元测试**
- 为 request context 下 “二次调用” 添加 unit test（确保门禁可验证且 request 间隔离）。
- Run: `uv run pytest -m unit tests/unit/types/test_request_payload.py -q`

**Step 4: 静态验证**
- Run: `uv run ruff check app tests/unit/types/test_request_payload.py`
- Run: `uv run pyright app`

