# Permission Config Version Tags Refactor Plan

> 状态: Draft
> 负责人: @codex
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: account-classification 规则页面权限配置, `permission_configs` 选项注册表, `/api/v1/accounts/classifications/permissions/<db_type>`
> 关联: `sql/seed/postgresql/permission_configs.sql`, `app/models/permission_config.py`, `app/api/v1/namespaces/accounts_classifications.py`, `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js`, `docs/architecture/spec.md`

> For Codex: REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

## 1. 动机与范围

### 1.1 背景问题

当前规则页面的"权限配置"选项来自 `permission_configs`(种子: `sql/seed/postgresql/permission_configs.sql`), 但该表只存 `db_type + category + permission_name + description`, 没有"版本"维度.

当数据库大版本新增权限项时:

- UI 无法提示该权限是否仅在新版本存在
- 用户可能在低版本实例上配置了不存在的权限项, 导致规则"永不命中"或"语义漂移"

目标是为新增权限项展示一个"版本标识", 示例: SQL Server 2022 新增的固定服务器角色显示 badge "2022".

### 1.2 范围

In scope:

- `permission_configs` 增加"引入版本"字段(用于 UI 展示)
- `/api/v1/accounts/classifications/permissions/<db_type>` 返回该字段
- 规则页面权限选择器展示版本 badge
- 种子数据补齐已知的版本差异(见第 2 节)

Out of scope:

- 不做"按实例版本过滤/隐藏"选项(可作为 Phase 3 可选增强)
- 不改动权限采集快照 schema(参考 `docs/changes/refactor/017-account-permissions-refactor-v4-plan.md`)

## 2. 官方文档审查: 各数据库版本权限差异(与本系统类别对齐)

本节只覆盖本系统 `permission_configs` 已使用的类别:

- MySQL: `global_privileges`, `database_privileges`
- PostgreSQL: `database_privileges`, `predefined_roles`, `role_attributes`
- SQL Server: `server_roles`, `server_permissions`, `database_roles`, `database_privileges`
- Oracle: `roles`, `system_privileges`

### 2.1 SQL Server (2008+)

依据 `docs/architecture/spec.md` 的驱动支持口径, SQL Server 最低支持 2008+.

Microsoft Learn 文档明确指出, SQL Server 2022(16.x)新增 10 个固定服务器角色:

- `##MS_DatabaseConnector##`
- `##MS_LoginManager##`
- `##MS_DatabaseManager##`
- `##MS_ServerStateManager##`
- `##MS_ServerStateReader##`
- `##MS_ServerPerformanceStateReader##`
- `##MS_ServerSecurityStateReader##`
- `##MS_DefinitionReader##`
- `##MS_PerformanceDefinitionReader##`
- `##MS_SecurityDefinitionReader##`

来源:

- Microsoft Learn (SQL Server 2008), "Server-Level Roles": `https://learn.microsoft.com/en-us/previous-versions/sql/sql-server-2008/ms188659(v=sql.100)`
- Microsoft Learn (current), "Server-Level Roles - SQL Server": `https://learn.microsoft.com/en-us/sql/relational-databases/security/authentication-access/server-level-roles?view=sql-server-ver17`

落地规则:

- `db_type=sqlserver`, `category=server_roles` 中, 上述 10 项设置 `introduced_in_major="2022"`
- UI 在角色名右侧展示 badge "2022"

### 2.2 PostgreSQL (11+)

依据 `docs/architecture/spec.md` 的驱动支持口径, PostgreSQL 最低支持 11+.

PostgreSQL 11 文档的 default roles 列表不包含 `pg_read_all_data`, `pg_write_all_data`, `pg_database_owner`, `pg_checkpoint`.

- PostgreSQL 11: `https://www.postgresql.org/docs/11/default-roles.html`

PostgreSQL 14 文档的 predefined roles 列表包含:

- `pg_read_all_data`
- `pg_write_all_data`
- `pg_database_owner`

- PostgreSQL 14: `https://www.postgresql.org/docs/14/predefined-roles.html`

PostgreSQL 15 文档的 predefined roles 新增:

- `pg_checkpoint`

- PostgreSQL 15: `https://www.postgresql.org/docs/15/predefined-roles.html`

落地规则:

- `db_type=postgresql`, `category=predefined_roles` 中:
  - `pg_read_all_data`, `pg_write_all_data`, `pg_database_owner` 设置 `introduced_in_major="14"`
  - `pg_checkpoint` 设置 `introduced_in_major="15"`
  - 其余 predefined roles 视为 11+ 通用项, `introduced_in_major=NULL`

### 2.3 MySQL (5.7+)

依据 `docs/architecture/spec.md` 的驱动支持口径, MySQL 最低支持 5.7+.

MySQL 5.7 的 "Privileges Provided by MySQL" 列表包含 `CREATE TABLESPACE`, 不包含 `CREATE ROLE`/`DROP ROLE` 等角色相关权限.

- MySQL 5.7: `https://dev.mysql.com/doc/refman/5.7/en/privileges-provided.html`

MySQL 8.0 的 "Privileges Provided by MySQL" 列表包含:

- `CREATE ROLE`
- `DROP ROLE`
- 以及大量拆分 `SUPER` 的管理类权限(包含 dynamic privileges)

- MySQL 8.0: `https://dev.mysql.com/doc/refman/8.0/en/privileges-provided.html`

结合当前种子数据 `sql/seed/postgresql/permission_configs.sql`(db_type=mysql, category=global_privileges), 建议将以下权限标记为 MySQL 8.0 引入:

- `APPLICATION_PASSWORD_ADMIN`
- `AUDIT_ABORT_EXEMPT`
- `AUDIT_ADMIN`
- `AUTHENTICATION_POLICY_ADMIN`
- `BACKUP_ADMIN`
- `BINLOG_ADMIN`
- `BINLOG_ENCRYPTION_ADMIN`
- `CLONE_ADMIN`
- `CONNECTION_ADMIN`
- `CREATE ROLE`
- `DROP ROLE`
- `ENCRYPTION_KEY_ADMIN`
- `FIREWALL_EXEMPT`
- `FLUSH_OPTIMIZER_COSTS`
- `FLUSH_STATUS`
- `FLUSH_TABLES`
- `FLUSH_USER_RESOURCES`
- `GROUP_REPLICATION_ADMIN`
- `GROUP_REPLICATION_STREAM`
- `INNODB_REDO_LOG_ARCHIVE`
- `INNODB_REDO_LOG_ENABLE`
- `PASSWORDLESS_USER_ADMIN`
- `PERSIST_RO_VARIABLES_ADMIN`
- `REPLICATION_APPLIER`
- `REPLICATION_SLAVE_ADMIN`
- `RESOURCE_GROUP_ADMIN`
- `RESOURCE_GROUP_USER`
- `ROLE_ADMIN`
- `SENSITIVE_VARIABLES_OBSERVER`
- `SERVICE_CONNECTION_ADMIN`
- `SESSION_VARIABLES_ADMIN`
- `SET_USER_ID`
- `SHOW_ROUTINE`
- `SYSTEM_USER`
- `SYSTEM_VARIABLES_ADMIN`
- `TABLE_ENCRYPTION_ADMIN`
- `TELEMETRY_LOG_ADMIN`
- `XA_RECOVER_ADMIN`

落地规则:

- `db_type=mysql`, `category=global_privileges` 中, 上述项设置 `introduced_in_major="8.0"`
- 其余项(在 5.7 中已存在)视为通用项, `introduced_in_major=NULL`

备注:

- MySQL 5.7/8.0 文档都包含 `PROXY` privilege, 但当前 registry 未包含. 是否纳入需要结合 adapter 采集能力与业务规则需求评估, 避免再次出现"UI 可选但后端永不命中".

### 2.4 Oracle (11g+)

依据 `docs/architecture/spec.md` 的驱动支持口径, Oracle 最低支持 11g+.

Oracle 的 system privileges/roles 规模大, 且官方文档更偏向"权威列表"而非"跨版本差异列表". 为了可维护性, 建议采用如下策略:

- 基线版本: 11g
- 覆盖版本: 11g, 12c, 18c, 19c, 21c (introduced_in_major 分别使用 "12"/"18"/"19"/"21")
- 权限清单来源: 官方在线文档(不导出), 分两类抓取并做 diff:
  - roles: Database Security Guide -> "Configuring Privilege and Role Authorization" -> Table "Oracle Database Predefined Roles"
  - system privileges: SQL Language Reference -> "GRANT" -> Table "System Privileges (Organized by the Database Object Operated Upon)"
- 版本差异判定: 对相邻版本做集合差, 将首次出现的项标记为对应 major 版本.
- 缺失处理: 若某项在任一版本文档中找不到(或仅出现在某些选件/组件文档中), 先保持 `introduced_in_major=NULL`, 并记录到 "unknown" 清单待人工核对.

概念参考:

- Oracle 11g roles: `https://docs.oracle.com/cd/E11882_01/network.112/e36292/authorization.htm`
- Oracle 11g system privileges: `https://docs.oracle.com/cd/E11882_01/server.112/e41084/statements_9013.htm`
- Oracle 12c roles: `https://docs.oracle.com/database/121/DBSEG/authorization.htm`
- Oracle 12c system privileges: `https://docs.oracle.com/database/121/SQLRF/statements_9014.htm`
- Oracle 18c roles: `https://docs.oracle.com/en/database/oracle/oracle-database/18/dbseg/configuring-privilege-and-role-authorization.html`
- Oracle 18c system privileges: `https://docs.oracle.com/en/database/oracle/oracle-database/18/sqlrf/GRANT.html`
- Oracle 19c roles: `https://docs.oracle.com/en/database/oracle/oracle-database/19/dbseg/configuring-privilege-and-role-authorization.html`
- Oracle 19c system privileges: `https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/GRANT.html`
- Oracle 21c roles: `https://docs.oracle.com/en/database/oracle/oracle-database/21/dbseg/configuring-privilege-and-role-authorization.html`
- Oracle 21c system privileges: `https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/GRANT.html`

落地规则(初版):

- Oracle 的 `introduced_in_major` 基于上述在线文档抓取 + diff 结果补齐.
- 已知差异(用于 sanity check):
  - `CDB_DBA`, `PDB_DBA` 在 12c+ roles 文档中出现, 在 11g roles 文档中未出现, 预期 `introduced_in_major="12"`.

## 3. 设计: permission_configs 增加 introduced_in_major

### 3.1 数据模型

`permission_configs` 新增列:

- `introduced_in_major`(varchar(20), nullable)

语义:

- `NULL`: 基线通用项(最低支持版本已存在)
- 非 `NULL`: 首次引入的 major 版本标签, 仅用于 UI 标识和后续可选过滤

示例:

- SQL Server 2022 新固定 server roles: `introduced_in_major="2022"`
- PostgreSQL 14 新 predefined roles: `introduced_in_major="14"`
- MySQL 8.0 新管理类权限: `introduced_in_major="8.0"`

### 3.2 迁移策略

Phase 0 仅加列, 不改变既有逻辑:

1. Alembic migration: `ALTER TABLE permission_configs ADD COLUMN introduced_in_major varchar(20) NULL`
2. 兼容部署: 后端读取时对该字段使用"不存在则忽略"的兼容逻辑, 避免滚动发布期间读写不一致
3. 种子数据更新: `sql/seed/postgresql/permission_configs.sql` 的 INSERT 语句补上该列, 并为已知项赋值

### 3.3 API 输出契约

`GET /api/v1/accounts/classifications/permissions/<db_type>` 每个权限项的结构从:

```json
{"name": "SELECT", "description": "..."}
```

扩展为:

```json
{"name": "SELECT", "description": "...", "introduced_in_major": "2022"}
```

兼容性:

- 旧前端忽略未知字段即可继续工作

### 3.4 前端展示

在 `permission-policy-center.js` 渲染 checkbox label 时:

- 当 `perm.introduced_in_major` 存在, 在权限名右侧追加一个 badge, 文案为该值
- 建议 badge 样式: `badge bg-secondary ms-2`
- 建议 tooltip: `title="Introduced in <major>"`

不改变:

- checkbox value 仍使用 `perm.name`
- 规则表达式的构建逻辑不变(仅展示增强)

## 4. 分阶段计划(可逐步上线)

### Phase 0: schema + API(不改 UI)

Files:

- Add: `migrations/versions/XXXXXXXXXXXX_add_permission_configs_introduced_in_major.py`
- Modify: `app/models/permission_config.py`

Steps:

1. Migration 增加 `introduced_in_major`
2. `PermissionConfig.to_dict()` 和 `get_permissions_by_db_type()` 输出该字段
3. 单测覆盖 API 输出结构(至少断言字段存在, 且默认值为 null)

### Phase 1: 种子数据补齐(已知差异)

Files:

- Modify: `sql/seed/postgresql/permission_configs.sql`

Steps:

1. 为 SQL Server 2022 新 roles 增加配置行, 并设置 `introduced_in_major="2022"`
2. 为 PostgreSQL 14/15 新 roles 设置 `introduced_in_major`
3. 为 MySQL 8.0 新 global privileges 设置 `introduced_in_major="8.0"`
4. 为 Oracle roles/system privileges 基于 11/12/18/19/21 官方在线文档补齐 `introduced_in_major`

### Phase 2: UI badge 展示

Files:

- Modify: `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js`

Steps:

1. 在权限名旁展示 `introduced_in_major` badge
2. 回归验证: 新建/编辑规则流程不受影响

### Phase 3(可选): 按实例版本过滤/提示

动机:

- 仅展示 badge 仍可能误用, 过滤能进一步降低误配置

设计要点:

- 规则是 `db_type` 维度(非单实例维度), 因此比较输入使用"当前环境该 db_type 的最旧实例版本"(floor):
  - 后端基于 `instances` 中启用且未删除的实例, 计算 `min_main_version`
  - `GET /api/v1/accounts/classifications/permissions/<db_type>` 返回 `version_context.min_main_version`
- SQL Server 需要从 `major.minor` 映射到年份(例如 16.0 -> 2022)
  - 映射(按 major): 10 -> 2008, 11 -> 2012, 12 -> 2014, 13 -> 2016, 14 -> 2017, 15 -> 2019, 16 -> 2022
- 过滤策略默认不隐藏, 采用"不可用提示"(disabled + tooltip):
  - 当权限项 `introduced_in_major` > `min_main_version` 时, 若该项未被选中则 disabled
  - 若该项已被选中(编辑旧规则), 保持可勾选以便用户取消, 但仍展示 tooltip 提示兼容风险
- 若无法获得 `min_main_version`(无实例/版本未知/解析失败), 仅展示 badge, 不做禁用

## 5. 兼容/适配/回退策略

- Backward compatible: API 增字段, 不删字段, 前端可灰度上线
- Rollback: 如需回滚, 前端忽略字段即可, 后端保持列存在不影响
- 防止"静默空白": 前端加载失败时保持已有 alert, 同时在后端日志记录缺失 registry 的异常

## 6. 验收指标

- SQL Server 的 10 个新固定 server roles 在 UI 展示 badge "2022"
- PostgreSQL 的 `pg_read_all_data` 等在 UI 展示 badge "14", `pg_checkpoint` 展示 badge "15"
- MySQL 的新增管理类权限在 UI 展示 badge "8.0"
- Oracle 的 `CDB_DBA`/`PDB_DBA` 在 UI 展示 badge "12"(以及其他 11-21 差异项按版本展示)
- 规则创建/编辑的 payload 和 evaluator 行为不变

## 7. 清理计划

- 当 Phase 3 完成并稳定后, 可考虑在 UI 增加"按版本筛选"开关, 并补齐所有 db_type 的版本映射表
- 若后续新增 db_type(例如 Doris), 先确定"最低支持版本"与"版本标签口径", 再落表
