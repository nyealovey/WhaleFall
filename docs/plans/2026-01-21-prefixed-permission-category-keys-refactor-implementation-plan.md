# Prefixed Permission Category Keys Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 对权限分类(category)字段名做破坏性重构：所有 key 加上数据库前缀（mysql/postgresql/sqlserver/oracle），并删除已废弃的 tablespace 权限分类；不考虑兼容历史数据。

**Architecture:** 以 “adapter 输出 permissions → PermissionManager 写入 snapshot.categories → facts_builder 派生 permission_facts → 前端按 db_type 渲染/策略中心按 config 渲染” 为主链路，统一替换所有旧 key。permission_configs 的 category 同步改为新 key，以保持 UI 策略中心的输入一致。

**Tech Stack:** Python (Flask + SQLAlchemy + Pydantic), Vanilla JS (Grid.js), PostgreSQL seed SQL.

---

## 0. 统一映射表（旧 → 新）

> 说明：本次重构不做兼容映射；旧 key 将被彻底移除（包含 tests/ 文档/前端）。

### 0.1 MySQL

| old | new |
| --- | --- |
| `global_privileges` | `mysql_global_privileges` |
| `database_privileges` | `mysql_database_privileges` |
| `roles` | `mysql_granted_roles` |
| `role_members` | `mysql_role_members` |

### 0.2 PostgreSQL

| old | new |
| --- | --- |
| `predefined_roles` | `postgresql_predefined_roles` |
| `role_attributes` | `postgresql_role_attributes` |
| `database_privileges` / `database_privileges_pg` | `postgresql_database_privileges` |

### 0.3 SQL Server

| old | new |
| --- | --- |
| `server_roles` | `sqlserver_server_roles` |
| `server_permissions` | `sqlserver_server_permissions` |
| `database_roles` | `sqlserver_database_roles` |
| `database_permissions` / `database_privileges` | `sqlserver_database_permissions` |

### 0.4 Oracle

| old | new |
| --- | --- |
| `roles` / `oracle_roles` | `oracle_roles` |
| `system_privileges` | `oracle_system_privileges` |

### 0.5 Removed

- `tablespace_privileges`：已在 seed 数据中标注“归并到 system_privileges”，且需求确认不再独立存在；本次直接删除所有代码/渲染/测试引用。

---

## Task 1: 重构 Permission Snapshot categories 写入（PermissionManager）

**Files:**
- Modify: `app/services/accounts_sync/permission_manager.py`
- Test: `tests/unit/services/test_account_permission_manager.py`

**Step 1: Write the failing test**

将 `test_apply_permissions_puts_privileges_into_categories` 的输入 key 改为新 key，并断言写入 `permission_snapshot.categories.<new_key>`。

示例（片段）：

```python
permissions = {"mysql_global_privileges": ["SELECT"], "unknown_field": "value"}
manager._apply_permissions(record, permissions)
assert record.permission_snapshot.get("categories", {}).get("mysql_global_privileges") == ["SELECT"]
assert record.permission_snapshot.get("extra", {}).get("unknown_field") == "value"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_account_permission_manager.py -q`
Expected: FAIL（新 key 未被归类，落到了 extra）

**Step 3: Write minimal implementation**

- 更新 `_PERMISSION_TO_SNAPSHOT_CATEGORY_KEY`：
  - 删除旧 key
  - 增加新 key（映射到自身）
  - 删除 `tablespace_privileges` / `database_privileges_pg` / `database_permissions` 等旧映射
- 更新 `PRIVILEGE_FIELD_LABELS`：
  - key 改为新 key（label 仍用中文显示名即可）
  - 删除 `tablespace_privileges`

**Step 4: Run test to verify it passes**

Run: 同上
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/accounts_sync/permission_manager.py tests/unit/services/test_account_permission_manager.py
git commit -m "refactor: prefix permission snapshot category keys"
```

---

## Task 2: 更新 permission_snapshot(v4) internal contract normalization

**Files:**
- Modify: `app/schemas/internal_contracts/permission_snapshot_v4.py`
- Test: `tests/unit/schemas/test_permission_snapshot_v4_internal_contract.py`

**Step 1: Write the failing test**

把测试中的 categories key 替换为新 key，例如：

- PostgreSQL：`predefined_roles` → `postgresql_predefined_roles`
- SQLServer：`server_roles` → `sqlserver_server_roles`；`database_roles` → `sqlserver_database_roles`
- Oracle：保持 `oracle_roles`，但覆盖 `oracle_system_privileges` 不需要 normalize（list[str] 直出）

示例：

```python
categories = {"sqlserver_server_roles": [{"name": "sysadmin"}]}
normalized = normalize_permission_snapshot_categories_v4("sqlserver", categories)
assert normalized["sqlserver_server_roles"] == ["sysadmin"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/schemas/test_permission_snapshot_v4_internal_contract.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

按 db_type 分支，把 normalize 的 key 全部替换为新 key：

- PostgreSQL: normalize `postgresql_predefined_roles`
- SQLServer: normalize `sqlserver_server_roles` + `sqlserver_database_roles`
- Oracle: normalize `oracle_roles`（维持 list[str] / list[{role}] 兼容）

**Step 4: Run test to verify it passes**

Run: 同上
Expected: PASS

**Step 5: Commit**

```bash
git add app/schemas/internal_contracts/permission_snapshot_v4.py tests/unit/schemas/test_permission_snapshot_v4_internal_contract.py
git commit -m "refactor: normalize v4 snapshot categories with db-prefixed keys"
```

---

## Task 3: 更新 facts_builder 从新 categories 提取 roles/privileges（不改 facts 结构）

**Files:**
- Modify: `app/services/accounts_permissions/facts_builder.py`
- Test: `tests/unit/services/test_permission_facts_builder.py`

**Step 1: Write the failing test**

把用到旧 categories key 的测试改成新 key，例如：

```python
snapshot = {
  "version": 4,
  "categories": {
    "sqlserver_server_roles": [{"name": "sysadmin"}],
    "sqlserver_database_roles": {"db1": [{"name": "db_owner"}]},
    "sqlserver_server_permissions": ["CONTROL SERVER"],
    "sqlserver_database_permissions": {"db1": ["ALTER"]},
  },
  "type_specific": {},
  "extra": {},
  "errors": [],
  "meta": {},
}
facts = build_permission_facts(record=_StubRecord(db_type="sqlserver"), snapshot=snapshot)
assert set(facts["roles"]) == {"sysadmin", "db_owner"}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/test_permission_facts_builder.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- `_extract_roles()` / `_extract_privileges()` 中把 categories key 全部切换为新 key
- 删除 `tablespace_privileges` 的提取逻辑（以及对应返回字段 `privileges["tablespace"]`）

**Step 4: Run test to verify it passes**

Run: 同上
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/accounts_permissions/facts_builder.py tests/unit/services/test_permission_facts_builder.py
git commit -m "refactor: facts builder reads db-prefixed category keys"
```

---

## Task 4: Adapter & external_contracts 输出改为新 key（分数据库逐个完成）

### Task 4.1: MySQL adapter/schema

**Files:**
- Modify: `app/services/accounts_sync/adapters/mysql_adapter.py`
- Modify: `app/schemas/external_contracts/mysql_account.py`
- Modify: `app/core/types/accounts.py`
- Test: `tests/unit/services/accounts_sync/test_mysql_adapter_normalize_account.py`
- Test: `tests/unit/services/accounts_sync/test_mysql_adapter_roles.py`

**Step 1: Write the failing test**

把测试中的 permissions key 全部替换为：
- `mysql_global_privileges`
- `mysql_database_privileges`
- `mysql_granted_roles`
- `mysql_role_members`

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/accounts_sync/test_mysql_adapter_normalize_account.py tests/unit/services/accounts_sync/test_mysql_adapter_roles.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- `MySQLPermissionSnapshotSchema` 字段改名并调整 validators
- `mysql_adapter.py`：
  - `_get_user_permissions()` 输出 key 改名
  - enrich 时写入 `mysql_granted_roles` / `mysql_role_members`

**Step 4: Run test to verify it passes**

Run: 同上
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/accounts_sync/adapters/mysql_adapter.py app/schemas/external_contracts/mysql_account.py app/core/types/accounts.py \
  tests/unit/services/accounts_sync/test_mysql_adapter_normalize_account.py tests/unit/services/accounts_sync/test_mysql_adapter_roles.py
git commit -m "refactor: mysql permissions keys prefixed"
```

### Task 4.2: PostgreSQL adapter/schema

**Files:**
- Modify: `app/services/accounts_sync/adapters/postgresql_adapter.py`
- Modify: `app/schemas/external_contracts/postgresql_account.py`
- Modify: `app/core/types/accounts.py`
- Test: `tests/unit/services/accounts_sync/test_postgresql_adapter_normalize_account.py`

**Step 1: Write the failing test**

把 `database_privileges_pg`/`predefined_roles`/`role_attributes` 改为：
- `postgresql_database_privileges`
- `postgresql_predefined_roles`
- `postgresql_role_attributes`

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/accounts_sync/test_postgresql_adapter_normalize_account.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- schema 字段改名
- adapter 输出 key 改名，并删除 `database_privileges_pg`（不再做 alias）

**Step 4: Run test to verify it passes**

Run: 同上
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/accounts_sync/adapters/postgresql_adapter.py app/schemas/external_contracts/postgresql_account.py app/core/types/accounts.py \
  tests/unit/services/accounts_sync/test_postgresql_adapter_normalize_account.py
git commit -m "refactor: postgresql permissions keys prefixed"
```

### Task 4.3: SQLServer adapter/schema

**Files:**
- Modify: `app/services/accounts_sync/adapters/sqlserver_adapter.py`
- Modify: `app/schemas/external_contracts/sqlserver_account.py`
- Modify: `app/core/types/accounts.py`
- Test: `tests/unit/services/accounts_sync/test_sqlserver_adapter_normalize_account.py`
- Test: `tests/unit/services/test_sqlserver_adapter_permissions.py`

**Step 1: Write the failing test**

把旧 key 改为：
- `sqlserver_server_roles`
- `sqlserver_server_permissions`
- `sqlserver_database_roles`
- `sqlserver_database_permissions`

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/accounts_sync/test_sqlserver_adapter_normalize_account.py tests/unit/services/test_sqlserver_adapter_permissions.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- schema 字段改名
- adapter `_get_login_permissions()` 输出 key 改名
- enrich 侧写入 key 同步改名

**Step 4: Run test to verify it passes**

Run: 同上
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/accounts_sync/adapters/sqlserver_adapter.py app/schemas/external_contracts/sqlserver_account.py app/core/types/accounts.py \
  tests/unit/services/accounts_sync/test_sqlserver_adapter_normalize_account.py tests/unit/services/test_sqlserver_adapter_permissions.py
git commit -m "refactor: sqlserver permissions keys prefixed"
```

### Task 4.4: Oracle adapter/schema

**Files:**
- Modify: `app/services/accounts_sync/adapters/oracle_adapter.py`
- Modify: `app/schemas/external_contracts/oracle_account.py`
- Modify: `app/core/types/accounts.py`
- Test: `tests/unit/services/accounts_sync/test_oracle_adapter_normalize_account.py`

**Step 1: Write the failing test**

把 `system_privileges` 改为 `oracle_system_privileges`（roles 统一用 `oracle_roles`）。

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/services/accounts_sync/test_oracle_adapter_normalize_account.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- schema 字段改名
- adapter 输出 key 改名（含 `_fetch_raw_accounts` 与 `_get_user_permissions`）

**Step 4: Run test to verify it passes**

Run: 同上
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/accounts_sync/adapters/oracle_adapter.py app/schemas/external_contracts/oracle_account.py app/core/types/accounts.py \
  tests/unit/services/accounts_sync/test_oracle_adapter_normalize_account.py
git commit -m "refactor: oracle permissions keys prefixed"
```

---

## Task 5: permission_configs seed & API contract 使用新 category key

**Files:**
- Modify: `sql/seed/postgresql/permission_configs.sql`
- Test: `tests/unit/routes/test_api_v1_accounts_classifications_contract.py`

**Step 1: Write the failing test**

把测试里插入的 `PermissionConfig(category=...)` 改为新 key，例如 MySQL：

```python
permission_config = PermissionConfig(
  db_type=\"mysql\",
  category=\"mysql_global_privileges\",
  permission_name=\"SELECT\",
  ...
)
```

并在断言 options 返回时使用新 key。

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_accounts_classifications_contract.py -q`
Expected: FAIL（options 返回没有新 key）

**Step 3: Write minimal implementation**

- seed SQL：把所有 INSERT 的 category 换成新 key（按 0 章映射）
- 确认 `PermissionConfig.get_permissions_by_db_type()` 无需改动（它只是按 category 分组）

**Step 4: Run test to verify it passes**

Run: 同上
Expected: PASS

**Step 5: Commit**

```bash
git add sql/seed/postgresql/permission_configs.sql tests/unit/routes/test_api_v1_accounts_classifications_contract.py
git commit -m \"refactor: permission configs categories prefixed\"
```

---

## Task 6: 前端权限策略中心读取新 category key

**Files:**
- Modify: `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js`

**Step 1: Manual sanity check (no JS unit tests)**

仅做静态检查：把读取 permissions 的位置从旧 key 改为新 key。

示例（MySQL）：

```js
const globals = Array.isArray(permissions.mysql_global_privileges) ? permissions.mysql_global_privileges : [];
const databases = Array.isArray(permissions.mysql_database_privileges) ? permissions.mysql_database_privileges : [];
```

Oracle/SQLServer/PostgreSQL 同理。

**Step 2: Run eslint to verify**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: PASS

**Step 3: Commit**

```bash
git add app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js
git commit -m \"refactor: permission policy center uses prefixed categories\"
```

---

## Task 7: 权限详情弹窗按新 snapshot.categories key 渲染 + 移除表空间区块

**Files:**
- Modify: `app/static/js/modules/views/components/permissions/permission-modal.js`

**Step 1: Manual sanity check**

- MySQL: `roles/role_members/global_privileges/database_privileges` → 新 key
- PostgreSQL: `predefined_roles/role_attributes/database_privileges` → 新 key
- SQLServer: `server_roles/server_permissions/database_roles/database_permissions` → 新 key
- Oracle: 渲染 `oracle_roles` + `oracle_system_privileges`，删除 tablespace section

**Step 2: Run eslint to verify**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: PASS

**Step 3: Commit**

```bash
git add app/static/js/modules/views/components/permissions/permission-modal.js
git commit -m \"refactor: permission modal renders prefixed categories\"
```

---

## Task 8: 全量回归（Python + JS）

**Files:**
- (no code changes; verification only)

**Step 1: Run unit tests**

Run: `uv run pytest -m unit -q`
Expected: PASS

**Step 2: Run typecheck**

Run: `make typecheck`
Expected: PASS

**Step 3: Run lint**

Run: `./scripts/ci/ruff-report.sh style`
Expected: PASS

**Step 4: Run eslint**

Run: `./scripts/ci/eslint-report.sh quick`
Expected: PASS

---

## Task 9: 文档同步（可选但推荐）

**Files:**
- Modify: `docs/Obsidian/reference/service/accounts-sync-permission-manager.md`
- Modify: `docs/Obsidian/reference/service/mysql-roles-sync-and-display.md`

**Step 1: Update docs**

- 替换旧 category key 为新 key（按 0 章映射）
- 删除 tablespace_privileges 相关描述

**Step 2: Commit**

```bash
git add docs/Obsidian/reference/service/accounts-sync-permission-manager.md docs/Obsidian/reference/service/mysql-roles-sync-and-display.md
git commit -m \"docs: update permission category keys\"
```

