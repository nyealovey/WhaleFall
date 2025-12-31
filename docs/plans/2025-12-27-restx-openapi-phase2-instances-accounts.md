# 004 Flask-RESTX/OpenAPI Phase 2 (Instances Accounts Read) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Instances 域的账户相关只读 API 迁移到 RestX API v1（/api/v1/instances/<id>/accounts/**），保持既有 JSON envelope 与错误口径。

**Architecture:** 在 app/api/v1/namespaces/instances.py 新增子资源路由, 复用 InstanceAccountsService；统一通过 BaseResource.safe_call() 输出封套；鉴权/权限使用 api_login_required + api_permission_required("view")。

**Tech Stack:** Flask, Flask-RESTX, pytest

---

## API v1 路径映射（Instances Accounts Read）

- 旧：GET /instances/api/<int:instance_id>/accounts
  - 新：GET /api/v1/instances/<int:instance_id>/accounts
- 旧：GET /instances/api/<int:instance_id>/accounts/<int:account_id>/permissions
  - 新：GET /api/v1/instances/<int:instance_id>/accounts/<int:account_id>/permissions
- 旧：GET /instances/api/<int:instance_id>/accounts/<int:account_id>/change-history
  - 新：GET /api/v1/instances/<int:instance_id>/accounts/<int:account_id>/change-history

---

### Task 1: Add API v1 instances accounts contract tests

**Files:**
- Modify: tests/unit/routes/test_api_v1_instances_contract.py

**Step 1: Write the failing tests**

- test_api_v1_instances_accounts_list_contract
- test_api_v1_instances_account_permissions_contract
- test_api_v1_instances_account_change_history_contract

**Step 2: Run tests to verify they fail**

Run: uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v

Expected: FAIL（404 或未实现）

---

### Task 2: Implement API v1 instances accounts endpoints

**Files:**
- Modify: app/api/v1/namespaces/instances.py

**Step 1: Implement GET /api/v1/instances/<id>/accounts**

- 调用: InstanceAccountsService().list_accounts(filters)
- 返回: data={"items","total","page","pages","limit","summary"}, message="获取实例账户数据成功"

**Step 2: Implement GET /api/v1/instances/<id>/accounts/<account_id>/permissions**

- 调用: InstanceAccountsService().get_account_permissions(instance_id, account_id)
- 返回: data=marshal(...), message="获取账户权限成功"

**Step 3: Implement GET /api/v1/instances/<id>/accounts/<account_id>/change-history**

- 调用: InstanceAccountsService().get_change_history(instance_id, account_id)
- 返回: data=marshal(...), message="获取账户变更历史成功"

**Step 4: Run tests**

Run: uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v

Expected: PASS

---

### Task 3: Update progress doc + verification gates

**Files:**
- Modify: docs/changes/refactor/004-flask-restx-openapi-migration-progress.md

**Step 1: Mark endpoints as DONE**

- 在 "实例管理模块" 中将 GET /instances/api/<int:instance_id>/accounts 标记为 DONE, 并注明新入口。
- 在 "实例详情扩展模块" 中将 permissions/change-history 两条标记为 DONE, 并注明新入口。

**Step 2: Run unit tests**

Run: uv run pytest -m unit

Expected: 0 failed

**Step 3: Verify OpenAPI export**

Run: uv run python scripts/dev/openapi/export_openapi.py --check

Expected: exit 0

**Step 4: Ensure progress doc endpoint set not drifted**

Note: 迁移期 API routes inventory tooling 已在 020 迁移期代码清理中移除；以 OpenAPI export 与 progress 文档人工核对为准。
