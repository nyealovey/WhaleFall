---
title: Scheduler - API Contract
aliases:
  - scheduler-api-contract
tags:
  - api/contract
  - scheduler
  - jobs
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/scheduler.py
---

# Scheduler - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/scheduler.py`（挂载：`/api/v1/scheduler`）
>

## Scope

- ✅ Jobs：list / detail / update
- ✅ Job Actions：pause / resume / run
- ✅ Jobs Actions：reload

## 快速导航

- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Update Job Trigger（内置任务）]]

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限以代码侧 `api_permission_required(...)` 为准：
  - 查看：`view`
  - 管理：`admin`
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含 action endpoints）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path                                             | Purpose | Service | Permission         | CSRF | Notes                            |
| ------ | ------------------------------------------------ | ------- | ------- | ------------------ | ---- | -------------------------------- |
| GET    | `/api/v1/scheduler/jobs`                         | 任务列表    | `SchedulerJobsReadService.list_jobs` | `view`             | -    | 调度器未启动时返回 409                    |
| GET    | `/api/v1/scheduler/jobs/{job_id}`                | 任务详情    | `SchedulerJobsReadService.get_job` | `view`             | -    | 任务不存在返回 404；调度器未启动返回 409         |
| PUT    | `/api/v1/scheduler/jobs/{job_id}`                | 更新任务触发器 | `SchedulerJobWriteService.upsert` | `admin`            | ✅    | 仅允许修改内置任务（否则 400/403）            |
| POST   | `/api/v1/scheduler/jobs/{job_id}/actions/pause`  | 暂停任务    | `scheduler.pause_job` | `admin`            | ✅    | 调度器未启动返回 409                     |
| POST   | `/api/v1/scheduler/jobs/{job_id}/actions/resume` | 恢复任务    | `scheduler.resume_job` | `admin`            | ✅    | 调度器未启动返回 409                     |
| POST   | `/api/v1/scheduler/jobs/{job_id}/actions/run`    | 立即执行任务  | `scheduler.get_job`<br>`job.func (background)` | `admin`            | ✅    | 成功返回 `data.manual_job_id`（后台线程名） |
| POST   | `/api/v1/scheduler/jobs/actions/reload`          | 重新加载任务  | `scheduler.remove_job`<br>`scheduler_module._reload_all_jobs` | `admin`            | ✅    | 会移除当前任务并重新注册；调度器未启动返回 409        |

## Update Job Trigger（内置任务）

### `PUT /api/v1/scheduler/jobs/{job_id}`

> [!warning]
> 仅允许修改内置任务（`BUILTIN_TASK_IDS`），非内置任务会被拒绝。

请求体（JSON，关键字段）：

- `trigger_type: "cron"|"interval"|"date"`（必填）
- 当 `trigger_type == "cron"`：
  - `cron_expression`（可选；5/6/7 段表达式均支持）
  - 或使用 `cron_second/cron_minute/cron_hour/cron_day/cron_month/cron_weekday/year` 等字段
  - `timezone`（可选；默认 `Asia/Shanghai`）
- 当 `trigger_type == "interval"`：
  - `weeks/days/hours/minutes/seconds`（任意正整数至少 1 个）
- 当 `trigger_type == "date"`：
  - `run_date`（必填；可被 `time_utils.to_utc` 解析）
