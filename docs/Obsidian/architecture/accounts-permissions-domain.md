---
title: Accounts + Permissions domain
aliases:
  - accounts-permissions-domain
tags:
  - architecture
  - architecture/domain
  - domain/accounts
  - domain/permissions
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: accounts sync, permission snapshot(v4), canonical schema, change log, 以及与分类/会话的边界
related:
  - "[[architecture/flows/accounts-sync]]"
  - "[[architecture/flows/sync-session]]"
  - "[[architecture/flows/auto-classify]]"
  - "[[canvas/accounts/accounts-domain-components.canvas]]"
  - "[[canvas/accounts/accounts-flow.canvas]]"
  - "[[canvas/accounts/accounts-sequence.canvas]]"
  - "[[canvas/accounts/accounts-session-sequence.canvas]]"
  - "[[canvas/accounts/accounts-state-machine.canvas]]"
  - "[[canvas/accounts/accounts-erd.canvas]]"
  - "[[canvas/cross-cutting-capabilities.canvas]]"
---

# Accounts + Permissions domain

## 边界与职责

- Accounts sync: 从外部 DB 拉取账号清单与权限, 归一化为 canonical schema, 并落库为快照与变更日志.
- Permission snapshot: 当前以 v4 为主, 是分类(auto-classify)的上游依赖.
- Change log: 记录账号权限变化, 为审计与排障提供可追踪证据.

## 与其他域的关系

- Instances: 提供 instance 元数据与 db_type, 作为 sync 的输入.
- Credentials + Connections: 提供连接能力与 adapter 基础.
- SyncSession: 批量异步能力的统一观测面.
- Classification: 依赖 permission snapshot/facts.

## 代码落点(常用)

- Services:
  - `app/services/accounts_sync/**`
  - `app/services/accounts_permissions/**`
- Canonical types(SSOT):
  - `app/types/accounts.py`
- Models:
  - `app/models/instance_account.py` (`instance_accounts`)
  - `app/models/account_permission.py` (`account_permission`)
  - `app/models/account_change_log.py` (`account_change_log`)

## 图(Canvas)

- Domain components: [[canvas/accounts/accounts-domain-components.canvas]]
- Flow: [[canvas/accounts/accounts-flow.canvas]]
- Sequence(manual single): [[canvas/accounts/accounts-sequence.canvas]]
- Sequence(session mode): [[canvas/accounts/accounts-session-sequence.canvas]]
- State machine: [[canvas/accounts/accounts-state-machine.canvas]]
- ERD: [[canvas/accounts/accounts-erd.canvas]]
- Cross-cutting: [[canvas/cross-cutting-capabilities.canvas]]

> [!tip]
> 当你要新增 db_type 或调整字段归一化, 优先改 adapters 输出 canonical schema, 下游只读 canonical keys.
