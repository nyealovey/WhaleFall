# Backend Standards Audit P1 Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按 `docs/reports/2026-01-13-backend-standards-audit-report.md` 的 P1 修复项收敛“对外错误诊断字段口径”和“回退/降级可观测性”，并把“业务关键路径日志”落为可审计 checklist。

**Architecture:** 通过标准文档给出明确边界（禁止对外暴露 `error_code`），并在代码层补齐统一 helper（`log_fallback`）与示例落点（SQLServer 权限查询回退分支）。最后补齐 services-layer 的“关键路径判定 checklist”以便评审与门禁落地。

**Tech Stack:** Python, structlog, pytest(`-m unit`).

---

### Task 1: 收敛 `error_code` 对外暴露边界（文档 + 代码）

**Files:**
- Modify: `docs/Obsidian/standards/backend/error-message-schema-unification.md:30`
- Modify: `docs/Obsidian/standards/backend/layer/api-layer-standards.md:128`
- Modify: `app/api/v1/namespaces/instances_connections.py:140`
- Test: `tests/unit/routes/test_api_v1_connections_contract.py`

**Step 1: 更新标准，明确 `error_code` 不得出现在对外 error envelope（包含 `extra`）**

Action:
- 在 `error-message-schema-unification.md` 明确“对外一律不输出 `error_code`（即使放 `extra` 也不允许）”。
- 在 `api-layer-standards.md` 的 `extra` 说明中补充禁止项与推荐替代（`error_id` / `diagnostic` 字段策略）。

**Step 2: 移除 API v1 连接测试错误响应里的 `extra.error_code`**

Action:
- 修改 `app/api/v1/namespaces/instances_connections.py`，保留 `connection_error_id` 与 `details`（如有），删除 `error_code` 输出。

**Step 3: 跑 unit 回归**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_connections_contract.py -v`
Expected: PASS

---

### Task 2: 增加回退/降级结构化日志 helper（`fallback=true` + `fallback_reason`）

**Files:**
- Modify: `app/infra/route_safety.py:1`
- Modify: `docs/Obsidian/standards/backend/resilience-and-fallback-standards.md:35`
- Test: `tests/unit/infra/test_log_fallback_helper.py`

**Step 1: 写 failing test（helper 必须写入 fallback 字段）**

```python
import pytest

from app.infra import route_safety


@pytest.mark.unit
def test_log_fallback_always_sets_fallback_fields(monkeypatch) -> None:
    captured = {}

    class _Logger:
        def warning(self, event, **kwargs):  # type: ignore[no-untyped-def]
            captured["event"] = event
            captured["kwargs"] = kwargs

    monkeypatch.setattr(route_safety, "get_logger", lambda _name: _Logger())
    route_safety.log_fallback(
        "warning",
        "fallback_event",
        module="test",
        action="action",
        fallback_reason="reason",
    )
    assert captured["kwargs"]["fallback"] is True
    assert captured["kwargs"]["fallback_reason"] == "reason"
```

**Step 2: 实现 helper**

Action:
- 在 `app/infra/route_safety.py` 增加 `log_fallback(...)`，内部复用 `log_with_context(...)`，强制写入 `fallback=true` 与 `fallback_reason`。

**Step 3: 更新标准引用 helper**

Action:
- 在 `resilience-and-fallback-standards.md` 的可观测性章节补充推荐 helper（并强调字段名固定）。

**Step 4: 跑 unit**

Run: `uv run pytest -m unit tests/unit/infra/test_log_fallback_helper.py -v`
Expected: PASS

---

### Task 3: 让现有 fallback 分支落到统一 helper（SQLServer 权限查询回退）

**Files:**
- Modify: `app/services/accounts_sync/adapters/sqlserver_adapter.py:640`
- Test: `tests/unit/services/test_sqlserver_adapter_permissions.py`

**Step 1: 将 fallback 事件补齐 `fallback=true` 与 `fallback_reason`**

Action:
- 把 `sqlserver_batch_permissions_sid_empty_fallback` 的日志改为使用 `log_fallback(...)`。
- 对 “SID 不可用直接回退用户名查询” 分支补一条 `log_fallback(...)`（避免 silent fallback）。

**Step 2: 跑相关 unit**

Run: `uv run pytest -m unit tests/unit/services/test_sqlserver_adapter_permissions.py -v`
Expected: PASS

---

### Task 4: 把“业务关键路径日志”落为可审计 checklist

**Files:**
- Modify: `docs/Obsidian/standards/backend/layer/services-layer-standards.md:160`

**Step 1: 增加 checklist**

Action:
- 在 services-layer 的日志规范章节追加“满足任一条件即必须打点”的 checklist（写操作/外部依赖交互/对外 action/存在 fallback 分支等）。
- 引用 `resilience-and-fallback-standards.md` 的 `fallback=true/fallback_reason` 要求，减少实现分裂。

---

### Task 5: 回归验证

**Files:**
- (none)

**Step 1: 跑 unit**

Run: `uv run pytest -m unit`
Expected: PASS

