---
title: Accounts Sync Adapters(SQL 分支 + 异常归一化)
aliases:
  - accounts-sync-adapters
  - accounts-sync-adapter
tags:
  - reference
  - reference/service
  - service
  - service/accounts-sync
  - services
  - decision-table
status: draft
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: app/services/accounts_sync/adapters/base_adapter.py
related:
  - "[[reference/service/accounts-sync-overview|Accounts Sync 总览]]"
  - "[[standards/doc/service-layer-documentation-standards]]"
---

# Accounts Sync Adapters(SQL 分支 + 异常归一化)

> [!note] 本文目标
> 以“差异表 + 数据流图”的方式集中描述各数据库适配器的分歧点, 避免为每个 `*Adapter` 重复写文档.

## 1. 概览

Accounts Sync 通过 Adapter 层屏蔽不同数据库的查询差异, 向上游提供统一的 `RemoteAccount` 结构.

- 适配器选择入口: `get_account_adapter(db_type)`
- 统一拉取接口: `BaseAccountAdapter.fetch_remote_accounts(instance, connection) -> list[RemoteAccount]`
- 可选补全接口: `BaseAccountAdapter.enrich_permissions(..., usernames=None) -> list[RemoteAccount]`
  - 默认实现“原样返回”(适用于已在 fetch 阶段填充 permissions 的适配器)
  - SQL Server 等需要按需补权限时重写

### RemoteAccount 约定(摘要)

| 字段 | 说明 |
| --- | --- |
| `username` | 唯一标识(可能含 host) |
| `display_name` | 可选展示名 |
| `is_superuser` / `is_active` | 归一化后的布尔属性 |
| `attributes` | 附加信息(锁定/主机/有效期等) |
| `permissions` | 标准化权限快照(供 PermissionSync 使用) |

## 2. 依赖与边界(Dependencies)

| 类型 | 组件 | 用途 | 失败语义(摘要) |
| --- | --- | --- | --- |
| Caller | `AccountSyncCoordinator` | 调用 adapter 拉取/补全 | adapter 异常通常传播到 coordinator |
| Connection | `ConnectionFactory` | 提供 `connection` | 连接失败 -> coordinator 处理 |
| Adapter | `MySQLAccountAdapter` / `PostgreSQLAccountAdapter` / `SQLServerAccountAdapter` / `OracleAccountAdapter` | SQL 差异承载 | 由各 adapter 自行决定抛异常/返回空 |

## 3. 数据流图(Data Flow)

```mermaid
flowchart LR
    A["ConnectionFactory.create_connection(instance)"] --> B["AccountSyncCoordinator"]
    B --> C["get_account_adapter(instance.db_type)"]
    C --> D["adapter.fetch_remote_accounts()"]
    D --> E["normalize -> RemoteAccount[]"]
    E --> F["adapter.enrich_permissions()(可选)"]
    F --> G["Inventory/Permission Managers"]
```

## 4. 决策表: adapter 选择

| db_type | adapter_cls | 备注 |
| --- | --- | --- |
| `mysql` | `MySQLAccountAdapter` |  |
| `postgresql` | `PostgreSQLAccountAdapter` |  |
| `sqlserver` | `SQLServerAccountAdapter` | 通常需要 `enrich_permissions()` |
| `oracle` | `OracleAccountAdapter` |  |
| 其他 | N/A | `raise ValueError` |

## 5. 差异表

| 适配器 | 权限加载策略 | username 归一化 | 主要异常 | 备注 |
| --- | --- | --- | --- | --- |
| MySQL | `fetch_raw_accounts`: 读 `mysql.user`, 仅 seed `permissions.type_specific`<br>`enrich_permissions`: `SHOW GRANTS` + `mysql.user` -> 生成 `global_privileges/database_privileges` | `user@host` 作为 username; 缺失时从 `username.split("@", 1)` 回填 `type_specific.original_username/host` | 捕获 `MYSQL_ADAPTER_EXCEPTIONS`; 抓取失败 fail-fast 抛异常(避免误清空); enrich 失败追加 `permissions.errors[]` | `GRANT` 解析失败仅 warning; 锁定态主要落在 `type_specific.account_locked`(is_locked 推导在 facts/capabilities 层); MySQL 8.0+ 角色用 `type_specific.account_kind=user|role`, 且缺失 `is_role` 时从 `role_edges/default_roles` 推断 |
| PostgreSQL | `fetch_raw_accounts`: 读 `pg_roles`, seed `role_attributes` + `type_specific.valid_until`<br>`enrich_permissions`: 查询 role attributes / predefined roles / db privileges(块级失败 warn 继续) | `rolname` 原样；`rolvaliduntil` 的 `±infinity` 归一为 NULL；`valid_until` 输出 ISO 字符串 | 捕获 `POSTGRES_ADAPTER_EXCEPTIONS`；抓取失败返回 `[]`；enrich 失败追加 `permissions.errors[]` | 使用 `database_privileges_pg`(历史 key) 供 Permission Manager 归一；`_merge_seed_permissions` 用 `setdefault` 防覆盖 seed 值 |
| SQL Server | `fetch_raw_accounts`: 读 `sys.server_principals` 等, seed `type_specific`(登录策略/禁用/锁定信号)<br>`enrich_permissions`: 批量查询 server roles/permissions + database roles/permissions(OPENJSON + batch, `BATCH_SIZE=20`) | login name 原样；过滤规则支持 LIKE patterns；`connect_to_engine` 统一 upper 且把 `GRANT_WITH_GRANT_OPTION` 归一为 `GRANT` | 捕获 `SQLSERVER_ADAPTER_EXCEPTIONS`(含 `pymssql.Error`/timeout/IO 等)；抓取失败返回 `[]`；enrich 失败追加 `permissions.errors[]` | 锁定/过期/必须改密等信号写入 `type_specific`，最终由 Facts Builder 推导 `LOCKED` capability |
| Oracle | `fetch_raw_accounts`: 读 `dba_users`, seed `type_specific.account_status/default_tablespace`<br>`enrich_permissions`: 逐用户查询 `dba_role_privs/dba_sys_privs` -> `oracle_roles/system_privileges` | username 强制 upper；exclude_users 为空时用 `"''"` 占位避免 SQL 语法错误 | 捕获 `ORACLE_ADAPTER_EXCEPTIONS`(含 `oracledb.Error`)；抓取失败返回 `[]`；enrich 失败追加 `permissions.errors[]` | `is_dba` 以 `username == "SYS"` 推断；LOCKED 判定依赖 `type_specific.account_status`(facts/capabilities 推导) |

## 6. 兼容/防御/回退/适配逻辑

| 位置(文件:行号) | 类型 | 描述 | 触发条件 | 清理条件/期限 |
| --- | --- | --- | --- | --- |
| `app/services/accounts_sync/adapters/factory.py:46` | 防御 | `(db_type or '').lower()` 对空值做归一化 | `db_type` 为空/None | 上游 `Instance.db_type` 强约束后删除 |
| `app/services/accounts_sync/adapters/factory.py:48` | 防御 | 不支持的 `db_type` 直接 `raise ValueError` | `db_type` 不在映射表 | 新增 adapter 或在入口层提前校验 |
| `app/services/accounts_sync/adapters/base_adapter.py:41` | 适配/回退 | `enrich_permissions()` 默认“原样返回”作为降级实现 | adapter 不需要二次补权限 | 明确所有 adapter 都实现 enrich 后可删除默认实现 |
| `app/services/accounts_sync/adapters/mysql_adapter.py:118` | 防御 | `(is_locked_flag or '').upper()` 兼容 DB 返回空值 | `mysql.user.account_locked` 为 None/空值 | DB 字段稳定后删除 |
| `app/services/accounts_sync/adapters/mysql_adapter.py:359` | 兼容 | `type_specific` 缺失时从 `username.split("@", 1)` 回填 user/host | 上游缺少 `type_specific.original_username/host` | RemoteAccount schema 固化后删除兜底 |
| `app/services/accounts_sync/adapters/postgresql_adapter.py:99` | 兼容 | `rolvaliduntil` 的 `±infinity` 映射为 NULL(避免不可解析时间) | 数据库返回 infinity 时间 | 若上游统一时间语义后删除 |
| `app/services/accounts_sync/adapters/postgresql_adapter.py:345` | 防御 | `_merge_seed_permissions` 仅在 seed 有值时 setdefault(避免覆盖新查询结果) | seed 权限携带额外字段 | seed 权限来源收敛后简化 |
| `app/services/accounts_sync/adapters/sqlserver_adapter.py:147` | 兼容 | `connect_to_engine` 值归一化(`GRANT_WITH_GRANT_OPTION` -> `GRANT`) | SQL Server 侧返回扩展状态值 | 若上游只需要 canonical 状态后删除 |
| `app/services/accounts_sync/adapters/sqlserver_adapter.py:396` | 适配 | 将 SQL LIKE 模式编译为 regex(%/_ 支持)用于过滤用户名 | filter_rules 使用 LIKE 语义 | 若统一为正则表达式配置后删除适配层 |
| `app/services/accounts_sync/adapters/oracle_adapter.py:92` | 兼容 | username 强制 upper(Oracle 用户名默认大写) | 上游返回混合大小写 | 明确用户名大小写策略后删除 |
| `app/services/accounts_sync/adapters/oracle_adapter.py:173` | 防御 | exclude_users 为空时 placeholders 使用 `"''"` 兜底避免 NOT IN () | exclude_users 为空 | 改为拼接条件化 SQL 后删除 |

## 7. 可观测性(Logs + Metrics)

- 建议在 adapter 层统一补齐: `db_type`, `instance_id`, `sql_name`(或 query key), `duration_ms`.
- 若 adapter 需要吞掉部分错误(例如单库权限不足), 必须在文档与代码里给出原因与清理条件.

## 8. 测试与验证(Tests)

- `uv run pytest -m unit tests/unit/services/test_sqlserver_adapter_permissions.py`
