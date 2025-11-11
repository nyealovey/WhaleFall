# 数据库账户锁定与超级管理员处理规范

> 目的：统一 MySQL / PostgreSQL / SQL Server / Oracle 四类数据库在同步链路中的“账户锁定”与“超级管理员”字段，确保前后端展示一致，排查类似 `dc_group_etl` 被锁但 UI 未显示的问题。

## 1. MySQL

| 维度 | 来源字段 | 处理逻辑 | 存储位置/展示 |
| --- | --- | --- | --- |
| 锁定状态 | `mysql.user.account_locked` (`Y`/`N`) | `account_sync.adapters.mysql_adapter` 在 `_fetch_raw_accounts` 中读取为 `is_locked = account_locked == 'Y'`；`type_specific.is_locked` 同步写入；`is_active = not is_locked`。`AccountPermission.is_locked_display` 直接读取 `type_specific['is_locked']`。实例账户 API `is_locked = is_locked_display or not is_active`，确保真正锁定也能展示锁定标签。 | `AccountPermission.type_specific.is_locked`；`InstanceAccount.is_active` 用于删除/活跃状态。前端列表依赖 `is_locked_display`。 |
| 超级管理员 | `mysql.user.Super_priv` (`Y`/`N`) | 同一查询中写入 `is_superuser = (Super_priv == 'Y')`，通过 `PermissionManager` 存入 `AccountPermission.is_superuser`。 | `AccountPermission.is_superuser`；页面使用 “超级用户”徽章。 |

补充：MySQL 还同步 `Grant_priv`、`plugin`、`password_last_changed` 等信息放在 `type_specific`，供 UI 使用。

## 2. PostgreSQL

| 维度 | 来源字段 | 处理逻辑 | 存储位置/展示 |
| --- | --- | --- | --- |
| 锁定状态 | `pg_roles.rolcanlogin` 及 `password_valid_until` | `_fetch_raw_accounts` 将 `rolcanlogin` 作为 `type_specific.can_login`；`AccountPermission.is_locked_display` 根据 `not can_login` 判定锁定。若存在 `valid_until` 也同步入 `type_specific`。 | `type_specific.can_login`、`type_specific.valid_until`；UI 展示锁定/即将过期提示。 |
| 超级管理员 | `pg_roles.rolsuper` | 适配器直接输出 `is_superuser = rolsuper`，由 `PermissionManager` 写入模型。 | `AccountPermission.is_superuser`。 |

## 3. SQL Server

| 维度 | 来源字段 | 处理逻辑 | 存储位置/展示 |
| --- | --- | --- | --- |
| 锁定状态 | `sys.sql_logins.is_disabled` / `LOGINPROPERTY` | 适配器在用户列表中读取 `is_disabled` 并写入 `type_specific.is_disabled`；`AccountPermission.is_locked_display` 返回 `type_specific['is_disabled']`。 | `type_specific.is_disabled`；UI 根据 `is_locked_display` 高亮。 |
| 超级管理员 | `sys.server_role_members` 中是否属于 `sysadmin` | 适配器拉取角色时将 `is_sysadmin` 映射到 `is_superuser`。 | `AccountPermission.is_superuser`。 |

## 4. Oracle

| 维度 | 来源字段 | 处理逻辑 | 存储位置/展示 |
| --- | --- | --- | --- |
| 锁定状态 | `DBA_USERS.account_status`（`OPEN`/`LOCKED` 等） | `account_status.upper() != 'OPEN'` 则 `is_locked = True`；写入 `type_specific.account_status`、`type_specific.lock_date` 等。`AccountPermission.is_locked_display` 判断 `account_status`。 | `type_specific.account_status`、`lock_date`、`expiry_date`；前端在实例视图提示“锁定/过期”。 |
| 超级管理员 | `DBA_ROLE_PRIVS` 中是否具备 `DBA` 等关键角色 | 适配器将 `is_dba` 标记为 `is_superuser`。 | `AccountPermission.is_superuser`。 |

## 5. 前后端协同要点

1. **同步阶段**：每个 adapter 都必须填充：
   - `is_locked`（或数据库特定字段）放入 `type_specific`，并根据锁定状态计算 `is_active`。
   - `is_superuser` 布尔值用于 `permission_manager`。
2. **持久化与展示**：
   - `AccountPermission.is_locked_display` 封装所有数据库的判定；新增数据库类型时只需更新该方法。
   - 对外 API（`/instances/<id>/accounts`、`/account/list` 等）必须使用 `is_locked_display`，而不是简单的 `not is_active`。
   - 前端模板统一使用 `account.is_locked_display` 或响应中 `is_locked` 字段，确保与同步逻辑一致。
3. **排查指引**：若发现锁定状态异常，检查流程为：
   1. 数据库中原始字段是否正确（如 `mysql.user.account_locked`）。
   2. 适配器是否写入 `type_specific`。
   3. `AccountPermission` 是否存储该字段。
   4. API 是否使用 `is_locked_display` 转换。
   5. UI 是否依赖正确字段。

该文档可放入 `docs/refactor/account_lock_superuser_handling.md`，并在相关 PR 中引用，确保所有成 员了解四种数据库的处理方式。
