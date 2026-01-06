# 调度与执行域(Scheduler)研发图表包

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-06
> 更新: 2026-01-06
> 范围: APScheduler jobstore + job lifecycle + manual run
> 关联: ./capacity-partitions-domain.md; ./accounts-permissions-domain.md; ./spec.md

## 1. 主流程图(Flow)

场景: 调度器加载任务配置并执行,以及通过 API 手动触发一次任务.

入口:

- boot: `app/scheduler.py` load `app/config/scheduler_tasks.yaml`
- manual run: `POST /api/v1/scheduler/jobs/{job_id}/run`

```mermaid
flowchart TD
  Boot["App start"] --> Lock["Acquire file lock (single scheduler instance)"]
  Lock --> Jobstore["Init APScheduler jobstore: userdata/scheduler.db (SQLite)"]
  Jobstore --> LoadCfg["Load scheduler_tasks.yaml"]
  LoadCfg --> Register["Register jobs (Cron/Interval/Date)"]
  Register --> Running["Scheduler running"]

  Running --> Tick["Scheduler tick"]
  Tick --> Dispatch["Call job.func(*args, **kwargs)"]
  Dispatch --> Task["app/tasks/* (domain tasks)"]
  Task --> Writes["Write Postgres/External DB via domain services"]

  Running --> API["Scheduler API"]
  API --> Run["POST /scheduler/jobs/{job_id}/run"]
  Run --> GetJob["scheduler.get_job(job_id)"]
  GetJob --> Exists{"job exists?"}
  Exists -->|no| E404["Return 404 NotFoundError"]
  Exists -->|yes| Thread["Spawn background thread"]
  Thread --> Ctx["create_app() + app_context()"]
  Ctx --> ManualKw{"builtin job needs manual flags?"}
  ManualKw -->|yes| Inject["inject manual_run/created_by"]
  ManualKw -->|no| Keep["use job.kwargs as-is"]
  Inject --> Call["job.func(...)"]
  Keep --> Call
  Call --> Writes
```

关键点:

- jobstore: APScheduler uses SQLite at `userdata/scheduler.db` to persist job definitions.
- lock: file lock prevents multiple scheduler instances in the same environment.
- manual run: API only submits a background thread, task execution is async.

## 2. 主时序图(Sequence)

场景: 手动触发内置任务立即执行.

入口: `POST /api/v1/scheduler/jobs/{job_id}/run`

```mermaid
sequenceDiagram
  autonumber
  participant U as User/Browser
  participant API as Scheduler API
  participant Safe as safe_route_call
  participant SCH as APScheduler
  participant TH as Background Thread
  participant APP as Flask app_context
  participant Task as job.func (app/tasks/*)
  participant PG as PostgreSQL
  participant EXT as External DB (task dependent)

  U->>API: POST /scheduler/jobs/{job_id}/run
  API->>Safe: execute()
  Safe->>SCH: ensure scheduler running
  Safe->>SCH: get_job(job_id)
  alt job not found
    Safe-->>U: 404 error envelope
  else job found
    Safe->>TH: start thread(job_id_manual)
    TH->>APP: create_app() + app_context()
    alt builtin job with manual flags
      TH->>Task: job.func(..., manual_run=True, created_by=user_id)
    else normal job
      TH->>Task: job.func(..., **job.kwargs)
    end
    Task->>PG: write sync_sessions/sync_instance_records (if task uses sessions)
    Task->>EXT: connect/query (if task touches external DB)
    Safe-->>U: 200 success envelope {manual_job_id}
  end
```

## 3. 状态机(Optional but valuable)

### 3.1 Job state (API visible)

Job state is observed via `next_run_time` and scheduler running status:

- running: scheduler running and job has next_run_time
- paused: job paused or scheduler stopped

```mermaid
stateDiagram-v2
  [*] --> running
  running --> paused: pause_job(job_id)
  paused --> running: resume_job(job_id)
  running --> paused: scheduler stopped
```

### 3.2 Manual run lifecycle

Manual run creates a background thread and returns immediately:

```mermaid
stateDiagram-v2
  [*] --> submitted
  submitted --> running: thread starts + app_context entered
  running --> succeeded: job.func returns normally
  running --> failed: job.func raises (logged)
  succeeded --> [*]
  failed --> [*]
```

## 4. API 契约(Optional)

说明:

- `/run` is async: returns `manual_job_id` immediately, execution details must be checked via logs and/or SyncSession (if the task writes sessions).
- `/jobs/{job_id}` update only supports builtin tasks trigger changes.

| Method | Path | Purpose | Idempotency | Notes |
| --- | --- | --- | --- | --- |
| GET | /api/v1/scheduler/jobs | list jobs | yes (read) | requires scheduler running |
| GET | /api/v1/scheduler/jobs/{job_id} | job detail | yes (read) | includes trigger + next_run_time |
| PUT | /api/v1/scheduler/jobs/{job_id} | update trigger | no | only builtin jobs; csrf required |
| POST | /api/v1/scheduler/jobs/{job_id}/pause | pause job | yes-ish | csrf required |
| POST | /api/v1/scheduler/jobs/{job_id}/resume | resume job | yes-ish | csrf required |
| POST | /api/v1/scheduler/jobs/{job_id}/run | run job now | no | returns manual_job_id; runs in background |
| POST | /api/v1/scheduler/jobs/reload | reload all jobs | no | deletes existing jobs then reloads from config |

