# MySQL 角色(ROLE)展示与权限采集重构设计

> 状态: 草案（待确认）
> 创建: 2026-01-21
> 目标模块:
> - 采集: `app/services/accounts_sync/adapters/mysql_adapter.py`
> - 快照/派生: `app/services/accounts_sync/permission_manager.py`、`app/services/accounts_permissions/facts_builder.py`
> - API: `app/services/ledgers/accounts_ledger_list_service.py`、`app/api/v1/restx_models/accounts.py`
> - UI(列表): `app/static/js/modules/views/instances/detail.js`、`app/static/js/modules/views/accounts/ledgers.js`
> - UI(权限弹窗): `app/static/js/modules/views/components/permissions/permission-modal.js`

## 背景

当前 MySQL 存在自定义角色（例如 `*_role@%`）。但系统内：

- 账户列表无法区分“用户账号 vs 角色账号”，导致角色看起来像“异常账号”。
- 角色通常处于 `account_locked`（不可登录）状态，前端直接渲染为“已锁定”（红色），造成误解。
- 权限弹窗仅展示全局/库级权限，不展示“账号的直授角色 / 默认角色（DEFAULT ROLE）”。

本设计目标是：从采集源头到快照/派生再到前端展示，形成一条稳定的数据链路，**让 MySQL 角色可以被正确识别与展示**。

## 目标

- 角色账号**需要落库**（可用于审计/权限查看/后续治理），并在数据侧明确标注类型（role vs user）。
- 账户台账页面（Accounts Ledgers）默认**不展示 MySQL 角色账号**，只展示“真实用户账号”，避免把角色误当成异常账号。
- 实例详情页（Instance Detail）账户列表默认**展示 MySQL 角色账号**，并支持查看 role 的权限（权限弹窗可展示 role 自身权限 + role 的角色关系）。
- 在权限弹窗中展示：
  - 直授角色（GRANT role TO user）
  - 默认角色（SET DEFAULT ROLE / mysql.default_roles）
- 设计保持最小侵入：不引入新表结构（优先使用 JSON 字段扩展），不改变现有对外接口的核心语义。

## 非目标（本次不做）

- 不计算“生效权限（effective privileges）”：不把角色继承带来的权限合并到用户的全局/库级权限中。
- 不引入跨数据库类型的统一“账号类型体系”（本次只解决 MySQL 角色采集与展示链路）。
- 不解决 SQL Server 相关展示问题（已明确本次不考虑）。

## 关键约束与事实

- MySQL 将“用户/角色”都视为 authorization identifier，二者具备一定互换性；
  因此需要明确“列表口径/权限口径”的数据来源与边界（避免把角色当账号展示）。
- 我们当前的“锁定状态”来自 `permission_facts.capabilities` 的 `LOCKED`，对 MySQL 主要由 `type_specific.account_locked` 推导：
  - 推导逻辑: `app/services/accounts_permissions/facts_builder.py`
  - 展示逻辑: `instances/detail.js`、`accounts/ledgers.js`

## 方案（确定）

本次不做方案分叉，直接采用结构化系统表作为单一真源：

- 角色关系：`mysql.role_edges`（直授） + `mysql.default_roles`（默认角色）
- 类型真源：`mysql.user.is_role` → `account_kind=user|role`（不做启发式补充）
- 列表口径：
  - 账户台账页面：默认不展示 MySQL 角色账号（`include_roles` 默认 false）
  - 实例详情页：默认展示 MySQL 角色账号（前端请求显式 `include_roles=true`）
- 不解析 `SHOW GRANTS` 中的“GRANT role TO user / SET DEFAULT ROLE”文本，不使用启发式补充

## 数据口径设计

### 1) 角色关系

- 直授角色：来自 `mysql.role_edges`（account → role）
- 默认角色：来自 `mysql.default_roles`（account → default role）

输出到快照的 canonical 形状（permission_snapshot.categories.roles）：

```json
{
  "roles": {
    "direct": ["report_read_role@%", "srm_order_role@%"],
    "default": ["report_read_role@%"]
  }
}
```

说明：
- `direct/default` 均为 `list[str]`，元素统一使用 `user@host` 形式，避免前端再拼装。
- 本次不做 effective roles（继承闭包）与 admin option 的细分；如后续需要，可扩展为：
  - `direct_admin`: [...]
  - `effective`: [...]

### 2) 列表口径（不展示角色账号）

本次明确：角色账号需要落库，但默认不进入“账户台账页面”的展示口径。

实现口径建议（不启发式、可解释）：

- 以 `mysql.user.is_role` 为单一真源写入类型字段：
  - `is_role = 'N'` → `account_kind = "user"`
  - `is_role = 'Y'` → `account_kind = "role"`
- 同步落库：`user` 与 `role` 都会写入 `InstanceAccount/AccountPermission`。
- 台账页面默认过滤规则（仅对 MySQL 生效）：
  - `account_kind != "role"`（即仅展示 user）
  - 通过可选 query 参数 `include_roles=true` 可临时包含角色（用于排障/审计；UI 默认不打开）
> 备注：用户提到“未被使用的角色等于无效角色”。采用“台账默认不展示 role（include_roles 默认 false）”后，这类角色也不会出现在账号台账中；是否需要额外治理（清理/告警）不在本次范围内。

## 采集链路重构（源头 → adapter 输出）

### 采集源

- 账号基表：`mysql.user`
  - 已采集：`Super_priv`、`Grant_priv`、`account_locked`、`plugin`、`password_last_changed`
  - 需要补充/确认：`is_role`（用于标记账号类型并支持台账过滤）
- 角色关系表：
  - `mysql.role_edges`
  - `mysql.default_roles`
- 权限详情：`SHOW GRANTS FOR user@host`

### SQL 示例（建议）

说明：以下 SQL 用于说明“我们要采什么数据”。具体实现时可根据实例规模选择：
- 小实例：直接全表读取 `role_edges/default_roles` 并在内存中过滤/映射（实现简单）。
- 大实例：按目标账号列表做 WHERE 过滤，避免全表扫描。

直授角色（role_edges：account → role）：

```sql
SELECT
  CONCAT(FROM_USER, '@', FROM_HOST) AS grantee,
  CONCAT(TO_USER, '@', TO_HOST) AS role,
  WITH_ADMIN_OPTION AS with_admin_option
FROM mysql.role_edges;
```

默认角色（default_roles：account → default role）：

```sql
SELECT
  CONCAT(USER, '@', HOST) AS grantee,
  CONCAT(DEFAULT_ROLE_USER, '@', DEFAULT_ROLE_HOST) AS role
FROM mysql.default_roles;
```

> 备注：如果后续需要展示“一个角色被授予给哪些账号”，可对 role_edges 做反向聚合（按 `role` 作为 key 收集 `grantee`）。

### Adapter 输出（RemoteAccount.permissions）

在 `app/services/accounts_sync/adapters/mysql_adapter.py` 中，把权限快照扩展为（示例为“用户账号”）：

```python
{
  "global_privileges": [...],
  "database_privileges": {"db": ["SELECT", "INSERT"]},
  "roles": {"direct": ["report_read_role@%"], "default": ["report_read_role@%"]},
  "type_specific": {
    "host": "%",
    "original_username": "app_user",
    "account_locked": false,
    "plugin": "caching_sha2_password",
    "password_last_changed": "...",
    "account_kind": "user",
  }
}
```

建议的采集方式：
- `_fetch_raw_accounts()` 拉取 `mysql.user` 时补齐 `is_role/account_kind`（`account_kind` 不做启发式，完全由 `is_role` 决定）。
- 在 `enrich_permissions()` 前做一次批量查询：
  - 取 `role_edges` / `default_roles` → 生成：
    - `direct_roles_map[account] = [roles...]`
    - `default_roles_map[account] = [roles...]`
- 在 enrich 的 per-account 循环内，把 `roles` 合并到 `permissions`。

## 快照与派生（permission_snapshot / permission_facts）

### permission_snapshot(v4)

- 需要把 `roles` 作为 categories 的一级字段写入：
  - 修改映射表：`app/services/accounts_sync/permission_manager.py` 中 `_PERMISSION_TO_SNAPSHOT_CATEGORY_KEY` 增加 `"roles": "roles"`。
- `type_specific`（v4 snapshot）建议同时写入 `account_kind`，用于权限弹窗/排障：
  - `snapshot.type_specific.mysql.account_kind = "user"|"role"`

### permission_facts

- `facts_builder` 已支持从 `categories["roles"]` 提取 roles（目前 categories 缺失导致永远为空）。
- 建议把 roles facts 口径改为（更符合“展示默认角色”的认知）：`roles = direct + default（去重）`。
- 建议调整 MySQL 的 LOCKED 口径：仅对 `account_kind="user"` 使用 `type_specific.account_locked` 推导 `LOCKED`；
  `account_kind="role"` 不推导 LOCKED（角色不可登录是语义事实，不应在 UI 上以“已锁定(异常)”表现）。

## API 输出调整

本次不需要为“列表项”新增字段（角色默认不展示），但需要为台账列表接口增加一个**筛选开关**以控制是否包含角色账号。

权限弹窗所需的角色信息来自权限快照 `snapshot.categories.roles`，权限接口已返回 snapshot 原始结构，无需额外字段。

### 账户台账列表 `/api/v1/accounts/ledgers`（新增 query 参数）

- 新增：`include_roles`（bool，默认 false）
  - `include_roles=false` 且 `db_type=mysql` 时，过滤掉 `account_kind="role"` 的行
  - 其他 db_type 不受影响（或忽略该参数）

影响说明：
- 账户台账页面使用默认值（不传 `include_roles`），因此默认隐藏 MySQL role。
- 实例详情页当前复用该接口（`/api/v1/accounts/ledgers?instance_id=...`），为了满足“默认展示 role”，
  需要在该页面请求中**显式传 `include_roles=true`**。

实现位置建议：
- Query/filters：`app/core/types/accounts_ledgers.py`（AccountFilters 增加 include_roles）
- API parser：`app/api/v1/namespaces/accounts.py`
- Repository filter：`app/repositories/ledgers/accounts_ledger_repository.py`

## UI 展示调整

### 实例详情页（账户列表，`instances/detail.js`）

目标：默认能看到 role，且“role 看起来不是异常锁定账号”，并能点开查看 role 权限。

建议改动点：
- 请求：`buildAccountsBaseUrl()` 默认追加 `include_roles=true`（仅实例详情页这么做）。
- 行展示：在“账户”列的副标题/徽标中增加类型提示：
  - `account_kind="role"`：展示 `ROLE`（例如 `@% · ROLE · CACHING_SHA2_PASSWORD`）
  - `account_kind="user"`：保持现状
- “锁定”列：当 `account_kind="role"` 时不展示红色“已锁定”，建议展示 `-` 或 `角色不可登录`（二选一，统一即可）。
  - 推荐把 LOCKED 能力在后端 facts 层就过滤掉（见上文 `permission_facts`），从源头避免“role=locked”的误导。

### 账户台账页面（`accounts/ledgers.js`）

目标：默认只展示真实用户账号，避免 role 污染台账视图；同时 role 仍已落库可用于审计/排障。

建议改动点：
- 默认不传 `include_roles`（保持后端默认 false）。
- 可选（不强制）：在筛选区提供一个“包含角色”的高级开关，对应 `include_roles=true`（便于排障，但不影响默认直觉）。

### 权限弹窗（`permission-modal.js`）

现状：MySQL 权限只展示全局/库级权限。

设计：在 `renderMySQLPermissions()` 增加两个 section：
- “直授角色”：`permissions.roles.direct`
- “默认角色”：`permissions.roles.default`

展示形态：复用 `renderLedgerChips`，空时显示“无角色/无默认角色”。

## 数据回填与上线策略

- 该重构主要影响“同步后写入的快照/事实”。历史数据没有 `snapshot.categories.roles`。
  上线后需要对 MySQL 实例执行一次权限同步（现有任务即可），以刷新 `snapshot.categories.roles`。
- 台账列表在 `include_roles=false`（默认）时，MySQL 角色账号不会出现在台账页面，但角色记录仍保留在库中用于审计/排障。

建议的灰度/回滚：
- 先上线“角色关系采集 + 权限弹窗展示”（对列表无破坏性）。
- 再上线“台账默认过滤 role（include_roles 默认 false）”（角色账号落库但不展示）。
- 回滚策略：关闭/回退 role_edges/default_roles 采集与 UI 展示，不影响账号台账主流程；或临时把 `include_roles` 默认改为 true（仅用于排障，不建议长期保留）。

## 测试建议

- Adapter 单测：
  - 给定 role_edges/default_roles 行，断言输出 `roles.direct/default` 正确。
- 断言 `mysql.user.is_role='Y'` 的账号会被采集且 `type_specific.account_kind == "role"`。

- 台账列表（Service/Repository）单测：
  - `include_roles=false` 时，MySQL `account_kind="role"` 的账号不会出现在列表结果中
  - `include_roles=true` 时，会包含 role 账号

- facts_builder 单测：
  - categories.roles 为 `{direct, default}` 时，facts.roles 取 `direct+default`（去重）。

- 前端回归：
  - 权限弹窗：能看到“直授角色/默认角色”。
