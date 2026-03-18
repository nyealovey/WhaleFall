---
title: 外部数据库账号权限要求(监控/同步)
aliases:
  - database-permissions-overview
tags:
  - reference
  - reference/database
status: active
created: 2025-09-08
updated: 2026-03-18
owner: WhaleFall Team
scope: 外部数据库实例只读账号(连接测试/账户同步/容量采集/审计配置读取)
related:
  - "[[reference/database/README|数据库参考]]"
  - "[[reference/database/database-drivers]]"
  - "[[reference/config/environment-variables]]"
---

# 外部数据库账号权限要求(监控/同步)

> [!info] Purpose
> WhaleFall 需要在外部数据库上执行 "元数据读取/权限快照采集/容量查询/审计配置读取" 等只读操作. 本文给出推荐脚本与访问对象范围(以实际代码查询为准).

> [!info] SSOT
> 推荐初始化脚本位于 `sql/ops/monitor-user/*.sql`, 以脚本为准.

## 推荐脚本与访问对象(示例)

| 数据库 | 推荐脚本(SSOT) | 主要访问对象(示例) | 主要用途 |
| --- | --- | --- | --- |
| MySQL | `sql/ops/monitor-user/setup_mysql_monitor_user.sql` | `mysql.user`, `SHOW GRANTS`, `information_schema.*` | 账户同步(账号/权限)与容量/台账查询 |
| PostgreSQL | `sql/ops/monitor-user/setup_postgresql_monitor_user.sql` | `pg_roles`, `pg_auth_members`, `pg_database`, `pg_tablespace` | 账户同步(角色/属性/权限函数)与元数据读取 |
| SQL Server | `sql/ops/monitor-user/setup_sqlserver_monitor_user.sql` | `sys.server_principals`, `sys.server_permissions`, `sys.databases`, `sys.database_principals`, `sys.server_audits`, `sys.server_audit_specifications`, `sys.database_audit_specifications` | 账户同步(登录/角色/权限)、跨库元数据读取与审计信息页(catalog) |
| Oracle | `sql/ops/monitor-user/setup_oracle_monitor_user.sql` | `dba_users`, `dba_roles`, `dba_role_privs`, `dba_sys_privs`, `dba_ts_quotas` | 账户同步(用户/角色/系统权限/表空间配额) |

## 默认值与约束

- 原则: 最小权限 + 只读账号. 生产环境建议创建专用 `monitor_user`(或等价账号), 避免使用 DBA/SA 等高权限账号.
- 账号权限需要覆盖两类调用:
  - 连接测试: 获取版本, 校验连通性(见 `app/services/connection_adapters/**`)
  - 同步/采集: 读取系统目录/视图/权限信息(见 `app/services/accounts_sync/adapters/**`, `app/services/database_sync/**`, `app/services/config_sync/**`)
- SQL Server 的 "跨数据库查询" 依赖服务器级权限(脚本已包含 `VIEW ANY DATABASE` 等); 如你限制该权限, 会导致跨库的账号/权限枚举失败.

## SQL Server: 审计信息页(首期)权限口径

> [!note]
> WhaleFall 当前 `实例详情 -> 审计信息` 首期只读取 SQL Server catalog 元数据, 不读取审计文件内容, 也不依赖运行时审计状态 DMV.

- 当前页面读取对象:
  - `sys.server_audits`
  - `sys.server_file_audits`
  - `sys.server_audit_specifications`
  - `sys.server_audit_specification_details`
  - `sys.database_audit_specifications`
  - `sys.database_audit_specification_details`
- 当前实现对应的最小权限说明:
  - `VIEW ANY DEFINITION`: 读取服务器级 audit / audit specification 元数据
  - `VIEW ANY DATABASE`: 枚举可见数据库, 用于遍历数据库级 audit specification
  - 每个数据库内的 `VIEW DEFINITION`: 读取各库内的数据库级 audit specification / details
- 当前实现**不以**以下能力为前提:
  - `sys.dm_server_audit_status`
  - `sys.fn_get_audit_file`
- 因此, `VIEW SERVER STATE` 在当前 WhaleFall 审计信息页里不是读取 audit catalog 的必要前提；若脚本中仍保留该权限, 主要是为了兼容既有监控或后续扩展查询.

## 示例

### 1) 创建/授权监控账号(推荐: 直接运行脚本)

> [!warning]
> 脚本内的默认口令为占位符, 必须替换为强密码.
> 并建议把 `%`(MySQL)等放宽范围收敛为可信网段/来源.

```bash
# MySQL
mysql -u root -p < sql/ops/monitor-user/setup_mysql_monitor_user.sql

# PostgreSQL
psql -U postgres -d postgres -f sql/ops/monitor-user/setup_postgresql_monitor_user.sql

# SQL Server(示例: sqlcmd)
sqlcmd -S server -U sa -P password -i sql/ops/monitor-user/setup_sqlserver_monitor_user.sql

# Oracle(示例: sqlplus/sysdba)
sqlplus sys/password@database as sysdba @sql/ops/monitor-user/setup_oracle_monitor_user.sql
```

### 2) 在 WhaleFall 中配置外部实例

- 用户名: 建议使用脚本创建的 `monitor_user`(或你的等价只读账号)
- 密码: 强密码(由部署系统/凭据管理注入; 不要写进仓库)
- 主机/端口/服务名: 按实例实际配置填写(Oracle 的 `service_name` 对应 WhaleFall 的 `database_name`)

## 版本/兼容性说明

- MySQL 权限模型在不同大版本上差异较大; 推荐以脚本作为可运行基线, 并在收敛权限前以实际查询语句为准做回归验证.
- SQL Server 脚本包含 "为新数据库自动授予权限" 的触发器逻辑(便利但具侵入性); 如组织策略不允许, 请移除触发器并改为流程化授予(同时接受新库无法自动同步的现实约束).
- SQL Server 审计信息页首期仅读取 catalog; 若未来要接入 `sys.dm_server_audit_status` 或 `sys.fn_get_audit_file`, 需要重新评估权限并同步更新脚本与本文.
- Oracle 侧查询主要依赖 `DBA_*` 视图; 如目标环境限制访问 `DBA_*`, 需要改造为 `ALL_*`/`USER_*` 视图并同步更新适配器实现.

## 常见错误

- 同步报 "权限不足/对象不存在": 优先检查是否按对应数据库脚本完成授权; 再根据错误定位具体缺失视图/权限.
- SQL Server 跨库查询失败: 检查 `VIEW ANY DATABASE` 与数据库级 `VIEW DEFINITION` 是否授予; 以及新库是否已创建对应用户映射.
- SQL Server 审计信息页为空/报权限不足: 先检查 `VIEW ANY DEFINITION`、`VIEW ANY DATABASE` 与数据库级 `VIEW DEFINITION`; 再确认目标实例确实已配置 server audit / audit specification.
- Oracle 账号状态非 `OPEN`: 同步会将其视为锁定; 需要在数据库侧解锁或调整筛选规则.
