# `permissions.type_specific` 重构与约束说明

## 目标与范围

本方案聚焦于 `AccountPermission.permissions.type_specific` 字段的维护规范，要求：

- **保持现有字段结构不变**：各数据库已经写入的键名继续沿用，避免破坏现有数据与前端解析。
- **严禁写入权限信息**：任何可映射到授权列表（GRANT/REVOKE）的数据都应放入 `global_privileges`、`database_privileges` 等专用字段，而不是 `type_specific`。
- **尽可能保存身份/状态信息**：使用当前字段承载账号本身的元数据（锁定状态、默认表空间、认证插件等），为差异比对与展示提供上下文。

## 核心信息要求

所有数据库的 `type_specific` 至少应包含以下几类账号核心状态：

1. **登录控制**：是否允许登录（如 `can_login`、`is_disabled` 等布尔字段）。
2. **锁定信息**：账户是否锁定及锁定原因（如 `is_locked`、`account_status`）。
3. **密码生命周期**：密码上次修改时间，若数据库不提供则写 `None`。
4. **特殊授权能力**：数据库原生提供的全局能力开关（例如 MySQL 的 `can_grant`、PostgreSQL 的 `can_create_db`、SQL Server 的 `is_disabled`）。这些属于账户级特殊权限，仍保留在 `type_specific` 方便展示和差异比对，但不得混入对象级授权列表。

## 通用约束

1. `type_specific` 仅用于**账号属性**或**状态补充**，不得出现权限枚举、对象路径等授权信息。
2. 所有布尔字段统一使用布尔类型；状态字符串保持数据库原语义的大写英文或原始描述。
3. 缺失值使用 `None` 或空字符串，避免混淆 `False/0` 的语义。
4. 历史遗留权限内容（如 MySQL 的 `grant_statements`）只保留已有字段，不再新增类似条目；如需诊断日志，另行存储。

## 各数据库字段映射（保持现状）

### MySQL
| 字段 | 说明 | 来源 |
| --- | --- | --- |
| `host` | 账户原始 Host | `mysql.user.Host` |
| `original_username` | 未拼接 Host 的用户名 | `mysql.user.User` |
| `is_locked` | 账户是否锁定 | `mysql.user.account_locked` |
| `plugin` | 认证插件 | `mysql.user.plugin` |
| `password_last_changed` | 密码最近修改时间（ISO 字符串） | `mysql.user.password_last_changed` |
| `can_grant` | 是否允许授权 | `mysql.user.Grant_priv` |
| `grant_statements` | `SHOW GRANTS` 原始语句数组（保留既有字段，不再扩展） | 采集阶段 |

> 调整建议：`grant_statements` 仅用于排障，写入日志前确保不会被差异逻辑识别为权限；禁止新增权限相关字段到 `type_specific`。

### PostgreSQL
| 字段 | 说明 | 来源 |
| --- | --- | --- |
| `can_create_role` | 是否可创建角色 | `pg_roles.rolcreaterole` |
| `can_create_db` | 是否可创建数据库 | `pg_roles.rolcreatedb` |
| `can_replicate` | 是否允许复制 | `pg_roles.rolreplication` |
| `can_bypass_rls` | 是否可绕过 RLS | `pg_roles.rolbypassrls` |
| `can_login` | 是否允许登录 | `pg_roles.rolcanlogin` |
| `can_inherit` | 是否继承权限 | `pg_roles.rolinherit` |
| `valid_until` | 账号有效期（ISO 字符串） | `pg_roles.rolvaliduntil` |

> 注意：上述字段表示角色属性（特殊权限开关），但不涉及对象级授权；应继续留在 `type_specific` 中用于展示账号状态。禁止将数据库/表授权写入此处。

### SQL Server
| 字段 | 说明 | 来源 |
| --- | --- | --- |
| `is_disabled` | 登录是否禁用 | `sys.server_principals.is_disabled` |

> 保持单一布尔字段。若未来需要扩展（例如锁定原因），可新增 `locked_reason` 等账号状态信息。特殊权限（如其它服务器级开关）允许写入 `type_specific`，但不要引入对象级授权列表。

### Oracle
| 字段 | 说明 | 来源 |
| --- | --- | --- |
| `account_status` | 账户状态（OPEN/LOCKED 等） | `DBA_USERS.account_status` |
| `default_tablespace` | 默认表空间 | `DBA_USERS.default_tablespace` |

> 这些字段属于账号元数据，可继续存储；严禁写入角色或系统权限列表。

## 差异计算与日志要求

- 权限管理器在写入 `AccountChangeLog` 时，将 `type_specific` 视作“非权限差异”，统一落入 `other_diff`。
- 保持摘要逻辑只读取现有字段，避免因为新增键导致描述混乱。
- 若 `type_specific` 中字段调整（新增/删除），必须更新文档并说明用途，确保前后端同步知晓。

## 数据填充与清理建议

1. **新增账户**：同步时应完整填充上述字段；暂无值时写 `None`。
2. **补齐缺失字段**：对于历史数据，可借助同步任务自动带出；必要时运行一次全量同步刷新。
3. **清理权限噪音**：若发现 `type_specific` 已包含权限列表（例如历史自研字段），优先迁移/删除，避免继续传播。

## 后续步骤（可选）

- 编写校验脚本，在同步结束后扫描 `type_specific` ，确保不存在命名为 `privileges`、`roles` 等的字段。
- 前端展示时根据本文档字段说明，统一呈现账号属性（锁定状态、认证方式等），增强可读性。
- 若未来需要扩展新数据库或属性，请在本文件中补充说明，并保持“非权限”这一核心约束。

通过上述约束，各数据库 `type_specific` 既能保留必要的账号特征，又能避免与权限差异混淆，便于后续维护和扩展。***
