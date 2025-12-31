# 004 Flask-RESTX/OpenAPI Phase 2 (Credentials Write) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Credentials 域的写操作 API（create/update/delete）迁移到 RestX API v1（`/api/v1/credentials/**`），保持既有 JSON envelope 与错误口径，并保持 CSRF 约束不降级。

**Architecture:** 在 `app/api/v1/namespaces/credentials.py` 复用既有 `CredentialWriteService`，统一通过 `BaseResource.safe_call()` 执行业务并提交事务；鉴权/权限使用 API v1 专用装饰器（JSON-only），写操作额外叠加 `require_csrf`。

**Tech Stack:** Flask, Flask-RESTX, Flask-WTF(CSRF), pytest

---

## API v1 路径映射（Credentials Write）

- 旧：`POST /credentials/api/credentials` → 新：`POST /api/v1/credentials`
- 旧：`PUT /credentials/api/credentials/<int:credential_id>` → 新：`PUT /api/v1/credentials/<int:credential_id>`
- 旧：`POST /credentials/api/credentials/<int:credential_id>/delete` → 新：`POST /api/v1/credentials/<int:credential_id>/delete`

> 说明：本阶段不强制把 `POST .../delete` 改为 `DELETE`（遵循迁移方案的“非目标”约束）。

---

### Task 1: Extend API v1 Credentials contract tests (write)

**Files:**
- Modify: `tests/unit/routes/test_api_v1_credentials_contract.py`

**Step 1: Write the failing tests**

- `test_api_v1_credentials_create_contract`
- `test_api_v1_credentials_update_contract`
- `test_api_v1_credentials_delete_contract`

测试要点：
- 使用同一个 `client` 先请求 `GET /auth/api/csrf-token` 获取 token，并在后续写请求中通过 `X-CSRFToken` 头传递。
- 校验状态码（create=201, update=200, delete=200）与最小 envelope 字段（success/error/message/timestamp/data）。

**Step 2: Run tests to verify they fail**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_credentials_contract.py -v`

Expected: FAIL（404 或方法未实现）

---

### Task 2: Implement Credentials write endpoints in RestX namespace

**Files:**
- Modify: `app/api/v1/namespaces/credentials.py`

**Step 1: Implement POST /api/v1/credentials**

- 装饰器：`api_login_required` + `api_permission_required("create")` + `require_csrf`
- 解析 JSON body（`request.get_json(silent=True) or {}`）
- 调用：`CredentialWriteService().create(payload, operator_id=current_user.id)`
- 返回：`data={"credential": credential.to_dict()}`, `message=SuccessMessages.DATA_SAVED`, `status=201`

**Step 2: Implement PUT /api/v1/credentials/<id>**

- 装饰器：`api_login_required` + `api_permission_required("update")` + `require_csrf`
- 调用：`CredentialWriteService().update(credential_id, payload, operator_id=current_user.id)`
- 返回：`message=SuccessMessages.DATA_UPDATED`

**Step 3: Implement POST /api/v1/credentials/<id>/delete**

- 装饰器：`api_login_required` + `api_permission_required("delete")` + `require_csrf`
- 调用：`CredentialWriteService().delete(credential_id, operator_id=current_user.id)`
- 返回：`data={"credential_id": credential_id}`, `message=SuccessMessages.DATA_DELETED`

**Step 4: Run tests**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_credentials_contract.py -v`

Expected: PASS

---

### Task 3: Update progress doc + verification gates

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

**Step 1: Mark credentials write endpoints as DONE**

- 在 “凭据管理模块” 中将以下三条标记为 DONE，并补充备注的新入口：
  - `POST /credentials/api/credentials`
  - `PUT /credentials/api/credentials/<int:credential_id>`
  - `POST /credentials/api/credentials/<int:credential_id>/delete`

**Step 2: Run unit tests**

Run: `uv run pytest -m unit`

Expected: 0 failed

**Step 3: Verify OpenAPI export**

Run: `uv run python scripts/dev/openapi/export_openapi.py --check`

Expected: exit 0

**Step 4: Ensure progress doc endpoint set not drifted**

Note: 迁移期 API routes inventory tooling 已在 020 迁移期代码清理中移除；以 OpenAPI export 与 progress 文档人工核对为准。
