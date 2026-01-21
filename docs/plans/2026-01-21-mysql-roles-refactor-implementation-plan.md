# MySQL Roles Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从采集→落库→派生→API→前端展示，完整支持 MySQL role 账号与 role 关系（direct/default），并满足：台账页默认隐藏 role、实例详情页默认展示 role。

**Architecture:**
- 采集端(MySQL adapter)补齐 `mysql.user.is_role` → `type_specific.account_kind`，并批量读取 `mysql.role_edges/mysql.default_roles` 写入 `permissions.roles={direct,default}`。
- 写入端(permission_manager)将 `roles` 映射到 snapshot.categories，facts_builder 以 `direct+default` 生成 facts.roles，并对 MySQL role 账号不推导 LOCKED。
- 展示端：`/api/v1/accounts/ledgers` 增加 `include_roles`（默认 false）用于过滤；实例详情页请求显式 `include_roles=true`，并对 role 的“锁定”列展示 `-`。

**Tech Stack:** Python (Flask + SQLAlchemy), Pydantic, Flask-RESTX, Vanilla JS (Grid.js)

---

### Task 1: permission_facts 支持 MySQL roles 与 role 锁定语义

**Files:**
- Modify: `app/services/accounts_permissions/facts_builder.py`
- Test: `tests/unit/services/test_permission_facts_builder.py`

**Step 1: Write the failing test**

```python
@pytest.mark.unit
def test_build_permission_facts_mysql_roles_include_direct_and_default() -> None:
    record = _StubRecord(db_type="mysql")
    snapshot = {
        "version": 4,
        "categories": {"roles": {"direct": ["r1@%"], "default": ["r2@%"]}},
        "type_specific": {"mysql": {"account_kind": "user"}},
        "extra": {},
        "errors": [],
        "meta": {},
    }
    facts = build_permission_facts(record=record, snapshot=snapshot)
    assert set(facts["roles"]) == {"r1@%", "r2@%"}


@pytest.mark.unit
def test_build_permission_facts_mysql_role_does_not_add_locked() -> None:
    record = _StubRecord(db_type="mysql")
    snapshot = {
        "version": 4,
        "categories": {},
        "type_specific": {"mysql": {"account_kind": "role", "account_locked": True}},
        "extra": {},
        "errors": [],
        "meta": {},
    }
    facts = build_permission_facts(record=record, snapshot=snapshot)
    assert "LOCKED" not in facts["capabilities"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_permission_facts_builder.py -q`

Expected: FAIL（roles 仅包含 direct；或 role 仍被推导为 LOCKED）。

**Step 3: Write minimal implementation**
- MySQL: roles = direct + default（去重）
- MySQL: `_collect_mysql_capabilities` 仅在 `account_kind != "role"` 时根据 `account_locked` 添加 LOCKED

**Step 4: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/services/test_permission_facts_builder.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/services/test_permission_facts_builder.py app/services/accounts_permissions/facts_builder.py
git commit -m "fix: mysql facts roles and locked semantics"
```

---

### Task 2: permission_snapshot(v4) 写入 roles category

**Files:**
- Modify: `app/services/accounts_sync/permission_manager.py`
- Test: `tests/unit/services/test_account_permission_manager.py`

**Step 1: Write the failing test**

```python
@pytest.mark.unit
def test_apply_permissions_writes_roles_into_categories() -> None:
    manager = AccountPermissionManager()
    record: Any = SimpleNamespace(db_type="mysql", permission_snapshot=None)
    permissions = {"roles": {"direct": ["r1@%"], "default": []}}

    manager._apply_permissions(record, permissions)

    assert record.permission_snapshot.get("categories", {}).get("roles") == {"direct": ["r1@%"], "default": []}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py -q`

Expected: FAIL（roles 进入 extra，而不是 categories）。

**Step 3: Write minimal implementation**
- `_PERMISSION_TO_SNAPSHOT_CATEGORY_KEY` 增加：`"roles": "roles"`
- （可选）`PRIVILEGE_FIELD_LABELS` 增加：`"roles": "角色"`

**Step 4: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/services/test_account_permission_manager.py app/services/accounts_sync/permission_manager.py
git commit -m "feat: persist mysql roles into permission snapshot"
```

---

### Task 3: /api/v1/accounts/ledgers 支持 include_roles，并输出 type_specific

**Files:**
- Modify: `app/core/types/accounts_ledgers.py`
- Modify: `app/schemas/accounts_query.py`
- Modify: `app/api/v1/namespaces/accounts.py`
- Modify: `app/repositories/ledgers/accounts_ledger_repository.py`
- Modify: `app/services/ledgers/accounts_ledger_list_service.py`
- Modify: `app/api/v1/restx_models/accounts.py`
- Test: `tests/unit/routes/test_api_v1_accounts_ledgers_contract.py`
- Test: `tests/unit/schemas/test_accounts_query.py`

**Step 1: Write failing tests**
- schema：`AccountsFiltersQuery` 解析 `include_roles` 默认 false
- API：默认隐藏 mysql role（`type_specific.account_kind="role"`），传 `include_roles=true` 时包含

**Step 2: Run tests to verify they fail**

Run: `uv run pytest -m unit tests/unit/schemas/test_accounts_query.py tests/unit/routes/test_api_v1_accounts_ledgers_contract.py -q`

Expected: FAIL

**Step 3: Minimal implementation**
- 增加 `include_roles: bool` 到 filters/query
- repository 增加过滤：当 include_roles=false 时，排除 `(db_type=mysql AND coalesce(type_specific.account_kind,'')='role')`
- DTO / restx marshal：列表 item 增加 `type_specific`（Raw）

**Step 4: Run tests to verify they pass**

Run: 同上

Expected: PASS

**Step 5: Commit**

```bash
git add app/core/types/accounts_ledgers.py app/schemas/accounts_query.py app/api/v1/namespaces/accounts.py \
  app/repositories/ledgers/accounts_ledger_repository.py app/services/ledgers/accounts_ledger_list_service.py \
  app/api/v1/restx_models/accounts.py tests/unit/schemas/test_accounts_query.py \
  tests/unit/routes/test_api_v1_accounts_ledgers_contract.py
git commit -m "feat: ledgers include_roles filter and expose type_specific"
```

---

### Task 4: MySQL adapter 采集 account_kind + roles(direct/default)

**Files:**
- Modify: `app/schemas/external_contracts/mysql_account.py`
- Modify: `app/services/accounts_sync/adapters/mysql_adapter.py`
- Test: `tests/unit/services/accounts_sync/test_mysql_adapter_roles.py`

**Step 1: Write failing test**

```python
@pytest.mark.unit
def test_mysql_adapter_enrich_permissions_includes_roles_and_account_kind() -> None:
    # build accounts + stub connection returning mysql.user/is_role, role_edges/default_roles, and show grants
    ...
    assert account["permissions"]["roles"] == {"direct": ["r1@%"], "default": ["r2@%"]}
    assert account["permissions"]["type_specific"]["account_kind"] == "user"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/accounts_sync/test_mysql_adapter_roles.py -q`

Expected: FAIL

**Step 3: Minimal implementation**
- `mysql.user` 查询补齐 `is_role`（如列不存在：回退为全部 user，account_kind="user"，并打日志）
- 批量读取：
  - `mysql.role_edges` → direct_roles_map
  - `mysql.default_roles` → default_roles_map
- enrich 时把 `roles` 合并到 permissions，并把 `account_kind` 写入 type_specific

**Step 4: Run test to verify it passes**

Run: 同上

Expected: PASS

**Step 5: Commit**

```bash
git add app/schemas/external_contracts/mysql_account.py app/services/accounts_sync/adapters/mysql_adapter.py \
  tests/unit/services/accounts_sync/test_mysql_adapter_roles.py
git commit -m "feat: mysql adapter collect roles and account_kind"
```

---

### Task 5: UI - 实例详情页默认展示 role，并对 role 锁定列显示 '-'

**Files:**
- Modify: `app/static/js/modules/views/instances/detail.js`
- Modify: `app/static/js/modules/views/components/permissions/permission-modal.js`

**Step 1: Manual verification (no unit tests)**
- 实例详情页：请求 URL 包含 `include_roles=true`
- role 行：锁定列显示 `-`
- 权限弹窗：MySQL 增加“直授角色/默认角色”两块

**Step 2: Implement minimal changes**
- `buildAccountsBaseUrl()` 追加 `include_roles=true`
- locked 列 formatter：若 `meta.type_specific.account_kind === "role"` 则渲染 `-`
- MySQL 权限弹窗：渲染 `permissions.roles.direct/default`

**Step 3: Run regression checks**

Run:
- `uv run pytest -m unit -q`

**Step 4: Commit**

```bash
git add app/static/js/modules/views/instances/detail.js app/static/js/modules/views/components/permissions/permission-modal.js
git commit -m "feat: show mysql roles in instance detail and permission modal"
```

---

### Task 6: Full verification

Run:
- `make format`
- `make typecheck`
- `uv run pytest -m unit`

