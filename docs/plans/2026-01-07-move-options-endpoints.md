# Options Endpoints Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 移除旧的 common db_type options 接口，并将 `instances/databases` 的 options 接口下沉到各自 namespace（`/api/v1/instances/options` 与 `/api/v1/databases/options`）。

**Architecture:** 保持现有 `FilterOptionsService` 能力不变，仅迁移路由层与 OpenAPI 模型引用；同步前端调用路径与单测契约，确保运行期不依赖旧的 `/api/v1/common/*` 路径。

**Tech Stack:** Flask-RESTX、Flask Blueprint、pytest、前端模块化 JS（`app/static/js/modules/...`）。

---

### Task 1: 写入/调整单测（先失败）

**Files:**
- Modify: `tests/unit/routes/test_api_v1_common_options_contract.py`

**Step 1: Write the failing test**

- 将实例/数据库 options 的请求路径改为：
  - `/api/v1/instances/options`
  - `/api/v1/databases/options`
- 删除 `database-types/options` 的契约测试（接口将被移除）

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_common_options_contract.py -q`
Expected: 404（新路径尚未实现/未注册）

---

### Task 2: 迁移路由（实现最小改动让测试通过）

**Files:**
- Modify: `app/api/v1/namespaces/instances.py`
- Modify: `app/api/v1/namespaces/databases.py`
- Delete: `app/api/v1/namespaces/common.py`
- Modify: `app/api/v1/__init__.py`

**Step 1: Implement instances options route**

- 在 `instances` namespace 添加 `@ns.route("/options")` 的 GET 资源
- 逻辑与旧 `CommonInstancesOptionsResource.get` 一致（支持 `db_type`）

**Step 2: Implement databases options route**

- 在 `databases` namespace 添加 `@ns.route("/options")` 的 GET 资源
- 逻辑与旧 `CommonDatabasesOptionsResource.get` 一致（校验 `instance_id`、分页参数）

**Step 3: Remove common namespace**

- 删除 `app/api/v1/namespaces/common.py`
- 从 `app/api/v1/__init__.py` 移除 `common_ns` import 与 `api.add_namespace(common_ns, path="/common")`

**Step 4: Run tests**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_common_options_contract.py -q`
Expected: PASS

---

### Task 3: 同步前端调用路径

**Files:**
- Modify: `app/static/js/modules/views/capacity/databases.js`
- Modify: `app/static/js/modules/views/capacity/instances.js`

**Step 1: Update endpoints**

- 将前端 options endpoint 更新到新的 namespace 路径：
  - `"/api/v1/instances/options"`
  - `"/api/v1/databases/options"`

**Step 2: Smoke check**

Run: `rg -n \"api/v1/common/(instances|databases)/options\" app/static/js -S`
Expected: no matches

---

### Task 4: 清理文档引用（避免误导）

**Files:**
- Modify: `docs/architecture/common-options.md`
- Modify: `docs/Obsidian/调整下面这些 api.md`
- Modify: `docs/Obsidian/canvas/common/common-api-contract.canvas`
- Modify: `docs/plans/2025-12-28-db-type-single-source-of-truth.md`

**Step 1: Update docs paths**

- 删除 `database-types/options` 相关描述
- 将 common 下的 instances/databases options 路径更新为新的 namespace 路径

**Step 2: Grep check**

Run: `rg -n \"api/v1/common/(database-types|instances|databases)/options\" -S docs tests app -g'*.md' -g'*.canvas'`
Expected: no matches

---

### Task 5: 回归验证

**Files:**
- None

**Step 1: Run unit tests**

Run: `uv run pytest -m unit -q`
Expected: PASS
