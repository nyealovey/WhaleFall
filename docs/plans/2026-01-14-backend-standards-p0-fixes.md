# Backend Standards P0 Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复后端标准审计中 P0 级问题：写路径 `parse_payload` 单入口、Routes fallback 可观测且不绕过 `safe_route_call`。

**Architecture:** 采用“薄 API / 强 Service”入口：API 只获取 raw payload（JSON dict / `request.form`），Service 入口统一 `parse_payload + validate_or_raise`；Routes 的降级在 `safe_route_call` 覆盖内完成，并通过 `log_fallback(..., fallback=true, fallback_reason=...)` 记录可观测性字段。

**Tech Stack:** Flask / Flask-RESTX / Pydantic schema(`app/schemas/**`) / `app/utils/request_payload.py` / `app/infra/route_safety.py`

---

### Task 1: 消除写路径双重 `parse_payload`（API + Service）

**Files:**
- Modify: `app/api/v1/namespaces/credentials.py`
- Modify: `app/api/v1/namespaces/tags.py`
- Modify: `app/api/v1/namespaces/users.py`
- Modify: `app/api/v1/namespaces/instances.py`

**Step 1: 静态定位双重解析点**

Run: `rg -n "\\bparse_payload\\b|_parse_payload\\(" app/api/v1/namespaces --glob='*.py'`
Expected: 能定位到写路径 `post/put` 中先 `_parse_payload()` 再进入 Service 的位置。

**Step 2: 改造 API：只获取 raw payload**

- 把 `_parse_payload()` 改为 `_get_raw_payload()`：只做 `request.get_json(silent=True)` / `request.form` 的形状获取，不调用 `parse_payload`。
- 写路径 `post/put`：传 raw payload 给写 Service（由 Service 执行 `parse_payload + validate_or_raise`）。

**Step 3: 运行最小验证**

Run: `python3 -m compileall app`
Expected: 0 errors

---

### Task 2: 对齐写 Service 入口签名（支持 raw payload）

**Files:**
- Modify: `app/services/auth/change_password_service.py`
- Modify: `app/services/auth/login_service.py`
- Modify: `app/services/credentials/credential_write_service.py`
- Modify: `app/services/tags/tag_write_service.py`
- Modify: `app/services/users/user_write_service.py`
- Modify: `app/services/instances/instance_write_service.py`

**Step 1: 调整 Service 入参类型**

- 将 `payload: ResourcePayload` / `payload: Mapping[...]` 改为 `payload: object | None`（与 `parse_payload(payload: object | None, ...)` 对齐）。
- Service 内调用 `parse_payload(payload, ...)`，避免 `payload or {}` 造成 MultiDict 空值时形状分支漂移。

**Step 2: 运行最小验证**

Run: `python3 -m compileall app`
Expected: 0 errors

---

### Task 3: Routes fallback 不绕过 `safe_route_call` + 必须可观测

**Files:**
- Modify: `app/routes/accounts/statistics.py`
- Modify: `app/routes/instances/statistics.py`
- Modify: `app/routes/users.py`

**Step 1: 将 fallback 移入 `safe_route_call` 覆盖范围**

- 路由函数 `return safe_route_call(_execute, ...)`，不在外层 `try/except SystemError`。
- 在 `_execute()` 内 `try/except SystemError`：触发 fallback 时调用 `app.infra.route_safety.log_fallback(...)` 并返回降级页面/默认值（保留原有 `flash(...)`）。

**Step 2: 运行最小验证**

Run: `python3 -m compileall app`
Expected: 0 errors

---

### Task 4: 收尾门禁（可选但推荐）

> 依赖环境允许时执行；本计划不包含自动 `git commit`（遵循仓库协作约定由人工决定）。

Run: `make typecheck`
Expected: 类型检查通过（若失败，至少应确认失败与本次改动相关再处理）。

