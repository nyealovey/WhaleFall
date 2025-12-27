# 004 Flask-RESTX/OpenAPI Phase 2 (Core Domains) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将核心业务域（instances/tags/credentials/accounts）的既有 JSON API（`*/api/*`）迁移到新的 RestX API v1（`/api/v1/**`），采用 clean/REST-ish 路径（去掉旧路径中的中间 `/api` 段），并补齐最小 HTTP 契约测试与 OpenAPI 可见性校验。

**Architecture:** 新增/扩展 `app/api/v1/namespaces/*` 的 Resource 作为新入口；业务逻辑复用现有 `app/services/**` 与 `app/repositories/**`，路由层统一通过 `BaseResource.safe_call()` + `BaseResource.success()` 输出 envelope。鉴权/权限在 API v1 使用专用装饰器（不走 redirect），保证返回统一错误封套。

**Tech Stack:** Flask, Flask-RESTX, pytest

---

## API v1 路径映射（Phase 2 首批只读）

> 口径：保持 payload/envelope 与旧接口一致；仅调整新入口路径（clean/REST-ish）。

### Instances
- 旧：`GET /instances/api/instances` → 新：`GET /api/v1/instances`
- 旧：`GET /instances/api/<int:instance_id>` → 新：`GET /api/v1/instances/<int:instance_id>`

### Tags
- 旧：`GET /tags/api/list` → 新：`GET /api/v1/tags`
- 旧：`GET /tags/api/tags` → 新：`GET /api/v1/tags/options`
- 旧：`GET /tags/api/categories` → 新：`GET /api/v1/tags/categories`
- 旧：`GET /tags/api/<int:tag_id>` → 新：`GET /api/v1/tags/<int:tag_id>`

### Credentials
- 旧：`GET /credentials/api/credentials` → 新：`GET /api/v1/credentials`
- 旧：`GET /credentials/api/credentials/<int:credential_id>` → 新：`GET /api/v1/credentials/<int:credential_id>`

### Accounts (Ledgers)
- 旧：`GET /accounts/api/ledgers` → 新：`GET /api/v1/accounts/ledgers`
- 旧：`GET /accounts/api/ledgers/<int:account_id>/permissions` → 新：`GET /api/v1/accounts/ledgers/<int:account_id>/permissions`

---

### Task 1: Add API v1 auth/permission decorators (JSON-only)

**Files:**
- Create: `app/api/v1/resources/decorators.py`

**Step 1: Write the failing test**

（可选）若要覆盖 401 行为：在后续各域的 contract test 中新增未登录请求断言 401（见 Task 3/5/7/9）。

**Step 2: Implement minimal decorators**

实现：
- `api_login_required`：未登录直接抛 `AuthenticationError(..., message_key="AUTHENTICATION_REQUIRED")`
- `api_permission_required(permission: str)`：权限不足抛 `AuthorizationError(..., message_key="PERMISSION_REQUIRED")`

**Step 3: Run one contract test**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v`

Expected: PASS（401 case 能得到统一错误封套）

---

### Task 2: Implement Instances namespace (read-only)

**Files:**
- Create: `app/api/v1/namespaces/instances.py`
- Modify: `app/api/v1/__init__.py`

**Step 1: Write the failing tests**

见 Task 3。

**Step 2: Add resources**

- `GET /instances`：复用 `InstanceListService().list_instances(...)`，保持返回 data 结构（items/total/page/pages/limit）与旧端点一致。
- `GET /instances/<id>`：复用 `InstanceDetailReadService().get_active_instance(id)`，保持返回 `{"instance": instance.to_dict()}`。

**Step 3: Run tests**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v`

Expected: PASS

---

### Task 3: Add Instances contract tests (API v1)

**Files:**
- Create: `tests/unit/routes/test_api_v1_instances_contract.py`

**Step 1: Write the failing test**

```python
def test_api_v1_instances_list_contract():
    ...
    resp = client.get("/api/v1/instances")
    assert resp.status_code == 200
```

**Step 2: Run it to verify it fails**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v`

Expected: FAIL（404 或未实现）

---

### Task 4: Implement Tags namespace (read-only)

**Files:**
- Create: `app/api/v1/namespaces/tags.py`
- Modify: `app/api/v1/__init__.py`

**Step 1: Add resources**

- `GET /tags`（列表）
- `GET /tags/options`（下拉选项）
- `GET /tags/categories`（分类列表）
- `GET /tags/<id>`（详情）

**Step 2: Run tests**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_tags_contract.py -v`

Expected: PASS

---

### Task 5: Add Tags contract tests (API v1)

**Files:**
- Create: `tests/unit/routes/test_api_v1_tags_contract.py`

---

### Task 6: Implement Credentials namespace (read-only)

**Files:**
- Create: `app/api/v1/namespaces/credentials.py`
- Modify: `app/api/v1/__init__.py`

---

### Task 7: Add Credentials contract tests (API v1)

**Files:**
- Create: `tests/unit/routes/test_api_v1_credentials_contract.py`

---

### Task 8: Implement Accounts namespace (Ledgers, read-only)

**Files:**
- Create: `app/api/v1/namespaces/accounts.py`
- Modify: `app/api/v1/__init__.py`

---

### Task 9: Add Accounts Ledgers contract tests (API v1)

**Files:**
- Create: `tests/unit/routes/test_api_v1_accounts_ledgers_contract.py`

---

### Task 10: Update migration progress doc (Phase 2)

**Files:**
- Modify: `docs/changes/refactor/004-flask-restx-openapi-migration-progress.md`

**Step 1: Mark Phase 2 as DOING**

- 更新摘要与 Phase 2 checklist

**Step 2: Mark migrated endpoints as DONE**

在对应模块表格中将已迁移的 endpoint 标记为 DONE，并在备注注明新入口路径（不带 METHOD）。

---

### Task 11: Verification

**Step 1: Run unit tests**

Run: `uv run pytest -m unit`

Expected: 0 failed

**Step 2: Verify OpenAPI export**

Run: `uv run python scripts/dev/openapi/export_openapi.py --check`

Expected: exit 0

**Step 3: Ensure progress doc endpoint set not drifted**

Run: `uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress`

Expected: missing=0 extra=0

