# 004 Flask-RESTX/OpenAPI Phase 2 (Tags Write) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Tags 域的写操作 API（create/update/delete/batch_delete）迁移到 RestX API v1（/api/v1/tags/**），保持既有 JSON envelope 与错误口径, 并保持 CSRF 约束不降级。

**Architecture:** 在 app/api/v1/namespaces/tags.py 复用既有 TagWriteService；统一通过 BaseResource.safe_call() 执行业务并提交事务；鉴权/权限使用 API v1 专用装饰器（JSON-only），写操作额外叠加 require_csrf。对 "标签仍被实例使用" 场景, 用 ConflictError(message_key="TAG_IN_USE") 走统一错误封套。

**Tech Stack:** Flask, Flask-RESTX, Flask-WTF(CSRF), pytest

---

## API v1 路径映射（Tags Write）

- 旧：POST /tags/api/create -> 新：POST /api/v1/tags
- 旧：POST /tags/api/edit/<int:tag_id> -> 新：PUT /api/v1/tags/<int:tag_id>
- 旧：POST /tags/api/delete/<int:tag_id> -> 新：POST /api/v1/tags/<int:tag_id>/delete
- 旧：POST /tags/api/batch_delete -> 新：POST /api/v1/tags/batch-delete

---

### Task 1: Extend API v1 Tags contract tests (write)

**Files:**
- Modify: tests/unit/routes/test_api_v1_tags_contract.py

**Step 1: Write the failing tests**

- test_api_v1_tags_create_contract
- test_api_v1_tags_update_contract
- test_api_v1_tags_delete_contract
- test_api_v1_tags_delete_in_use_returns_conflict
- test_api_v1_tags_batch_delete_contract

测试要点:
- 使用同一个 client 先请求 GET /auth/api/csrf-token 获取 token, 并在后续写请求中通过 X-CSRFToken 头传递。
- 校验状态码:
  - create=201
  - update=200
  - delete=200
  - delete(in_use)=409 且 message_code="TAG_IN_USE"
  - batch_delete=200 或 207 (取决于是否包含失败)

**Step 2: Run tests to verify they fail**

Run: uv run pytest -m unit tests/unit/routes/test_api_v1_tags_contract.py -v

Expected: FAIL（405/404 或方法未实现）

---

### Task 2: Implement Tags write endpoints in RestX namespace

**Files:**
- Modify: app/api/v1/namespaces/tags.py

**Step 1: Implement POST /api/v1/tags**

- 装饰器: api_login_required + api_permission_required("create") + require_csrf
- 调用: TagWriteService().create(payload, operator_id=current_user.id)
- 返回: data={"tag": tag.to_dict()}, message="标签创建成功", status=201

**Step 2: Implement PUT /api/v1/tags/<id>**

- 装饰器: api_login_required + api_permission_required("update") + require_csrf
- 调用: TagWriteService().update(tag_id, payload, operator_id=current_user.id)
- 返回: message="标签更新成功"

**Step 3: Implement POST /api/v1/tags/<id>/delete**

- 装饰器: api_login_required + api_permission_required("delete") + require_csrf
- 调用: TagWriteService().delete(tag_id, operator_id=current_user.id)
- in_use: raise ConflictError(message_key="TAG_IN_USE", status=409)
- deleted: success data={"tag_id": tag_id}, message="标签删除成功"

**Step 4: Implement POST /api/v1/tags/batch-delete**

- 装饰器: api_login_required + api_permission_required("delete") + require_csrf
- body: {"tag_ids": [1,2,3]}
- 调用: TagWriteService().batch_delete(tag_ids, operator_id=current_user.id)
- has_failure=True: status=207, message="部分标签未能删除"
- 否则: status=200, message="标签批量删除成功"

**Step 5: Run tests**

Run: uv run pytest -m unit tests/unit/routes/test_api_v1_tags_contract.py -v

Expected: PASS

---

### Task 3: Update progress doc + verification gates

**Files:**
- Modify: docs/changes/refactor/004-flask-restx-openapi-migration-progress.md

**Step 1: Mark tags write endpoints as DONE**

在 "标签管理模块" 中将以下条目标记为 DONE 并补充新入口:
- POST /tags/api/create
- POST /tags/api/edit/<int:tag_id>
- POST /tags/api/delete/<int:tag_id>
- POST /tags/api/batch_delete

**Step 2: Run unit tests**

Run: uv run pytest -m unit

Expected: 0 failed

**Step 3: Verify OpenAPI export**

Run: uv run python scripts/dev/openapi/export_openapi.py --check

Expected: exit 0

**Step 4: Ensure progress doc endpoint set not drifted**

Run: uv run python scripts/dev/docs/generate_api_routes_inventory.py --check-progress

Expected: missing=0 extra=0

