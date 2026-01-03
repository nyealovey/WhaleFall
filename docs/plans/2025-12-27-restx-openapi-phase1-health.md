# 004 Flask-RESTX/OpenAPI Phase 1 (Health) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将既有健康检查域（`/health/api/*`）迁移出一套 API v1（`/api/v1/health/*`）的 RestX Resource，并补齐最小 HTTP 契约测试（200/4xx），保持 JSON envelope/错误口径不变。

**Architecture:** 在 `app/api/v1/namespaces/health.py` 中新增/扩展 Resource；实现层复用 `app/routes/health.py` 的业务逻辑（Service/Repository），但不复用旧 Blueprint 路由。统一返回通过 `BaseResource.success()`；异常交由全局错误处理器/RestX `Api.handle_error` 输出统一错误封套。

**Tech Stack:** Flask, Flask-RESTX, pytest

---

### Task 1: Add contract tests for API v1 health

**Files:**
- Modify: `tests/unit/routes/test_api_v1_health_ping_contract.py`

**Step 1: Write the failing tests**

新增以下测试（预期当前 FAIL，因为端点未实现或未覆盖 4xx）：

```python
def test_api_v1_health_basic_returns_success_envelope(client):
    resp = client.get("/api/v1/health/basic")
    assert resp.status_code == 200

def test_api_v1_health_health_returns_success_envelope(client):
    resp = client.get("/api/v1/health/health")
    assert resp.status_code == 200

def test_api_v1_health_unknown_path_returns_error_envelope(client):
    resp = client.get("/api/v1/health/does-not-exist")
    assert resp.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `pytest -m unit tests/unit/routes/test_api_v1_health_ping_contract.py -v`

Expected: FAIL（`/api/v1/health/basic`/`/api/v1/health/health` 未注册；或 404 未覆盖断言）

---

### Task 2: Implement API v1 health endpoints

**Files:**
- Modify: `app/api/v1/namespaces/health.py`

**Step 1: Add resources**

在 `Namespace("health")` 下新增：

- `GET /basic`：返回与旧 `/health/api/basic` 对齐的数据结构与 message
- `GET /health`：返回与旧 `/health/api/health` 对齐的数据结构与 message

**Step 2: Use safe_call + unified envelope**

每个 handler 使用：

```python
return self.safe_call(
    lambda: self.success(data=payload, message="..."),
    module="health",
    action="...",
    public_error="...",
)
```

**Step 3: Run tests**

Run: `pytest -m unit tests/unit/routes/test_api_v1_health_ping_contract.py -v`

Expected: PASS

---

### Task 3: Update migration progress document (Phase 1)

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

**Step 1: Mark Phase 1 as started**

- 勾选/更新 Phase 1 的 checklist：
  - health 低风险域已迁移（以 `/api/v1/health/*` 作为新入口）
  - 最小 HTTP 契约测试已覆盖（200/4xx）

**Step 2: Update the health module rows**

在“健康检查模块”的表格中，将对应行标记为 `DONE`，并在备注中注明新路径（例如：`/api/v1/health/health`）。

---

### Task 4: Verify OpenAPI export

**Files:**
- No code changes

**Step 1: Export/check OpenAPI**

Run: `python3 scripts/dev/openapi/export_openapi.py --check`

Expected: exit code 0
