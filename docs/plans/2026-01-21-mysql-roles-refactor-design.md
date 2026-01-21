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

- 在账户列表中将角色作为“账户”展示，但明确标注为“角色”。
- 对角色的“不可登录（account_locked）”用更符合语义的文案/样式展示，避免与“用户被锁定”混淆。
- 在权限弹窗中展示：
  - 直授角色（GRANT role TO user）
  - 默认角色（SET DEFAULT ROLE / mysql.default_roles）
- 设计保持最小侵入：不引入新表结构（优先使用 JSON 字段扩展），不改变现有对外接口的核心语义。

## 非目标（本次不做）

- 不计算“生效权限（effective privileges）”：不把角色继承带来的权限合并到用户的全局/库级权限中。
- 不做跨数据库类型的统一“账号类型体系”（仅 MySQL 落地 account_kind）。
- 不解决 SQL Server 相关展示问题（已明确本次不考虑）。

## 关键约束与事实

- MySQL 将“用户/角色”都视为 authorization identifier，二者具备一定互换性；
  因此“角色识别”需要明确口径（见下方“角色识别策略”）。
- 我们当前的“锁定状态”来自 `permission_facts.capabilities` 的 `LOCKED`，对 MySQL 主要由 `type_specific.account_locked` 推导：
  - 推导逻辑: `app/services/accounts_permissions/facts_builder.py`
  - 展示逻辑: `instances/detail.js`、`accounts/ledgers.js`

## 方案对比

### 方案 A：仅解析 `SHOW GRANTS` 文本

- 优点：无需额外访问 `mysql.*` 系统表。
- 缺点：
  - 依赖文本格式，解析脆弱；
  - 对“默认角色”语句的覆盖不稳定；
  - 难以批量、且不利于后续统计。

### 方案 B：以 `mysql.role_edges` + `mysql.default_roles` 为主（推荐）

- 优点：结构化、可批量、可明确区分“直授角色/默认角色”。
- 缺点：需要同步账号具备读取 `mysql.*` 系统表权限。

### 方案 C：仅基于 `mysql.user` 特征做启发式判断

- 优点：实现简单。
- 缺点：误判风险大；且无法获得“用户的直授角色/默认角色”。

**决策：采用方案 B，并用少量启发式作为补充（仅用于识别“未被授予/未配置默认角色但确实是角色”的条目）。**

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

### 2) “账号类型”识别（account_kind）

我们需要一个能落地展示的类型字段：

- `account_kind = "role" | "user"`

判定策略（建议）：

- 若该标识符出现在以下集合中，则视为 `role`：
  - `mysql.role_edges` 的“被授予方”（role）集合
  - `mysql.default_roles` 的 default role 集合
- 若两者都不命中，再用补充启发式：
  - `account_locked = true` 且 “无认证凭据/不可登录特征明显”（例如认证字符串为空、密码过期等）

该字段存放在两处：
- `account_permission.type_specific`（用于列表页快速展示，不依赖展开 snapshot）
- `permission_snapshot.type_specific.mysql.account_kind`（用于权限弹窗展示与后续扩展）

> 注意：由于 MySQL 的“用户/角色可互换”，上述策略本质是在做“RBAC 语义识别”。当某个 user 被当作 role 授予他人时，它将被识别为 role —— 这是符合“按用途展示”的口径。

## 采集链路重构（源头 → adapter 输出）

### 采集源

- 账号基表：`mysql.user`
  - 已采集：`Super_priv`、`Grant_priv`、`account_locked`、`plugin`、`password_last_changed`
  - 建议补充：用于启发式识别的字段（例如认证字符串/密码过期字段，按实际可用字段选取）
- 角色关系表：
  - `mysql.role_edges`
  - `mysql.default_roles`
- 权限详情：`SHOW GRANTS FOR user@host`

### Adapter 输出（RemoteAccount.permissions）

在 `app/services/accounts_sync/adapters/mysql_adapter.py` 中，把权限快照扩展为：

```python
{
  "global_privileges": [...],
  "database_privileges": {"db": ["SELECT", "INSERT"]},
  "roles": {"direct": [...], "default": [...]},
  "type_specific": {
    "host": "%",
    "original_username": "report_read_role",
    "account_locked": true,
    "plugin": "caching_sha2_password",
    "password_last_changed": "...",
    "account_kind": "role"
  }
}
```

建议的采集方式：
- 在 `enrich_permissions()` 前做一次批量查询：
  - 取 `role_edges` / `default_roles` → 生成：
    - `direct_roles_map[account] = [roles...]`
    - `default_roles_map[account] = [roles...]`
    - `role_identifier_set = {...}`
- 在 enrich 的 per-account 循环内，把 `roles` 与 `account_kind` 合并到 `permissions`。

## 快照与派生（permission_snapshot / permission_facts）

### permission_snapshot(v4)

- 需要把 `roles` 作为 categories 的一级字段写入：
  - 修改映射表：`app/services/accounts_sync/permission_manager.py` 中 `_PERMISSION_TO_SNAPSHOT_CATEGORY_KEY` 增加 `"roles": "roles"`。
- `type_specific` 保持按 db_type 分桶写入：
  - `type_specific["mysql"]["account_kind"] = "role"|"user"`

### permission_facts

- `facts_builder` 已支持从 `categories["roles"]` 提取 roles（目前 categories 缺失导致永远为空）。
- 建议把 roles facts 口径改为：
  - `roles = direct + default（去重）`
  - 并保留结构化信息在 snapshot 里供 UI 展示。

## API 输出调整（列表页必需）

### 账户台账列表 `/api/v1/accounts/ledgers`

当前返回项缺少 `type_specific/account_kind`，导致前端无法区分角色。

建议：
- `AccountLedgerItem` 增加 `account_kind` 字段（仅 MySQL 有意义，其他 db_type 固定输出 `"user"`）。
- `ACCOUNT_LEDGER_ITEM_FIELDS` 增加：
  - `account_kind: fields.String`（example: "role"）

数据来源：`AccountPermission.type_specific`（v1 dict）中的 `account_kind`。

> 备注：实例详情页当前也复用了 `/api/v1/accounts/ledgers?instance_id=...`，因此该 API 扩展能同时覆盖“实例详情账户列表”。

## UI 展示调整

### 1) 实例详情账户列表（`instances/detail.js`）

现状：锁定列仅看 `is_locked`，角色全部显示“已锁定”。

设计：
- 增加“类型”列（建议插入到“账户”与“锁定”之间）：
  - `role` → pill: “角色”（info 样式）
  - `user` → pill: “用户”（muted 样式）
- 锁定列展示逻辑调整：
  - 若 `account_kind == role`：显示“不可登录”（info/muted 样式），避免红色告警感。
  - 若 `account_kind == user`：沿用“已锁定/正常”。

### 2) 账户台账页面（`accounts/ledgers.js`）

现状：可用性列同样把 role 视作“已锁定”。

设计：
- 增加“类型”列或在“账户/实例”单元格中加入类型 chip。
- 可用性列同上：role 显示“角色（不可登录）”或“不可登录”。

### 3) 权限弹窗（`permission-modal.js`）

现状：MySQL 权限只展示全局/库级权限。

设计：在 `renderMySQLPermissions()` 增加两个 section：
- “直授角色”：`permissions.roles.direct`
- “默认角色”：`permissions.roles.default`

展示形态：复用 `renderLedgerChips`，空时显示“无角色/无默认角色”。

## 数据回填与上线策略

- 该重构主要影响“同步后写入的快照/事实”。历史数据没有 `account_kind/roles`，展示仍会混乱。
- 上线后需要对 MySQL 实例执行一次权限同步（现有任务即可），以刷新 `type_specific`、`snapshot.categories.roles`。

建议的灰度/回滚：
- 先只加字段与 UI 展示（不改锁定推导口径），观察：
  - 角色是否被正确标注
  - 列表中“已锁定”红色告警是否显著减少
- 如出现误判，可临时降级：
  - UI 仅在 `account_kind == role` 时改变展示；
  - `account_kind` 识别策略可调整为更保守（仅来源于 role_edges/default_roles）。

## 测试建议

- Adapter 单测：
  - 给定 role_edges/default_roles 行，断言输出 `roles.direct/default` 正确。
  - 断言 `account_kind` 判定策略对典型角色（`*_role@%`）生效。
- Service/API 单测：
  - `/api/v1/accounts/ledgers` 返回项包含 `account_kind`，并能被前端消费。
- 前端回归：
  - 实例详情账户列表：角色行显示“角色”，锁定列不再显示红色“已锁定”。
  - 权限弹窗：能看到“直授角色/默认角色”。

