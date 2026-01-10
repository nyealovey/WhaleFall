---
title: 关键流程索引
aliases:
  - architecture-flows
  - flows
tags:
  - architecture
  - architecture/flows
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 登录/同步会话/容量采集/scheduler 等关键流程的索引入口
related:
  - "[[architecture/spec]]"
  - "[[architecture/identity-access]]"
  - "[[operations/observability-ops]]"
  - "[[API/api-v1-api-contract]]"
---

# 关键流程索引

> [!note] 说明
> 本目录提供关键流程的索引入口. 当前流程图的 SSOT 在 [[architecture/spec]].

## 登录

- Web 登录: [[architecture/spec#5.1 Web 登录(页面)]]
- API 登录与调用: [[architecture/spec#5.2 API 登录与调用(REST)]]

## 同步会话

- 账户同步(后台): [[architecture/spec#5.3 账户同步(后台: inventory + permissions)]]
- 会话中心与记录模型:
  - `SyncSession`: `app/models/sync_session.py`
  - `SyncInstanceRecord`: `app/models/sync_instance_record.py`

## 容量采集与聚合

- 容量采集: [[architecture/spec#5.5 容量采集(库存 + size stats)]]
- 周/月/季聚合: [[architecture/spec#5.6 周/月/季聚合(aggregation)]]
- 分区管理(保留期): `app/tasks/partition_management_tasks.py`

## scheduler 执行

- 调度器初始化与任务运行: [[architecture/spec#8. Scheduler & Tasks(任务调度)]]
- 运维口径: [[operations/README|operations]]

## 日志与排障

- 统一日志落库与查询: [[architecture/spec#5.7 统一日志落库与查询]]
- 排障 SOP: [[operations/observability-ops]]

