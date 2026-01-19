# scheduler（app/scheduler.py + services/scheduler + core/constants/scheduler_jobs.py）

## Core Purpose

- 提供 APScheduler 的初始化、任务加载/重载、任务执行与内置任务集合。
- 为 scheduler 管理相关 API/页面提供读写服务与动作编排。

## Unnecessary Complexity Found

- （已落地）`app/scheduler.py:332`：
  - `_acquire_scheduler_lock` 存在重复的 “handle 是否存在” 分支判断，且 `os.getpid()` 多次读取。
  - 逻辑可等价压缩为 “同进程直接复用 / 否则关闭继承句柄并重置 / 重新加锁”，减少读者心智负担。

- （已落地）`app/scheduler.py:521`：
  - `_reload_all_jobs` 仅作为薄封装（兼容历史调用点/测试 monkeypatch），不提供额外抽象收益。

- （已落地）`app/services/scheduler/scheduler_actions_service.py:94`：
  - `run_job_in_background` 对内置任务/非内置任务分了两条调用路径，但最终都是 `job.func(*args, **kwargs)`，差异仅在少数 job_id 的 kwargs 注入。
  - 可收敛为单次调用 + 条件注入，减少重复与分支噪音。

## Code to Remove

- `app/scheduler.py:521`：保留 `_reload_all_jobs` 作为兼容入口，但内部直接转发到 `_load_tasks_from_config(force=True)`（可删/可减复杂度 LOC 估算：~0-4；主要是减少调用点分支/重复逻辑）。
- `app/services/scheduler/scheduler_actions_service.py:94`：收敛为单次 `job.func` 调用（可删/可减复杂度 LOC 估算：~4-10）。
- `app/scheduler.py:332`：移除重复分支并复用 `current_pid`（可删/可减复杂度 LOC 估算：~2-6）。

## Simplification Recommendations

1. 压缩锁获取逻辑到最小必要分支
   - Current: “handle 存在” 判断重复，读者需要二次确认状态流转。
   - Proposed: 先处理同 PID 复用，再处理继承句柄重置，最后统一加锁。

2. 删除无收益的薄封装
   - Current: `_reload_all_jobs` 仅转发参数。
   - Proposed: 保留 `_reload_all_jobs` 作为兼容入口，但让所有真实逻辑集中在 `_load_tasks_from_config`。

3. 收敛“同一调用的两套路径”
   - Current: 内置任务与非内置任务最终都调用 `job.func`，但被拆成两条分支。
   - Proposed: 仅对需要注入参数的任务做 kwargs patch，其余统一走同一调用。

## YAGNI Violations

- 仅为了“看起来更抽象/更可扩展”而引入的薄封装与重复分支（缺少明确收益/用例）。

## Final Assessment

- 可删/可减复杂度估算：~18-34（已落地，以删薄封装与分支噪音为主）
- Complexity: Medium -> Lower
- Recommended action: Proceed（本轮仅做等价重排与删薄封装，不触碰调度器行为路径）。
