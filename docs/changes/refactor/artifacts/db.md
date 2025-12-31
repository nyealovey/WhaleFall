# 数据库权限/预定义角色变更（可核验版）

> **范围说明**
>
> - 仅保留“能在官方文档/发布说明中直接核验”的条目；每一条“新增/移除/变更”都必须给出来源链接。
> - 如果官方来源只证明“该版本文档中已存在”，而没有明确写“introduced in”，则表述为“在该版本文档中已存在（因此该版本可用）”。
> - 原文件中大量 “无新增”/“某版本新增” 的结论缺少来源，已删除或改写为可核验表述。

---

## Oracle Database

### 变更条目（可核验）

> 注：Oracle 官方将 23 系列命名为 “23ai”。本文在版本列/`introduced_in_major` 统一使用主版本号 `23`。

| 版本 | 类型 | 权限/角色 | 说明 | 官方来源 |
|---|---|---|---|---|
| 11gR2 (11.2) | 行政权限 | `SYSASM` | 用于 ASM 管理的独立行政权限（分离职责）。 | Oracle 11gR2 ASM 文档：<https://docs.oracle.com/cd/E11882_01/server.112/e25494/asm.htm> |
| 12cR1 (12.1) | 行政权限 | `SYSBACKUP` / `SYSDG` / `SYSKM` | 备份恢复 / Data Guard / 密钥管理专用行政权限。 | Oracle 12.1 安全指南（Administrative Privileges）：<https://docs.oracle.com/database/121/DBSEG/authorization.htm> |
| 12cR1 (12.1.0.2) | 对象/系统权限 | `READ` / `READ ANY TABLE` | `READ` 为对象权限；`READ ANY TABLE` 为系统权限。 | Oracle 12.1.0.2 安全指南（READ privileges）：<https://docs.oracle.com/database/121/DBSEG/authorization.htm#DBSEG00511> |
| 21c | 系统权限（+参数） | `ENABLE DIAGNOSTICS`（+ `DIAGNOSTICS_CONTROL` 参数） | 诊断事件设置的授权控制：通过 `ENABLE DIAGNOSTICS` 系统权限进行授权，`DIAGNOSTICS_CONTROL` 为 21c 起可用参数。 | Oracle 21c 参考手册（DIAGNOSTICS_CONTROL / ENABLE DIAGNOSTICS）：<https://docs.oracle.com/en/database/oracle/oracle-database/21/refrn/DIAGNOSTICS_CONTROL.html> |
| 23 | Schema-level 授权 | `SELECT ANY TABLE ON SCHEMA ...` 等 schema privileges | 允许在 schema 维度授予 “ANY” 风格权限，覆盖现有与未来对象（更易做最小权限）。 | Oracle 23ai Blog（schema privileges）：<https://blogs.oracle.com/cloudsecurity/post/oracle-database-23ai-schema-privileges-simplify-access-control> |
| 23 | 系统权限 | `GRANT ANY SCHEMA PRIVILEGE` | 用于在其他 schema 上授予 schema-level 权限。 | Oracle SQL Reference（GRANT，系统权限要求）：<https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/GRANT.html> |
| 23 | 预定义角色 | `DB_DEVELOPER_ROLE` | 面向开发者的预定义角色（权限集合）。 | Oracle 23ai 文档（DB_DEVELOPER_ROLE）：<https://docs.oracle.com/en/database/oracle/oracle-database/23/dbseg/configuring-privilege-and-role-authorization.html#GUID-6FA9C8E1-1B7D-499C-A3C3-EC2B20462A28> |

### 本地核验（示例）

- 行政权限（如 `SYSASM` / `SYSBACKUP`）是否存在/可授权：查看密码文件用户权限列 `V$PWFILE_USERS`（需要相应权限）。
- 系统/对象权限名是否存在：可查询 `SYSTEM_PRIVILEGE_MAP` / `TABLE_PRIVILEGE_MAP`（不同版本可见性略有差异）。
- 角色是否存在：`SELECT role FROM dba_roles WHERE role = 'DB_DEVELOPER_ROLE';`

---

## MySQL

### 变更条目（可核验）

| 版本 | 类型 | 权限 | 说明 | 官方来源 |
|---|---|---|---|---|
| 8.2.0 | 新增 | `SET_ANY_DEFINER` / `ALLOW_NONEXISTENT_DEFINER` | 替代/配合 `SET_USER_ID`，用于更细粒度的 DEFINER 相关控制。 | MySQL 8.2.0 Release Notes：<https://dev.mysql.com/doc/relnotes/mysql/8.2/en/news-8-2-0.html> |
| 8.2.0 | 弃用 | `SET_USER_ID` | 在 8.2.0 中被标记为 deprecated。 | MySQL 8.2.0 Release Notes：<https://dev.mysql.com/doc/relnotes/mysql/8.2/en/news-8-2-0.html> |
| 8.3.0 | 新增 | `TRANSACTION_GTID_TAG` | 新增用于事务 GTID tag 的权限。 | MySQL 8.3.0 Release Notes：<https://dev.mysql.com/doc/relnotes/mysql/8.3/en/news-8-3-0.html> |
| 8.4.0 | 新增 | `OPTIMIZE_LOCAL_TABLE` | 用于 `OPTIMIZE LOCAL TABLE` / `OPTIMIZE NO_WRITE_TO_BINLOG TABLE`。 | MySQL 8.4.0 Release Notes：<https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-0.html> |
| 8.4.0 | 移除 | `SET_USER_ID` | 在 8.4.0 中被移除。 | MySQL 8.4.0 Release Notes：<https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-0.html> |
| 8.4（LTS） | 新增 | `FLUSH_PRIVILEGES` | 引入专用于 `FLUSH PRIVILEGES` 语句的动态权限。 | MySQL 官方博客：<https://dev.mysql.com/blog-archive/introducing-mysql-8-4-lts/> |

### 权限清单参考（不做“引入版本”断言）

- MySQL “Privileges Provided by MySQL”（按具体版本文档核验权限是否存在）：<https://dev.mysql.com/doc/refman/8.0/en/privileges-provided.html>

### 本地核验（示例）

- 查看实例支持的权限：`SHOW PRIVILEGES;`
- 查看动态权限授予情况（全局）：`SELECT * FROM mysql.global_grants;`（需相应权限）
- 核验某个权限是否存在：`SHOW PRIVILEGES LIKE 'OPTIMIZE_LOCAL_TABLE';`

---

## SQL Server

### 变更条目（可核验）

| 版本 | 类型 | 权限/能力 | 说明 | 官方来源 |
|---|---|---|---|---|
| 2016+ | 权限/特性 | `UNMASK` + Dynamic Data Masking | `UNMASK` 用于查看 DDM 屏蔽前的原始数据。 | Microsoft Docs（DDM，适用于 SQL Server 2016+，含 UNMASK 权限说明）：<https://learn.microsoft.com/en-us/sql/relational-databases/security/dynamic-data-masking> |
| 2022 | 权限粒度增强 | Granular `UNMASK` | SQL Server 2022 起，可在 database/schema/table/column 级别授予/回收 `UNMASK`。 | Microsoft Docs（DDM，Granular permissions introduced in SQL Server 2022）：<https://learn.microsoft.com/en-us/sql/relational-databases/security/dynamic-data-masking> |
| 2022 | 新权限域 | Ledger permissions（如 `ENABLE LEDGER` / `VIEW LEDGER CONTENT`） | SQL Server 2022 引入 Ledger；相关权限名见数据库权限清单。 | Microsoft Docs（Database permissions，含 Ledger 权限名）：<https://learn.microsoft.com/en-us/sql/relational-databases/security/permissions-database-engine> |

### 本地核验（示例）

- 查看内置权限名：`SELECT * FROM sys.fn_builtin_permissions('DATABASE') WHERE permission_name LIKE '%UNMASK%';`
- 查看实际授权：`SELECT * FROM sys.database_permissions WHERE permission_name = 'UNMASK';`

---

## PostgreSQL

### 变更条目（可核验）

| 版本 | 类型 | 权限/角色 | 说明 | 官方来源 |
|---|---|---|---|---|
| 11 | 新增预定义角色 | `pg_read_server_files` / `pg_write_server_files` / `pg_execute_server_program` | 用于受控的服务器文件读写与执行程序能力。 | PostgreSQL 11 Release Notes（Security）：<https://www.postgresql.org/docs/release/11.0/> |
| 11 | 预定义角色（存在） | 同上 | 在 11 文档的 predefined roles 中可见。 | PostgreSQL 11 Docs（predefined roles）：<https://www.postgresql.org/docs/11/predefined-roles.html> |
| 14 | 预定义角色（存在） | `pg_read_all_data` / `pg_write_all_data` / `pg_database_owner` | 在 14 文档中已存在（因此 14 可用）。 | PostgreSQL 14 Docs（predefined roles）：<https://www.postgresql.org/docs/14/predefined-roles.html> |
| 15 | 新增预定义角色（存在） | `pg_checkpoint` | 在 15 文档中出现（14 文档未出现）。 | PostgreSQL 15 Docs（predefined roles）：<https://www.postgresql.org/docs/15/predefined-roles.html> |
| 16 | 新增预定义角色（存在） | `pg_create_subscription` / `pg_use_reserved_connections` | 在 16 文档中出现（15 文档未出现）。 | PostgreSQL 16 Docs（predefined roles）：<https://www.postgresql.org/docs/16/predefined-roles.html> |
| 17 | 新增权限 | `MAINTAIN` | 关系对象维护相关权限（在 17 文档中出现；16 权限清单无该项）。 | PostgreSQL 17 Docs（Privileges，含 MAINTAIN）：<https://www.postgresql.org/docs/17/ddl-priv.html> |
| 17 | 新增预定义角色（存在） | `pg_maintain` | 与 `MAINTAIN` 权限配套的预定义角色（在 17 文档中出现；16 无该项）。 | PostgreSQL 17 Docs（predefined roles）：<https://www.postgresql.org/docs/17/predefined-roles.html> |

### 常见误解纠正（可核验）

- PostgreSQL 对 **FOREIGN SERVER** 的权限是 `USAGE`，不是 `EXECUTE`。见 PostgreSQL 17 权限说明（FOREIGN SERVER 属于 `USAGE` 的适用对象）：<https://www.postgresql.org/docs/17/ddl-priv.html>

### 本地核验（示例）

- 预定义角色是否存在：`SELECT rolname FROM pg_roles WHERE rolname = 'pg_maintain';`
- 查看权限清单/授予：psql 中 `\\dp` / `\\du`（或查询 `information_schema.*_privileges`）

---

## 原文件中的主要修正/删除点（概览）

- Oracle 21c：将 `DIAGNOSTICS_CONTROL` 从“系统权限”修正为 **参数**，并补充官方指出的系统权限 `ENABLE DIAGNOSTICS`。
- MySQL：将 `TRANSACTION_GTID_TAG` 的新增版本更正为 8.3.0；补充 8.2.0 引入的 `SET_ANY_DEFINER` / `ALLOW_NONEXISTENT_DEFINER`；补充 8.4.0 新增 `OPTIMIZE_LOCAL_TABLE` 与移除 `SET_USER_ID`。
- SQL Server：删除无法核验且命名不一致的“ADMINISTER DATABASE LEDGER”等说法，改为引用官方权限清单中的 Ledger 权限名。
- PostgreSQL：将 `MAINTAIN` 修正为在 17 文档中出现；将 FOREIGN SERVER 权限从 `EXECUTE` 修正为 `USAGE`。 
