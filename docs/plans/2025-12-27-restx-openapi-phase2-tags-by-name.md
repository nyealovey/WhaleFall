# 004 Flask-RESTX/OpenAPI Phase 2 (Tags By-Name Read) Implementation Plan

> 状态：Deprecated
> - 2026-01-08：`GET /api/v1/tags/by-name/<tag_name>` 因内部无调用已移除（breaking change，不保留旧路径）。

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Tags 域的「按名称获取标签详情」只读 API 迁移到 RestX API v1（`/api/v1/tags/by-name/<tag_name>`），保持既有 JSON envelope 与错误口径。

**Architecture:** 在 `app/api/v1/namespaces/tags.py` 新增子资源路由，复用 `Tag.get_tag_by_name()`；统一通过 `BaseResource.safe_call()` 输出封套；鉴权/权限使用 `api_login_required + api_permission_required("view")`（JSON-only）。

**Tech Stack:** Flask, Flask-RESTX, pytest

---

## API v1 路径映射（Tags By-Name Read）

- 旧：GET /tags/api/tags/<tag_name>
  - 新：GET /api/v1/tags/by-name/<tag_name>

---

### Task 1: Add API v1 tags by-name contract test

**Files:**
- Modify: tests/unit/routes/test_api_v1_tags_contract.py

**Step 1: Write the failing test**

- `test_api_v1_tags_get_by_name_contract`

**Step 2: Run tests to verify it fails**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_tags_contract.py -v`

Expected: FAIL（404 或未实现）

---

### Task 2: Implement API v1 tags by-name endpoint

**Files:**
- Modify: app/api/v1/namespaces/tags.py

**Step 1: Implement GET /api/v1/tags/by-name/<tag_name>**

- 调用: `Tag.get_tag_by_name(tag_name)`
- 不存在: 抛 `NotFoundError("标签不存在", extra={"tag_name": tag_name})`
- 返回: `data={"tag": tag.to_dict()}`, message="获取标签详情成功"

**Step 2: Run tests**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_tags_contract.py -v`

Expected: PASS

---

### Task 3: Update progress doc + verification gates

**Files:**
- Modify: docs/changes/refactor/004-flask-restx-openapi-migration-progress.md

**Step 1: Mark endpoint as DONE**

- 将 `GET /tags/api/tags/<tag_name>` 标记为 DONE，并注明新入口（不带 METHOD）。

**Step 2: Run unit tests**

Run: `uv run pytest -m unit`

Expected: 0 failed

**Step 3: Verify OpenAPI export**

Run: `uv run python scripts/dev/openapi/export_openapi.py --check`

Expected: exit 0

**Step 4: Ensure progress doc endpoint set not drifted**

Note: 迁移期 API routes inventory tooling 已在 020 迁移期代码清理中移除；以 OpenAPI export 与 progress 文档人工核对为准。
