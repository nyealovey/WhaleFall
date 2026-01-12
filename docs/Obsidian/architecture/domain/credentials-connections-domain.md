---
title: Credentials + Connections domain
aliases:
  - credentials-connections-domain
tags:
  - architecture
  - architecture/domain
  - domain/credentials
  - domain/connections
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: credential 存储, connection test, 以及 connection adapter 边界
related:
  - "[[API/credentials-api-contract]]"
  - "[[API/instances-api-contract]]"
  - "[[architecture/flows/capacity-sync]]"
  - "[[architecture/flows/accounts-sync]]"
  - "[[canvas/credentials/credentials-connection-domain-components.canvas]]"
  - "[[canvas/credentials/credentials-connection-flow.canvas]]"
  - "[[canvas/credentials/credentials-connection-sequence.canvas]]"
  - "[[canvas/credentials/credentials-connection-state-machine.canvas]]"
  - "[[canvas/credentials/credentials-connection-erd.canvas]]"
---

# Credentials + Connections domain

## 边界与职责

- Credentials: 管理连接凭据(加密存储, 生命周期).
- Connections: 对外部数据库做 connection test, 以及为 accounts sync / capacity sync 提供连接能力.
- Adapters: 屏蔽不同 db_type 的连接差异, 对上游提供统一的 `DatabaseConnection`.

## 代码落点(常用)

- Credentials:
  - API: `app/api/v1/namespaces/credentials.py`
  - service: `app/services/credentials/credential_write_service.py`
- Connection test:
  - service: `app/services/connection_adapters/connection_test_service.py`
- Connection adapters:
  - factory: `app/services/connection_adapters/connection_factory.py`
  - adapters: `app/services/connection_adapters/adapters/**`

## 图(Canvas)

- Domain components: [[canvas/credentials/credentials-connection-domain-components.canvas]]
- Flow: [[canvas/credentials/credentials-connection-flow.canvas]]
- Sequence: [[canvas/credentials/credentials-connection-sequence.canvas]]
- State machine: [[canvas/credentials/credentials-connection-state-machine.canvas]]
- ERD: [[canvas/credentials/credentials-connection-erd.canvas]]

> [!tip]
> accounts/capacity 的 coordinator 都会走 ConnectionFactory, 排障时优先从 connection test 与 adapter 日志入手.
