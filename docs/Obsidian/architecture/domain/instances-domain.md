---
title: Instances domain
aliases:
  - instances-domain
tags:
  - architecture
  - architecture/domain
  - domain/instances
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: instances 的生命周期, 以及与 accounts/capacity 等能力的边界与落点
related:
  - "[[architecture/project-structure]]"
  - "[[architecture/flows/accounts-sync]]"
  - "[[architecture/flows/capacity-sync]]"
  - "[[API/instances-api-contract]]"
  - "[[canvas/instances/instances-flow.canvas]]"
  - "[[canvas/instances/instances-domain-components.canvas]]"
  - "[[canvas/instances/instances-state-machine.canvas]]"
---

# Instances domain

## 边界与职责

- 本域负责 "实例(Instance)元数据" 的增删改查, 以及其生命周期(启用/禁用/回收站/恢复).
- 本域不直接承诺 accounts/capacity 的业务语义, 但它们的触发入口常挂在 instances 相关 UI/API 上.

## 常见任务导航

- 账户同步: [[architecture/flows/accounts-sync]]
- 容量同步: [[architecture/flows/capacity-sync]]

## 代码落点(常用)

- Models:
  - `app/models/instance.py`
  - `app/models/instance_database.py`
- Services:
  - `app/services/instances/instance_write_service.py`
  - `app/services/instances/instance_list_service.py`
  - `app/services/instances/instance_detail_read_service.py`
- API v1:
  - `app/api/v1/namespaces/instances.py`
- Web UI:
  - templates: `app/templates/instances/**`
  - JS: `app/static/js/modules/views/instances/**`

## 图(Canvas)

- Domain components: [[canvas/instances/instances-domain-components.canvas]]
- Flow: [[canvas/instances/instances-flow.canvas]]
- Sequence: [[canvas/instances/instances-sequence.canvas]]
- State machine: [[canvas/instances/instances-state-machine.canvas]]
- ERD: [[canvas/instances/instances-erd.canvas]]

> [!tip]
> 推荐先从 domain components 看边界, 再看 flow/sequence 定位调用链.
