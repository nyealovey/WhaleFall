---
title: Scheduler domain
aliases:
  - scheduler-domain
tags:
  - architecture
  - architecture/domain
  - domain/scheduler
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: APScheduler(jobstore/lock/job lifecycle), 以及与 tasks/operations 的边界
related:
  - "[[architecture/spec]]"
  - "[[operations/scheduler-jobstore-ops]]"
  - "[[canvas/scheduler/scheduler-domain-components.canvas]]"
  - "[[canvas/scheduler/scheduler-flow.canvas]]"
  - "[[canvas/scheduler/scheduler-sequence.canvas]]"
  - "[[canvas/scheduler/scheduler-state-machine.canvas]]"
  - "[[canvas/scheduler/scheduler-erd.canvas]]"
---

# Scheduler domain

## 边界与职责

- 负责 job 的注册/持久化(jobstore)/触发与手动运行入口.
- 通过文件锁确保多进程下仅 1 个 scheduler 实例持锁运行.
- 任务逻辑不在 scheduler 内实现, 而是 dispatch 到 `app/tasks/**`.

## 关键配置与文件

- scheduler 开关: `ENABLE_SCHEDULER`
- 默认任务配置: `app/config/scheduler_tasks.yaml`
- jobstore(SQLite): `userdata/scheduler.db`
- file lock: `userdata/scheduler.lock`

## 代码落点(常用)

- scheduler wrapper: `app/scheduler.py`
- API(manual run): `app/api/v1/namespaces/scheduler.py`
- job write service: `app/services/scheduler/scheduler_job_write_service.py`

## 运维口径(必看)

- [[operations/scheduler-jobstore-ops]]

## 图(Canvas)

- Domain components: [[canvas/scheduler/scheduler-domain-components.canvas]]
- Flow: [[canvas/scheduler/scheduler-flow.canvas]]
- Sequence: [[canvas/scheduler/scheduler-sequence.canvas]]
- State machine: [[canvas/scheduler/scheduler-state-machine.canvas]]
- ERD: [[canvas/scheduler/scheduler-erd.canvas]]
