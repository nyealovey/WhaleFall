# 004 Flask-RESTX/OpenAPI Phase 2 (Instances Write) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Instances 域的写操作 API（create/update/delete/restore）迁移到 RestX API v1（/api/v1/instances/**），保持既有 JSON envelope 与错误口径, 并保持 CSRF 约束不降级。

**Architecture:** 在 app/api/v1/namespaces/instances.py 复用既有 InstanceWriteService；统一通过 BaseResource.safe_call() 执行业务并提交事务；鉴权/权限使用 API v1 专用装饰器（JSON-only），写操作额外叠加 require_csrf。

**Tech Stack:** Flask, Flask-RESTX, Flask-WTF(CSRF), pytest

---

## API v1 路径映射（Instances Write）

- 旧：POST /instances/api/create -> 新：POST /api/v1/instances
- 旧：POST /instances/api/<int:instance_id>/delete -> 新：POST /api/v1/instances/<int:instance_id>/delete
- 旧：POST /instances/api/<int:instance_id>/restore -> 新：POST /api/v1/instances/<int:instance_id>/restore
- 旧：POST /instances/api/<int:instance_id>/edit -> 新：PUT /api/v1/instances/<int:instance_id>

---

### Task 1: Extend API v1 Instances contract tests (write)

**Files:**
- Modify: tests/unit/routes/test_api_v1_instances_contract.py

**Step 1: Write the failing tests**

- test_api_v1_instances_create_contract
- test_api_v1_instances_update_contract
- test_api_v1_instances_soft_delete_contract
- test_api_v1_instances_restore_contract

测试要点:
- 使用同一个 client 先请求 GET /auth/api/csrf-token 获取 token, 并在后续写请求中通过 X-CSRFToken 头传递。
- 校验状态码（create=201, update=200, delete=200, restore=200）与最小 envelope 字段（success/error/message/timestamp/data）。

**Step 2: Run tests to verify they fail**

Run: uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v

Expected: FAIL（405/404 或方法未实现）

---

### Task 2: Implement Instances write endpoints in RestX namespace

**Files:**
- Modify: app/api/v1/namespaces/instances.py

**Step 1: Implement POST /api/v1/instances**

- 装饰器: api_login_required + api_permission_required("create") + require_csrf
- body: JSON 或表单 (与旧端点兼容), request.get_json(silent=True) / request.form
- 调用: InstanceWriteService().create(payload, operator_id=current_user.id)
- 返回: data={"instance": instance.to_dict()}, message="实例创建成功", status=201

**Step 2: Implement PUT /api/v1/instances/<id>**

- 装饰器: api_login_required + api_permission_required("update") + require_csrf
- 调用: InstanceWriteService().update(instance_id, payload, operator_id=current_user.id)
- 返回: message="实例更新成功"

**Step 3: Implement POST /api/v1/instances/<id>/delete**

- 装饰器: api_login_required + api_permission_required("delete") + require_csrf
- 调用: InstanceWriteService().soft_delete(instance_id, operator_id=current_user.id)
- 返回: data={"instance_id": ..., "deleted_at": ..., "deletion_mode": "soft"}, message="实例已移入回收站"

**Step 4: Implement POST /api/v1/instances/<id>/restore**

- 装饰器: api_login_required + api_permission_required("update") + require_csrf
- 调用: InstanceWriteService().restore(instance_id, operator_id=current_user.id)
- 返回:
  - restored=False: message="实例未删除，无需恢复", data={"instance": instance.to_dict()}
  - restored=True: message="实例恢复成功", data={"instance": instance.to_dict()}

**Step 5: Run tests**

Run: uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v

Expected: PASS

---

### Task 3: Update progress doc + verification gates

**Files:**
- Modify: docs/changes/refactor/004-flask-restx-openapi-migration-progress.md

**Step 1: Mark instances write endpoints as DONE**

- 在 "实例管理模块" 中将以下三条标记为 DONE 并补充新入口:
  - POST /instances/api/create
  - POST /instances/api/<int:instance_id>/delete
  - POST /instances/api/<int:instance_id>/restore
- 在 "实例详情扩展模块" 中将以下条目标记为 DONE 并补充新入口:
  - POST /instances/api/<int:instance_id>/edit

**Step 2: Run unit tests**

Run: uv run pytest -m unit

Expected: 0 failed

**Step 3: Verify OpenAPI export**

Run: uv run python scripts/dev/openapi/export_openapi.py --check

Expected: exit 0

**Step 4: Ensure progress doc endpoint set not drifted**

Run: uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress

Expected: missing=0 extra=0

