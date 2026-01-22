---
title: Scheduler/jobstore 运维口径
aliases:
  - scheduler-jobstore-ops
  - scheduler-ops
tags:
  - operations
  - operations/scheduler
status: draft
created: 2026-01-10
updated: 2026-01-22
owner: WhaleFall Team
scope: APScheduler + SQLite jobstore(`userdata/scheduler.db`) 的运行口径, 多进程/多实例注意点, 重置方式与风险
related:
  - "[[operations/README|operations]]"
  - "[[API/scheduler-api-contract]]"
  - "[[standards/backend/task-and-scheduler]]"
  - "[[reference/errors/message-code-catalog]]"
---

# Scheduler/jobstore 运维口径

## 1. 适用场景

- scheduler API 返回 409("调度器未启动")
- 多进程/多实例部署后发现任务重复执行
- 需要重置 jobstore(SQLite) 或恢复默认任务

## 2. 前置条件

- 你知道当前环境的部署形态(单机单实例, 单机多进程, 多机多实例).
- 你有一组可用的管理员账号(用于调用 `/api/v1/scheduler/**`).
  - 参考: `docs/Obsidian/reference/examples/api-v1-cookbook.md`

## 3. 核心事实(实现约定)

- 调度器实现: `app/scheduler.py`
- 默认任务配置: `app/config/scheduler_tasks.yaml`
- jobstore: SQLite, 文件路径固定为 `userdata/scheduler.db`
- 单实例策略: 通过部署约束确保仅 1 个进程启用 `ENABLE_SCHEDULER=true`（推荐 Web/Scheduler 分进程/分容器）。
- 多机多实例: 每台机器都会各自启动 scheduler, 因为 jobstore 是本地文件, 不共享.

> [!warning]
> 生产多实例部署时, 默认会出现任务重复执行(每台机器 1 份). 正确口径是: 仅让 1 个实例启用 scheduler, 其余实例禁用.

## 4. ENABLE_SCHEDULER 开关

- 环境变量: `ENABLE_SCHEDULER`
- 取值:
  - `true/1/yes`: 启用(默认)
  - 其他: 禁用

建议:

- Web API 实例: `ENABLE_SCHEDULER=false`
- 单独的 scheduler 实例: `ENABLE_SCHEDULER=true`

## 5. 常用操作

### 5.1 确认 scheduler 是否在跑

通过 API:

- `GET /api/v1/scheduler/jobs`
  - 成功: 200, 返回 jobs 列表
  - 失败: 409, 通常 `message_code=CONSTRAINT_VIOLATION`, `message` 类似 "调度器未启动"

通过文件:

```bash
ls -la userdata/scheduler.db || true
```

### 5.2 重新加载默认任务

适用:

- `scheduler_tasks.yaml` 更新后
- jobstore 状态不一致, 需要"删除全部 job -> 重新注册"

操作:

- `POST /api/v1/scheduler/jobs/actions/reload`

风险:

- 会删除当前 jobstore 中的所有 job, 再按 `scheduler_tasks.yaml` 重新注册.

### 5.3 重置 jobstore(SQLite)

适用:

- jobstore 损坏/写入异常
- 需要彻底清空并重新生成

步骤(建议先备份):

```bash
ts="$(date +%Y%m%d%H%M%S)"
if [[ -f userdata/scheduler.db ]]; then
  cp -a userdata/scheduler.db "userdata/scheduler.db.bak.${ts}"
fi

rm -f userdata/scheduler.db
```

验证:

- 重启服务后, `userdata/scheduler.db` 会被重新创建.
- 通过 `GET /api/v1/scheduler/jobs` 确认默认任务已出现.

> [!danger]
> 重置 jobstore 会丢失"通过 API 修改过的 cron trigger"等运行态变更. 如果你依赖这些变更, 必须先导出并记录.

## 6. 故障排查

### 6.1 任务重复执行

典型原因:

- 多机多实例部署, 每台机器都有自己的 scheduler.

处理:

- 仅保留 1 个实例 `ENABLE_SCHEDULER=true`, 其余全部置为 `false`.

### 6.2 API 返回 409("调度器未启动")

检查:

- 当前进程是否启用了 `ENABLE_SCHEDULER`
- 是否处于 Flask reloader 父进程(开发模式)导致 scheduler 被跳过

代码入口:

- `app/scheduler.py` -> `_should_start_scheduler()`

### 6.3 jobstore 文件存在但任务为空

处理:

- 调用 reload: `POST /api/v1/scheduler/jobs/actions/reload`
- 或按 5.3 重置 jobstore
