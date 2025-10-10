# Scheduler Health Check Updates

## 背景

原有的调度器健康检查逻辑直接访问 `scheduler.executors` 属性。某些 APScheduler 版本并不会公开该属性，
导致健康检查在日志中频繁输出 “调度器无 executors 属性” 的警告。虽然调度器本身运行正常，但重复的告警
让监控信息变得噪声很大，也掩盖了真正的问题。

## 新的实现概览

我们新增了 `SchedulerHealthService`（`app/services/scheduler_health_service.py`），把健康检查的细节封装成一个
独立的服务类，以便在其它地方重用。服务会通过工具方法逐步尝试以下检查：

1. 调用 `scheduler.get_jobs()` 获取任务列表，并捕获异常判断 JobStore 是否可用；
2. 读取 `_executors` 字典，如果没有则尝试 `lookup_executor` / `_lookup_executor`，兼容不同版本的 APScheduler；
3. 为每个执行器生成 `ExecutorReport`，记录名称、类型、健康状态和诊断信息；
4. 聚合结果后返回 `SchedulerHealthReport`，包含运行状态、任务数量、暂停情况和执行器检查结论。

`app/routes/scheduler.py` 中的 `get_scheduler_health` 现在调用新的服务，并基于报告生成健康分数：

- 运行状态占 35 分；
- JobStore 正常占 25 分；
- 至少一个执行器工作占 25 分；
- 至少存在一个任务占 15 分；
- 如果有任务但执行器不可用，会扣 30 分；
- 如果无任务但调度器运行正常，会保证最低 40 分。

除了总分之外，接口还会返回 `executor_details` 与 `warnings`，方便在前端或日志中展示更细致的诊断信息。

## 使用方式

前端或运维系统仍旧调用 `/scheduler/api/health`。响应中新字段：

- `executor_details`: 列表形式，记录每个执行器的别名、类型、是否健康、补充说明；
- `warnings`: 字符串数组，例如 `"no_executors_detected"`、`"jobstore_unreachable"`；
- `source` 字段保持不变，仍然在总容量接口等位置指示数据来源。

通过这些信息，即便某个执行器缺失或 JobStore 出现短暂异常，也能快速定位原因，而不会再被误报的
“调度器无 executors 属性” 警告刷屏。
