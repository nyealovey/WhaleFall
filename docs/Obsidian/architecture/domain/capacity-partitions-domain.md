---
title: Capacity + Partitions domain
aliases:
  - capacity-partitions-domain
tags:
  - architecture
  - architecture/domain
  - domain/capacity
  - domain/partitions
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: capacity stats(采集/聚合)与分区表(partitions)的边界, 以及关键表与任务
related:
  - "[[architecture/flows/capacity-sync]]"
  - "[[architecture/flows/aggregation-stats]]"
  - "[[operations/scheduler-jobstore-ops]]"
  - "[[canvas/capacity/capacity-domain-components.canvas]]"
  - "[[canvas/capacity/capacity-flow.canvas]]"
  - "[[canvas/capacity/capacity-sequence.canvas]]"
  - "[[canvas/capacity/aggregation-stats-flow.canvas]]"
  - "[[canvas/capacity/capacity-aggregation-sequence.canvas]]"
  - "[[canvas/capacity/capacity-state-machine.canvas]]"
  - "[[canvas/capacity/capacity-erd.canvas]]"
---

# Capacity + Partitions domain

## 边界与职责

- Capacity sync: 从外部 DB 采集 database/instance size stats, 落库为日粒度 stats.
- Aggregations: 将 stats 聚合为多周期(period_type)数据, 支撑 charts 与查询.
- Partitions: 对大表(例如 logs, stats)做分区与保留期治理, 降低长期运行成本.

## 关键表(SSOT 以 models 为准)

- stats:
  - `database_size_stats`
  - `instance_size_stats`
- aggregations:
  - `database_size_aggregations`
  - `instance_size_aggregations`

## 代码落点(常用)

- Tasks:
  - `app/tasks/capacity_collection_tasks.py`
  - `app/tasks/capacity_aggregation_tasks.py`
- Services:
  - `app/services/database_sync/**`
  - `app/services/aggregation/aggregation_service.py`
  - `app/services/partition_management_service.py`

## 图(Canvas)

- Domain components: [[canvas/capacity/capacity-domain-components.canvas]]
- Flow(collect + partitions): [[canvas/capacity/capacity-flow.canvas]]
- Sequence(collect): [[canvas/capacity/capacity-sequence.canvas]]
- Flow(aggregation stats): [[canvas/capacity/aggregation-stats-flow.canvas]]
- Sequence(aggregation): [[canvas/capacity/capacity-aggregation-sequence.canvas]]
- State machine: [[canvas/capacity/capacity-state-machine.canvas]]
- ERD: [[canvas/capacity/capacity-erd.canvas]]

> [!tip]
> 如果你遇到 charts 不更新, 优先检查 stats 是否持续写入, 然后再看 aggregation job 是否在跑.
