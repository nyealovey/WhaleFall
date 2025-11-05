# `permissions.type_specific` 字段统一重构方案

## 背景

`type_specific` 字段用于补充不同数据库账号在权限之外的原生属性，例如 MySQL 的 `host`、PostgreSQL 的 `can_login` 等。随着适配器演进，各数据库写入的内容逐渐分散，字段命名和语义差异较大，给前端展示、日志分析以及差异比对带来额外成本。本方案旨在梳理当前实现，提出统一约束，让各数据库的 `type_specific` 差异保持在最小范围。

## 当前实现分析

| 数据库 | 字段 | 含义 | 来源位置 |
| --- | --- | --- | --- |
| MySQL | `host` | 原始 Host | `mysql.user.Host` |
|  | `original_username` | 原始用户名（未拼 host） | 同上 |
|  | `is_locked` | 账户是否锁定 (`account_locked`) | `mysql.user.account_locked` |
|  | `plugin` | 认证插件 | `mysql.user.plugin` |
|  | `password_last_changed` | 密码修改时间 | `mysql.user.password_last_changed` |
|  | `can_grant` | 是否允许授权 | `mysql.user.Grant_priv` |
|  | `grant_statements` | `SHOW GRANTS` 原始语句数组 | 采集阶段 |
| PostgreSQL | `can_create_role` | 可创建角色 | `pg_roles.rolcreaterole` |
|  | `can_create_db` | 可创建数据库 | `pg_roles.rolcreatedb` |
|  | `can_replicate` | 可启用复制 | `pg_roles.rolreplication` |
|  | `can_bypass_rls` | 可绕过 RLS | `pg_roles.rolbypassrls` |
|  | `can_login` | 是否允许登陆 | `pg_roles.rolcanlogin` |
|  | `can_inherit` | 是否继承权限 | `pg_roles.rolinherit` |
|  | `valid_until` | 账号有效期 | `pg_roles.rolvaliduntil` |
| SQL Server | `is_disabled` | 登录是否禁用 | `sys.server_principals.is_disabled` |
| Oracle | `account_status` | 账户状态 (`OPEN/LOCKED`) | `DBA_USERS` |
|  | `default_tablespace` | 默认表空间 | `DBA_USERS.default_tablespace` |

### 存在的问题
1. **字段命名分散**：同类语义在不同数据库使用不同名称（如登录能力 `can_login / is_disabled / is_locked`）。
2. **非结构化信息**：MySQL 写入 `grant_statements` 字符串数组，与权限差异逻辑重复，建议剥离。
3. **缺乏统一数据类型**：布尔值、状态值的表示不一致（`OPEN` vs `True/False`）。
4. **扩展策略不清晰**：未来新增信息缺少规范，容易再次出现各自为政的情况。

## 统一设计目标
1. **核心字段对齐**：保障各数据库至少提供同一组核心信息，便于前端统一展示。
2. **类型明确**：布尔值统一使用布尔型，状态枚举统一使用大写英文或统一中文描述。
3. **扩展区隔**：预留 `extras` 作为数据库特有扩展字段，避免混入非核心字段。
4. **禁用权限相关内容**：`type_specific` 只存储“身份属性”，不记录授权/权限列表（这些归属于 `privilege_diff` 逻辑）。

## 建议的标准结构

```json
{
  "login_control": {
    "can_login": true,           // 是否允许登录（MySQL、PostgreSQL、Oracle、SQLServer 通用）
    "locked_reason": ""          // 锁定原因/状态，若无则为空字符串
  },
  "identity": {
    "origin": "user@host",       // 原始用户名（MySQL 专用，其他数据库可为空）
    "auth_plugin": "mysql_native_password"  // 认证插件，如不适用则为空
  },
  "lifecycle": {
    "password_last_changed": "2025-11-01T10:00:00Z",  // 密码修改时间，不适用则为空
    "valid_until": "2026-01-01T00:00:00Z"             // PostgreSQL 等有有效期限制的数据库可填
  },
  "resource": {
    "default_tablespace": "USERS"  // Oracle 专用，其他数据库为空
  }
}

### 字段说明

#### 核心字段（所有数据库必须提供）
- **`login_control.can_login`**：统一布尔值，表示账户是否允许登录
  - MySQL：`not is_locked`（基于 `account_locked` 字段）
  - PostgreSQL：直接使用 `rolcanlogin`
  - SQL Server：`not is_disabled`（基于 `is_disabled` 字段）
  - Oracle：`account_status.upper() == "OPEN"`

- **`login_control.locked_reason`**：锁定原因的原始状态描述
  - MySQL：`is_locked` 为 true 时填入 `"LOCKED"`，否则为空
  - PostgreSQL：`can_login` 为 false 时填入 `"LOGIN_DISABLED"`，否则为空
  - SQL Server：`is_disabled` 为 true 时填入 `"DISABLED"`，否则为空
  - Oracle：`account_status` 不为 `"OPEN"` 时填入原始状态值（如 `"LOCKED"`、`"EXPIRED"`），否则为空

#### 身份标识字段
- **`identity.origin`**：原始用户标识
  - MySQL：`{original_username}@{host}` 格式
  - 其他数据库：保持为空字符串

- **`identity.auth_plugin`**：认证插件信息
  - MySQL：填入 `plugin` 字段值
  - 其他数据库：保持为空字符串

#### 生命周期字段
- **`lifecycle.password_last_changed`**：密码最后修改时间
  - MySQL：使用 `password_last_changed` 字段，转换为 ISO 格式
  - 其他数据库：暂时为空，后续可扩展

- **`lifecycle.valid_until`**：账户有效期
  - PostgreSQL：使用 `rolvaliduntil` 字段，转换为 ISO 格式
  - 其他数据库：保持为空

#### 资源配置字段
- **`resource.default_table

## 各数据库字段映射建议

| 数据库 | 当前字段 | 统一后归属 | 说明 |
| --- | --- | --- | --- |
| MySQL | `is_locked` | `login_control.can_login` + `locked_reason` | `can_login = not is_locked`；`locked_reason = "LOCKED"` |
|  | `original_username` | `identity.origin` | 组合为 `f"{original_username}@{host}"` 或在 `extras` 保留分段；根据需求决定 |
|  | `host` | `identity.origin` 或 `extras.host` | 为避免丢失 host，可放入 `extras.host` |
|  | `plugin` | `identity.auth_plugin` | 直接拷贝 |
|  | `password_last_changed` | `lifecycle.password_last_changed` | ISO 格式 |
|  | `can_grant` | `extras.can_grant` | 权限相关开关，放 extras |
|  | `grant_statements` | **废除**或迁移至诊断日志 | 不再保存在 `type_specific` |
| PostgreSQL | `can_login` | `login_control.can_login` | 维持布尔值 |
|  | `valid_until` | `lifecycle.valid_until` | 已是 datetime |
|  | 其他 `can_*` 字段 | `extras.*` | 如 `extras.can_create_db` |
| SQL Server | `is_disabled` | `login_control.can_login` + `extras.is_disabled` | `can_login = not is_disabled`；保留原值在 extras |
| Oracle | `account_status` | `login_control.can_login` + `locked_reason` | `can_login = (account_status.upper() == "OPEN")`；`locked_reason = account_status` |
|  | `default_tablespace` | `resource.default_tablespace` | 保留表空间信息 |

> 注：若某数据库不存在对应值，统一使用 `None`/空字符串，避免混入 `False` 导致误判。

## 实施步骤

1. **定义统一结构**：在 `permission_manager` 中新增工具函数，对旧结构进行迁移和兜底，确保写入日志前即转换完成。
2. **更新各适配器**：
   - MySQL/PG/SQLServer/Oracle 的 `_normalize_account` 及权限采集阶段统一调用 `build_type_specific_payload()`。
   - 移除 `grant_statements` 等诊断性字段，若需要保留，可在日志模块另存。
3. **同步差异处理**：
   - `type_specific` 在 diff 计算时以新结构对比，保留到 `other_diff`。
   - 空字段统一清理（不写入 `None`/空集合）。
4. **前端适配**：
   - 修改账户详情/历史界面，针对统一结构展示核心信息（登录状态、锁定原因、有效期等）。
5. **数据迁移**（可选）：
   - 对历史 `account_permission` / `account_change_log` 表中旧格式数据做一次离线脚本迁移，使存量数据符合新结构。

## 验证要点

1. **单实例回归**：针对 MySQL/PG/SQLServer/Oracle 各选一个实例执行同步，检查生成的 `account_permission.type_specific` 与 `account_change_log.other_diff` 内容符合新结构。
2. **日志检查**：确认 `message` 摘要未引用已移除字段（如 `grant_statements`）。
3. **前端展示**：账户变更历史和详情页能正确显示 `can_login`、锁定原因等信息。
4. **差异对比**：运行一次账户 diff，验证 `privilege_diff` 未受到影响。

## 后续维护建议

- 新增数据库或补充新字段时，优先判断是否属于现有分类（`login_control`、`identity`、`lifecycle`、`resource`、`extras`）。
- 统一在文档（本文件）登记新增字段的用途与数据类型。
- 定期复查 `type_specific` 内容，避免再次混入权限列表或诊断信息。

通过该方案，各数据库的 `type_specific` 结构将保持最大程度一致，降低前后端处理成本，并让权限差异与账户属性差异的界限更加清晰。
