---
title: Instance Capacity Sync Actions Service(单实例容量同步)
aliases:
  - instance-capacity-sync-actions-service
tags:
  - server
  - server/capacity
  - services
  - diagram
  - decision-table
status: draft
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: app/services/capacity/instance_capacity_sync_actions_service.py
related:
  - "[[architecture/flows/capacity-sync]]"
  - "[[API/instances-api-contract]]"
  - "[[reference/server/database-sync-overview]]"
  - "[[reference/server/aggregation-pipeline]]"
  - "[[standards/doc/service-layer-documentation-standards]]"
---

# Instance Capacity Sync Actions Service(单实例容量同步)

> [!note] 本文目标
> 说明 `POST /api/v1/instances/{id}/actions/sync-capacity` 的 action 编排层: 连接 -> inventory -> capacity -> 持久化 -> best-effort 触发聚合, 以及 message_key/http_status 规则.

## 1. 概览(Overview)

覆盖文件:

- `app/services/capacity/instance_capacity_sync_actions_service.py`

核心入口:

- `InstanceCapacitySyncActionsService.sync_instance_capacity(instance_id) -> InstanceCapacitySyncActionResult`

调用方:

- route: `POST /api/v1/instances/{instance_id}/actions/sync-capacity`

下游依赖:

- `database_sync_module.CapacitySyncCoordinator`
- `aggregation_module.AggregationService` (best-effort)

## 2. 事务与失败语义(Transaction + Failure Semantics)

- 本 service 不做 commit; 由 route 层 commit/rollback.
- 连接失败:
  - `coordinator.connect()` False -> http 409 + message_key=DATABASE_CONNECTION_ERROR.
- inventory 只同步:
  - `active_databases` 为空 -> success=true, 返回 message "未发现活跃数据库,已仅同步数据库列表".
- capacity 采集失败:
  - 捕获 `(RuntimeError, ConnectionError, TimeoutError, OSError)` -> http 409 + message_key=SYNC_DATA_ERROR.
  - `databases_data` 为空 -> http 409 + message_key=SYNC_DATA_ERROR.
- 触发聚合失败:
  - 捕获 `Exception` 仅 warning log, 不影响主流程返回.
- finally:
  - 总会调用 `coordinator.disconnect()`.

## 3. 主流程图(Flow)

```mermaid
flowchart TB
    A["POST /instances/{id}/actions/sync-capacity"] --> S["InstanceCapacitySyncActionsService.sync_instance_capacity"]
    S --> I["Instance.query.get(id)"]
    I -->|missing| NErr["raise NotFoundError"]
    I -->|ok| C["CapacitySyncCoordinator(instance)"]
    C --> Conn{connect()?}
    Conn -->|no| FailConn["409 DATABASE_CONNECTION_ERROR"]
    Conn -->|yes| Inv["synchronize_inventory() -> active_databases"]
    Inv --> DBs{active_databases empty?}
    DBs -->|yes| OkInv["200 success (inventory only)"]
    DBs -->|no| Cap["collect_capacity(databases)"]
    Cap -->|error| FailCap["409 SYNC_DATA_ERROR"]
    Cap --> Save["save_database_stats + update_instance_total_size"]
    Save --> Agg["best-effort AggregationService.calculate_daily_*"]
    Agg --> Out["200 success + counts"]
    Out --> Disc["finally: disconnect()"]
    FailConn --> Disc
    FailCap --> Disc
    OkInv --> Disc
```

## 4. 决策表/规则表(Decision Table)

### 4.1 message_key/http_status

| 场景 | http_status | message_key |
| --- | --- | --- |
| instance 不存在 | - | (NotFoundError) |
| connect 失败 | 409 | DATABASE_CONNECTION_ERROR |
| capacity 采集异常/空数据 | 409 | SYNC_DATA_ERROR |
| inventory only | 200 | OPERATION_SUCCESS |
| 完整成功 | 200 | OPERATION_SUCCESS |

实现位置: `app/services/capacity/instance_capacity_sync_actions_service.py:46`.

## 5. 兼容/防御/回退/适配逻辑

| 位置(文件:行号) | 类型 | 描述 | 触发条件 | 清理条件/期限 |
| --- | --- | --- | --- | --- |
| `app/services/capacity/instance_capacity_sync_actions_service.py:73` | 防御 | connect 失败返回 ActionResult(不抛异常) | 外部实例不可用 | 若要求统一异常口径, 可改为抛 AppError 并由 route 封套 |
| `app/services/capacity/instance_capacity_sync_actions_service.py:101` | 防御 | collect_capacity 捕获有限异常集合并转 SYNC_DATA_ERROR | 适配器/网络异常 | 若要细分错误码, 收敛异常类型并补用例 |
| `app/services/capacity/instance_capacity_sync_actions_service.py:132` | 回退 | 触发聚合失败仅 warning 不影响成功返回 | 聚合失败/DB 错误 | 若聚合必须成功, 改为硬失败并更新 UI 语义 |

## 6. 可观测性(Logs + Metrics)

- 聚合触发失败: `log_warning("容量同步后触发聚合失败", module="databases_capacity", instance_id=...)`.

## 7. 测试与验证(Tests)

最小验证命令:

- `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_sync_capacity_contract.py`
