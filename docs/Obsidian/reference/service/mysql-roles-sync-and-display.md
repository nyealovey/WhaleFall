---
title: MySQL Roles 同步与展示(账号/角色/成员)
aliases:
  - mysql-roles-sync
  - mysql-roles-display
  - mysql-account-kind
  - mysql-role-members
  - mysql-default-roles
  - mysql-role-edges
tags:
  - reference
  - reference/service
  - service
  - service/accounts-sync
  - service/accounts-ledgers
  - mysql
  - mysql/roles
status: draft
created: 2026-01-21
updated: 2026-01-21
owner: WhaleFall Team
scope: MySQL 账号同步, 台账展示, 权限详情展示
related:
  - "[[reference/service/accounts-sync-adapters|Accounts Sync Adapters]]"
  - "[[reference/service/accounts-sync-permission-manager|AccountPermissionManager 权限同步]]"
  - "[[reference/service/accounts-ledger-services|Accounts Ledger Services]]"
  - "[[standards/backend/layer/api-layer-standards|API Layer Standards]]"
  - "[[standards/doc/service-layer-documentation-standards]]"
---

# MySQL Roles 同步与展示(账号/角色/成员)

## 1. 背景与目标

### 1.1 背景

- MySQL 8.0 引入内置角色(role), 并通过系统表维护授权关系.
- 账户同步需要把 user 与 role 同时落库, 但在不同页面有不同展示诉求.

### 1.2 目标

- 角色要落库, 且可在实例详情页默认展示.
- 账户台账页默认只展示真实用户(不展示 MySQL role), 但不删除角色数据.
- 权限详情(查看 role 的权限)需要额外展示: 该 role 下面包含哪些用户.
- 同步失败不得触发"把远端 0 账户"的误判, 不允许清空既有账户.

### 1.3 非目标

- 本文不覆盖 SQL Server.
- 本文不追求跨 MySQL 兼容实现的 100% 系统表一致性, 仅保证在权限可读时正确展示.

## 2. 数据源(系统表与语义)

### 2.1 账户清单

- MySQL 账户(含 role)来源: `mysql.user`

典型字段:

- `User`, `Host`: 唯一键建议拼为 `user@host`
- `account_locked`: 用户锁定标志(登录态相关)
- `plugin`: 认证插件
- `password_last_changed`: 口令变更时间
- `is_role`: 标识该记录是否为 role(部分兼容实现可能缺失)

### 2.2 角色关系

- 直授角色: `mysql.role_edges`
  - `FROM_USER@FROM_HOST` 是被授予的 role
  - `TO_USER@TO_HOST` 是被授予者(grantee)
- 默认角色: `mysql.default_roles`
  - `DEFAULT_ROLE_USER@DEFAULT_ROLE_HOST` 是默认 role
  - `USER@HOST` 是被授予者(grantee)

## 3. 从采集到落库: 端到端数据流

## 3.1 入口与阶段

- 入口: `AccountSyncService` -> `AccountSyncCoordinator`
- 两阶段:
  - Inventory: 维护 `InstanceAccount`(账号清单)
  - Collection: 维护 `AccountPermission` + `AccountChangeLog`(权限快照与变更)

关键约束:

- "获取远端账户列表"失败时必须 fail-fast, 终止本次同步.
- 不允许在远端查询失败时返回空列表, 否则 Inventory 会把全部账号误判为远端已删除并 deactivated.

## 3.2 MySQLAccountAdapter: 账户清单采集

### 3.2.1 supports_roles 的内部判定

- 使用实例已采集的版本字段(`instance.main_version` 等)做内部判断.
- MySQL 5.7: 不支持 roles.
- MySQL 8.0+: 支持 roles.
- MariaDB: 即使走 MySQL 类型也不按 MySQL 8 角色表路径处理.

### 3.2.2 拉取 mysql.user

- 首选带 `is_role` 列的查询.
- 若出现 `Unknown column 'is_role'`, 则回退为不选 `is_role`.

当 `is_role` 缺失时的角色推断:

- 通过 `mysql.role_edges` + `mysql.default_roles` 汇总"被授予过的角色集合".
- 仅把出现在该集合中的账号标为 `role`.
- 未被使用(未出现在关系表)且 `is_role` 缺失时, 无法可靠区分, 会被当作 `user`(符合"未使用角色等于无效角色"的约束).

### 3.2.3 归一化与 type_specific

- 唯一用户名: `username = f"{User}@{Host}"`
- MySQL 专属信息写入 `permissions.type_specific`, 同时在 Permission Manager 写入 `AccountPermission.type_specific`:
  - `account_kind`: `user` | `role`
  - `plugin`
  - `account_locked`
  - `password_last_changed`
  - `host`, `original_username`

锁定态约定:

- `account_kind=user`: `is_locked` 由 `account_locked` 推导.
- `account_kind=role`: 角色不可登录, UI 锁定列展示 `-`(不把 role 当作锁定账号).

## 3.3 MySQLAccountAdapter: 权限采集(enrich_permissions)

对目标用户执行:

- `SHOW GRANTS FOR user@host` -> 解析全局权限与库级权限.
- `mysql.user`(where user/host) -> 补齐 `plugin`, `account_locked`, `password_last_changed` 等属性.
- 角色信息:
  - `mysql_granted_roles`: `{direct: [...], default: [...]}`
  - `mysql_role_members`(仅 role 才有): `{direct: [...], default: [...]}`

`mysql_role_members` 的构造:

- 全量拉取 `role_edges/default_roles` 后在内存中做映射反转.
- direct: role_edges 中 `role -> [user]`
- default: default_roles 中 `role -> [user]`

## 3.4 Permission Manager: v4 snapshot 分类

- `AccountPermissionManager` 负责把 `permissions` 写入 `permission_snapshot`(version=4).
- MySQL 相关 categories:
  - `mysql_granted_roles`
  - `mysql_role_members`
  - `mysql_global_privileges`
  - `mysql_database_privileges`

## 4. 从落库到展示: 页面与 API

## 4.1 API: /api/v1/accounts/ledgers

- 默认 `include_roles=false`.
- 过滤逻辑基于 `AccountPermission.type_specific.account_kind`:
  - `db_type=mysql` 且 `account_kind=role` -> 默认过滤掉.
  - `include_roles=true` -> 不过滤.

## 4.2 实例详情页: 默认展示 role

- 实例详情页账户 grid 调用:
  - `/api/v1/accounts/ledgers?instance_id=...&include_roles=true`
- MySQL 额外列:
  - 账户
  - 插件
  - 类型(`user`/`role`)
  - 锁定
  - 超管
  - 删除
  - 最后变更

## 4.3 权限详情弹窗: role 显示成员

- 权限详情 API:
  - `/api/v1/accounts/ledgers/<account_id>/permissions`
- 前端基于 v4 snapshot.categories 渲染 MySQL:
  - 直授角色
  - 默认角色
  - 包含用户(仅当 snapshot.categories.mysql_role_members 存在)
  - 全局权限
  - 数据库权限
  - 表权限(若存在)

## 5. 失败语义与安全性

- 远端查询失败:
  - 必须抛异常, 由上层返回同步失败.
  - 严禁返回空账号列表作为"降级".
- 远端查询成功但远端确实无账号:
  - Inventory 允许把本地账号 deactivated.

## 6. 验证清单

- 单元测试:
  - `uv run pytest -m unit tests/unit/services/accounts_sync/test_mysql_adapter_roles.py`
- 静态检查:
  - `uv run ruff check ...`
  - `make typecheck`
  - `./scripts/ci/eslint-report.sh quick`
