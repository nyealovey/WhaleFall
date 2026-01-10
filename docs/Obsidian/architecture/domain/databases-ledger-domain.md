---
title: Databases ledger domain
aliases:
  - databases-ledger-domain
  - databases-ledger
tags:
  - architecture
  - architecture/domain
  - domain/databases
  - domain/databases-ledger
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 数据库台账(跨实例数据库清单)的查询/导出/表容量快照与刷新, 以及与 capacity/database_sync 的边界
related:
  - "[[architecture/project-structure]]"
  - "[[architecture/flows/capacity-sync]]"
  - "[[API/databases-api-contract]]"
  - "[[reference/service/database-ledger-service]]"
  - "[[reference/service/database-sync-table-sizes]]"
  - "[[reference/errors/message-code-catalog]]"
  - "[[operations/observability-ops]]"
  - "[[canvas/databases-ledger/databases-ledger-domain-components.canvas]]"
  - "[[canvas/databases-ledger/databases-ledger-flow.canvas]]"
---

# Databases ledger domain

## 边界与职责

- 提供"数据库台账"视图: 以 `InstanceDatabase` 为主表, 汇总实例信息, 标签, 以及最新容量.
- 提供导出: 以 CSV 附件形式导出台账.
- 提供表容量快照: 查询最新表级容量快照, 并支持手动刷新(连接外部数据库采集后写回主库).
- 不负责容量采集/聚合调度: 采集与聚合属于 `capacity`/`database_sync` 域, 本域只是消费其结果用于展示与查询.

## 用户入口

Web UI:

- `/databases/ledgers`

API v1(SSOT: [[API/databases-api-contract]]):

- `GET /api/v1/databases/ledgers`
- `GET /api/v1/databases/ledgers/exports`(CSV)
- `GET /api/v1/databases/options`
- `GET /api/v1/databases/sizes`
- `GET /api/v1/databases/{database_id}/tables/sizes`
- `POST /api/v1/databases/{database_id}/tables/sizes/actions/refresh`

## 代码落点(Where to change what)

Web UI:

- route: `app/routes/databases/ledgers.py`
- template: `app/templates/databases/ledgers.html`
- JS: `app/static/js/modules/views/databases/ledgers.js`

API v1:

- namespace: `app/api/v1/namespaces/databases.py`

Services:

- ledger query: `app/services/ledgers/database_ledger_service.py`
- export: `app/services/files/database_ledger_export_service.py`
- table sizes snapshot: `app/services/instances/instance_database_table_sizes_service.py`
- table sizes refresh coordinator: `app/services/database_sync/table_size_coordinator.py`

Repositories/Models(主库):

- model: `app/models/instance_database.py`
- ledger repo: `app/repositories/ledgers/database_ledger_repository.py`
- capacity stats:
  - `app/models/database_size_stat.py`
  - `app/models/database_table_size_stat.py`

## 组件图

```mermaid
graph TB
    UI["Web UI<br/>/databases/ledgers"] --> Api["API v1<br/>/api/v1/databases/**"]

    Api --> Ledger["DatabaseLedgerService<br/>(list, iterate_all)"]
    Ledger --> LedgerRepo["DatabaseLedgerRepository"]
    LedgerRepo --> MainDB["PostgreSQL<br/>(instance_databases + tags + capacity stats)"]

    Api --> ExportSvc["DatabaseLedgerExportService<br/>(render CSV)"]
    ExportSvc --> Ledger

    Api --> TableSnap["InstanceDatabaseTableSizesService<br/>(read snapshot)"]
    TableSnap --> MainDB

    Api --> Refresh["TableSizeCoordinator.refresh_snapshot<br/>(connect + collect + upsert)"]
    Refresh --> ExtDB["External DB<br/>(db_type adapters)"]
    Refresh --> MainDB
```

> [!tip]
> Canvas: [[canvas/databases-ledger/databases-ledger-domain-components.canvas]]

## 流程图(表容量刷新)

```mermaid
flowchart TD
    UIAction["UI: click refresh"] --> API["POST /api/v1/databases/{id}/tables/sizes/actions/refresh<br/>(CSRF + update)"]
    API --> Connect{"connect ok?"}
    Connect -->|no| Conflict["409 DATABASE_CONNECTION_ERROR"]
    Connect -->|yes| Collect["collect table sizes"]
    Collect --> Upsert["upsert latest snapshot<br/>database_table_size_stats"]
    Upsert --> Query["GET /api/v1/databases/{id}/tables/sizes"]
    Query --> Resp["return snapshot + saved/deleted/elapsed"]
```

> [!tip]
> Canvas: [[canvas/databases-ledger/databases-ledger-flow.canvas]]

## 常见坑

- 分页统一为 `page/limit`, 不支持 `offset`(databases namespace 会直接报 `VALIDATION_ERROR`).
- `ledgers/exports` 成功返回 CSV, 失败仍是 JSON envelope(对齐 contract).
- `tables/sizes/actions/refresh` 是写动作:
  - MUST: `X-CSRFToken`
  - MUST: `api_permission_required("update")`

## 排障锚点

- 错误码入口: [[reference/errors/message-code-catalog]]
- 常见 message_code:
  - `DATABASE_CONNECTION_ERROR`
  - `SYNC_DATA_ERROR`
  - `VALIDATION_ERROR`
- 日志定位: module 常见为 `databases`/`databases_ledgers`/`database_aggregations`(以实际日志 `context.module` 为准), SOP 见 [[operations/observability-ops]].

