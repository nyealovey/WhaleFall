# P2-004 事务边界收敛：`db.session.commit()` / `db.session.begin_nested()` 清单

更新时间：2026-01-28  
范围：`app/**`  
目标：把散落的 commit / begin_nested 逐点盘点，判断哪些是“必要的进度持久化/局部隔离”，哪些是“可删除的样板/可由上层入口统一”。

## 总览

- `db.session.commit()`：69 处（8 个文件；其中 6 个在 `app/tasks/**`）
- `db.session.begin_nested()`：29 处（15 个文件）

> 说明：本清单只解释“为什么存在/是否可收敛”，不在这里直接改代码。

---

## A. `db.session.commit()`（69）

### `app/infra/route_safety.py`

- `app/infra/route_safety.py:192`：`safe_route_call()` 在业务函数成功后统一 `commit()`。
  - 为什么存在：把 Web 请求的事务提交集中到单一入口，失败时统一 `rollback()` + 统一日志。
  - 是否可收敛：KEEP（这是“收敛”的目标点；删掉反而会逼迫 routes/service 自己提交，语义更分散）。

### `app/infra/logging/queue_worker.py`

- `app/infra/logging/queue_worker.py:184`：`LogQueueWorker._flush_buffer()` 批量写入结构化日志模型后 `commit()`。
  - 为什么存在：后台线程不走 `safe_route_call`；必须显式提交才能把日志真正落库。
  - 是否可收敛：KEEP（这是该线程的顶层事务边界）。

### `app/tasks/capacity_collection_tasks.py`（13）

> 该文件的 commit 主要用于两件事：
> 1) TaskRun/TaskRunItem 的进度写入（让 UI/取消逻辑能看到“已开始/已完成/失败”）；
> 2) capacity 同步会话/实例记录的状态落库（避免进程中断导致状态悬空）。

- `app/tasks/capacity_collection_tasks.py:42`：`_finalize_task_failed()` 内，标记 session 失败后 `commit()`。
  - 为什么存在：把 session 的失败状态立即落库，避免后续错误处理/重试看不到失败终态。
  - 是否可收敛：KEEP（属于失败终态写入点）。

- `app/tasks/capacity_collection_tasks.py:57`：`_finalize_task_failed()` 内，更新 TaskRun/TaskRunItem 为 failed 并 `finalize_run()` 后 `commit()`。
  - 为什么存在：确保任务运行记录与 item 状态落库，UI 能看到失败明细。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_collection_tasks.py:75`：`_process_instance_with_fallback()` 内，`runner.start_instance_sync(record.id)` 后 `commit()`。
  - 为什么存在：把“该实例同步已开始/运行中”持久化；后续异常 `rollback()` 不会把“开始”撤销。
  - 是否可收敛：多半 KEEP（属于进度点；若要减少 commit 次数，需要确认上游不依赖 running 状态实时展示）。

- `app/tasks/capacity_collection_tasks.py:100`：`_process_instance_with_fallback()` 异常分支，`runner.fail_instance_sync(...)` 后 `commit()`。
  - 为什么存在：把失败原因与失败状态写入实例记录；随后任务仍可继续跑下一个实例。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_collection_tasks.py:109`：`_process_instance_with_fallback()` 成功分支末尾 `commit()`。
  - 为什么存在：把 `process_capacity_instance()` 对本实例产生的 DB 变更落库。
  - 是否可收敛：MAYBE（如果 `process_capacity_instance()` 本身已经在内部做了“每实例一次 upsert + flush”，理论上可以把这次 commit 合并到更外层“每实例结束时的 commit”，但需要确认没有依赖中途可见性）。

- `app/tasks/capacity_collection_tasks.py:135`：`_finalize_no_active_instances()` 在 `finalize_run()` 后 `commit()`。
  - 为什么存在：无实例时也要把 TaskRun 的 summary/终态写入。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_collection_tasks.py:168`：`_sync_instances()` 每实例 `task_runs_service.start_item()` 后 `commit()`。
  - 为什么存在：让 item 立刻从 pending -> running；同时保证后续异常回滚不影响“已开始”记录。
  - 是否可收敛：多半 KEEP（进度点）。

- `app/tasks/capacity_collection_tasks.py:206`：`_sync_instances()` 每实例 `complete_item()/fail_item()` 后 `commit()`。
  - 为什么存在：把该实例 item 的最终状态写入，便于 UI 查看与统计。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_collection_tasks.py:219`：`_finalize_capacity_session()` 写入 session 汇总字段后 `commit()`。
  - 为什么存在：会话级“成功/失败实例数、完成时间、状态”需要落库。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_collection_tasks.py:244`：`_finalize_task_run_success()` 生成 summary + `finalize_run()` 后 `commit()`。
  - 为什么存在：把任务成功终态与 summary 写入。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_collection_tasks.py:296`：`sync_databases()` 内，`start_run()` 后 `commit()`。
  - 为什么存在：确保 run_id 对应的 TaskRun 已落库，后续 `_is_cancelled()` 查询可见。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_collection_tasks.py:360`：`sync_databases()` 内，`init_items()` 后 `commit()`。
  - 为什么存在：把所有实例 item 的初始状态写入，便于 UI 提前看到待处理列表。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_collection_tasks.py:363`：`sync_databases()` 内，`runner.create_capacity_session()` 后 `commit()`。
  - 为什么存在：把会话与实例记录落库（包括 session_id 等），后续实例处理要引用。
  - 是否可收敛：KEEP。

### `app/tasks/capacity_aggregation_tasks.py`（13）

> 该文件的 commit 同样以“每实例进度 + 会话/TaskRun 终态”为主。

- `app/tasks/capacity_aggregation_tasks.py:96`：`_aggregate_instances()` 每实例 `start_item()` 后 `commit()`。
  - 为什么存在：实例 item 进入 running 的进度落库。
  - 是否可收敛：多半 KEEP。

- `app/tasks/capacity_aggregation_tasks.py:103`：`_aggregate_instances()` 每实例 `runner.start_instance_sync()` 后 `commit()`。
  - 为什么存在：把聚合 session 的“实例开始”状态写入。
  - 是否可收敛：多半 KEEP。

- `app/tasks/capacity_aggregation_tasks.py:123`：`_aggregate_instances()` 每实例 `runner.complete_instance_sync()` 后 `commit()`。
  - 为什么存在：把聚合 session 的“实例完成/失败 + 统计信息”写入。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:147`：`_aggregate_instances()` 每实例 `complete_item()/fail_item()` 后 `commit()`。
  - 为什么存在：TaskRunItem 的实例级终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:191`：`_handle_aggregation_task_exception()` 标记 session failed 后 `commit()`。
  - 为什么存在：异常时确保 session 终态落库（并尝试把未 finalize 的 record 标记失败）。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:229`：`_resolve_task_run_id()` 创建 TaskRun 后 `commit()`。
  - 为什么存在：run_id 需要立刻可见，供后续查询/取消判断。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:256`：`_finalize_skip_run()` 写 summary + `finalize_run()` 后 `commit()`。
  - 为什么存在：跳过也要落库终态。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:287`：`_handle_aggregation_task_failure()` 更新 TaskRun/TaskRunItem failed 并 `finalize_run()` 后 `commit()`。
  - 为什么存在：任务失败终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:389`：`calculate_database_aggregations()` 内 `init_items()` 后 `commit()`。
  - 为什么存在：提前写入实例 item 列表（便于 UI 可见/取消逻辑一致）。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:398`：`calculate_database_aggregations()` 内 `runner.init_aggregation_session()` 后 `commit()`。
  - 为什么存在：会话/记录落库，供后续 per-instance 聚合写入。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:424`：取消分支 `finalize_run()` 后 `commit()`。
  - 为什么存在：把取消终态持久化。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:437`：写入 session 汇总字段后 `commit()`。
  - 为什么存在：会话成功/失败实例数与完成时间落库。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_aggregation_tasks.py:454`：最终 `finalize_run()` 后 `commit()`。
  - 为什么存在：TaskRun 终态与 summary 落库。
  - 是否可收敛：KEEP。

### `app/tasks/accounts_sync_tasks.py`（12）

> 该文件 commit 的核心是：每实例同步的进度可见性（TaskRunItem + SyncInstanceRecord）以及会话/任务的最终摘要。

- `app/tasks/accounts_sync_tasks.py:83`：`_resolve_run_id()` 创建 TaskRun 后 `commit()`。
  - 为什么存在：run_id 立刻可见。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:110`：`_finalize_no_instances()` 跳过时 `finalize_run()` 后 `commit()`。
  - 为什么存在：跳过也需要终态/summary。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:126`：`_init_items()` 写入实例 item 初始化后 `commit()`。
  - 为什么存在：预先生成 item 列表，UI 可见。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:157`：`_create_records()` 添加 SyncInstanceRecord 并更新 `session.total_instances` 后 `commit()`。
  - 为什么存在：会话记录落库；后续 per-instance 更新依赖 record_id。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:192`：`_sync_instances()` 每实例 `start_item()` 后 `commit()`。
  - 为什么存在：实例 item running 落库。
  - 是否可收敛：多半 KEEP。

- `app/tasks/accounts_sync_tasks.py:195`：`_sync_instances()` 每实例 `sync_session_service.start_instance_sync()` 后 `commit()`。
  - 为什么存在：实例记录 running/started_at 落库。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:203`：`_sync_instances()` 运行 `_sync_single_instance()` 后 `commit()`。
  - 为什么存在：把该实例同步过程中产生的 DB 变更整体落库。
  - 是否可收敛：MAYBE（若 `_sync_single_instance()` 内部已经把关键节点分段提交，则可合并；但通常建议“每实例一次 commit”保持隔离）。

- `app/tasks/accounts_sync_tasks.py:235`：`_sync_instances()` 每实例 `complete_item()/fail_item()` 后 `commit()`。
  - 为什么存在：TaskRunItem 实例级终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:254`：`_finalize_success()` 写入 session 汇总字段后 `commit()`。
  - 为什么存在：会话统计/终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:272`：`_finalize_success()` `finalize_run()` 后 `commit()`。
  - 为什么存在：TaskRun summary/终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:300`：`_finalize_failure()` 标记 session failed 后 `commit()`。
  - 为什么存在：会话失败终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/accounts_sync_tasks.py:313`：`_finalize_failure()` 更新 TaskRun/TaskRunItem failed + `finalize_run()` 后 `commit()`。
  - 为什么存在：任务失败终态落库。
  - 是否可收敛：KEEP。

### `app/tasks/account_classification_auto_tasks.py`（10）

> 该任务允许“按规则逐条处理，部分成功”；commit 用于：规则维度的 item 进度 + 清空/写入分配后的持久化。

- `app/tasks/account_classification_auto_tasks.py:61`：`_resolve_run_id()` 创建 TaskRun 后 `commit()`。
  - 为什么存在：run_id 立刻可见。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_auto_tasks.py:136`：`_finalize_run_no_rules()` `finalize_run()` 后 `commit()`。
  - 为什么存在：无规则时写入失败终态。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_auto_tasks.py:183`：`_finalize_run_no_accounts()` `finalize_run()` 后 `commit()`。
  - 为什么存在：无账户时写入跳过/完成终态。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_auto_tasks.py:244`：`_finalize_rule_failure()` 更新 TaskRun/TaskRunItem failed 并 `finalize_run()` 后 `commit()`。
  - 为什么存在：规则处理失败时落库终态（随后抛出异常终止任务）。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_auto_tasks.py:273`：`_finalize_run_success()` `finalize_run()` 后 `commit()`。
  - 为什么存在：成功终态与 summary 落库。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_auto_tasks.py:340`：`auto_classify_accounts()` `init_items()` 后 `commit()`。
  - 为什么存在：规则 item 初始化可见。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_auto_tasks.py:353`：`cleanup_all_assignments()`（清空旧分配）后 `commit()`。
  - 为什么存在：重新分类是“先清空再写入”，清空需要先落库，避免后续失败时把新旧混在一个事务里。
  - 是否可收敛：MAYBE（如果希望“要么全部成功要么不改”，则不应该在这里 commit；但当前语义更偏向“阶段性落库 + 失败可定位/可重跑”）。

- `app/tasks/account_classification_auto_tasks.py:370`：取消分支 `finalize_run()` 后 `commit()`。
  - 为什么存在：取消终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_auto_tasks.py:382`：每规则 `start_item()` 后 `commit()`。
  - 为什么存在：规则 item running 落库。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_auto_tasks.py:410`：每规则 `complete_item()` 后 `commit()`。
  - 为什么存在：规则 item 完成终态落库。
  - 是否可收敛：KEEP。

### `app/tasks/account_classification_daily_tasks.py`（10）

> 该任务按“规则 -> 统计行 upsert”执行；commit 用于规则维度进度 + 任务终态写入。

- `app/tasks/account_classification_daily_tasks.py:52`：`_resolve_run_id()` 创建 TaskRun 后 `commit()`。
  - 为什么存在：run_id 立刻可见。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:85`：`_finalize_no_rules()` `finalize_run()` 后 `commit()`。
  - 为什么存在：无规则时失败终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:119`：`_finalize_no_accounts()` `finalize_run()` 后 `commit()`。
  - 为什么存在：无账户时失败终态落库（并把 item 标失败）。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:249`：`_finalize_rule_failure()` `finalize_run()` 后 `commit()`。
  - 为什么存在：规则处理失败时落库终态（随后抛出异常终止任务）。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:307`：`_finalize_success()` `finalize_run()` 后 `commit()`。
  - 为什么存在：成功终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:347`：`_finalize_task_failure()` 更新 TaskRun/TaskRunItem failed 后 `commit()`。
  - 为什么存在：任务失败终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:423`：`calculate_account_classification()` `init_items()` 后 `commit()`。
  - 为什么存在：规则 item 初始化可见。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:448`：取消分支 `finalize_run()` 后 `commit()`。
  - 为什么存在：取消终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:458`：每规则 `start_item()` 后 `commit()`。
  - 为什么存在：规则 item running 落库。
  - 是否可收敛：KEEP。

- `app/tasks/account_classification_daily_tasks.py:478`：每规则 `complete_item()` 后 `commit()`。
  - 为什么存在：规则 item 完成终态落库。
  - 是否可收敛：KEEP。

### `app/tasks/capacity_current_aggregation_tasks.py`（9）

> 该任务按“runner callback”写入实例级进度；commit 用于回调内的进度持久化与任务终态。

- `app/tasks/capacity_current_aggregation_tasks.py:67`：`_resolve_run_id()` 创建 TaskRun 后 `commit()`。
  - 为什么存在：run_id 立刻可见。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_current_aggregation_tasks.py:89`：`_init_items()` 初始化实例 item 后 `commit()`。
  - 为什么存在：提前生成 item 列表。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_current_aggregation_tasks.py:117`：`_write_summary()` 写入 TaskRun summary 后 `commit()`。
  - 为什么存在：把概览/周期信息落库，UI 能看到任务参数与当前状态。
  - 是否可收敛：MAYBE（如果 summary 只用于最终展示，可推迟到末尾一起提交；但当前写法更偏“过程可见”）。

- `app/tasks/capacity_current_aggregation_tasks.py:135`：`_finalize_cancelled()` `finalize_run()` 后 `commit()`。
  - 为什么存在：取消终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_current_aggregation_tasks.py:169`：`_finalize_error()` 更新 TaskRun/TaskRunItem failed 后 `commit()`。
  - 为什么存在：失败终态落库。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_current_aggregation_tasks.py:194`：`_AggregationCallbacks.on_start()` 每实例 start_item 后 `commit()`。
  - 为什么存在：回调驱动的实例级进度点。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_current_aggregation_tasks.py:224`：`_AggregationCallbacks.on_complete()` 每实例 complete/fail 后 `commit()`。
  - 为什么存在：回调驱动的实例级终态。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_current_aggregation_tasks.py:236`：`_AggregationCallbacks.on_error()` 每实例 error 后 `commit()`。
  - 为什么存在：回调驱动的失败落库。
  - 是否可收敛：KEEP。

- `app/tasks/capacity_current_aggregation_tasks.py:365`：`capacity_aggregate_current()` 末尾 `finalize_run()` 后 `commit()`。
  - 为什么存在：任务最终终态落库。
  - 是否可收敛：KEEP。

---

## B. `db.session.begin_nested()`（29）

> `begin_nested()` 的“必要场景”主要有两类：
> 1) **吞错继续（返回兜底值/继续处理下一条）**：必须用 savepoint 或显式 rollback，否则 session 会进入 failed 状态；
> 2) **循环内隔离（单条失败不影响整体）**：每条/每实例一个 savepoint，允许继续处理后续条目。
>
> 相反，“异常会向上抛出并由上层统一 rollback”的场景，`begin_nested()` 往往是可疑样板。

### `app/services/auth/change_password_service.py`

- `app/services/auth/change_password_service.py:48`：修改密码时对 `repository.add(user)` 用 `begin_nested()`。
  - 为什么存在：提供 savepoint，理论上允许捕获 flush 错误后继续复用 session。
  - 是否可收敛：CANDIDATE（当前实现捕获后直接抛错，且 Web 入口 `safe_route_call` 会 rollback；这一层 savepoint 可能是冗余样板）。

### `app/services/dashboard/dashboard_overview_service.py`

- `app/services/dashboard/dashboard_overview_service.py:36`：Dashboard overview 中，容量汇总查询用 `begin_nested()`。
  - 为什么存在：该段会吞掉 `SQLAlchemyError` 并使用兜底值继续返回；savepoint 用于避免查询失败污染整个 session。
  - 是否可收敛：KEEP（与“吞错继续”语义配套）。

### `app/services/statistics/log_statistics_service.py`

- `app/services/statistics/log_statistics_service.py:67`：趋势查询用 `begin_nested()`。
  - 为什么存在：查询失败会返回空列表（兜底），需要 savepoint 保证 session 可继续使用。
  - 是否可收敛：KEEP。

- `app/services/statistics/log_statistics_service.py:102`：级别分布查询用 `begin_nested()`。
  - 为什么存在：同上，吞错返回 `[]`。
  - 是否可收敛：KEEP。

### `app/services/tags/tag_write_service.py`

- `app/services/tags/tag_write_service.py:161`：批量删除标签时，每个 tag 删除用 `begin_nested()`。
  - 为什么存在：单个 tag 删除失败要继续处理下一个；savepoint 让“部分成功”成立。
  - 是否可收敛：KEEP（典型的“循环内隔离”）。

### `app/services/aggregation/instance_aggregation_runner.py`

- `app/services/aggregation/instance_aggregation_runner.py:153`：按实例循环聚合时，每实例一个 `begin_nested()`。
  - 为什么存在：某个实例聚合失败不影响其它实例；外层 `except` 会记录失败并继续。
  - 是否可收敛：KEEP。

- `app/services/aggregation/instance_aggregation_runner.py:303`：单实例聚合入口中，持久化聚合记录用 `begin_nested()`。
  - 为什么存在：与批量版本保持一致；也避免单次写入失败后污染 session。
  - 是否可收敛：MAYBE（若该入口失败直接抛错且上层会 rollback，可考虑删掉以减少样板）。

### `app/services/aggregation/database_aggregation_runner.py`

- `app/services/aggregation/database_aggregation_runner.py:150`：按实例循环数据库聚合时，每实例一个 `begin_nested()`。
  - 为什么存在：单实例失败不影响其它实例。
  - 是否可收敛：KEEP。

- `app/services/aggregation/database_aggregation_runner.py:270`：单实例聚合入口调用 `_aggregate_databases_for_instance()` 时使用 `begin_nested()`。
  - 为什么存在：与批量版本一致，隔离单次写入。
  - 是否可收敛：MAYBE（同上，若失败直接抛错且上层统一 rollback，这层可删）。

### `app/services/partition_management_service.py`

- `app/services/partition_management_service.py:142`：创建分区：外层 `begin_nested()`。
  - 为什么存在：把“创建分区的一组 DDL/操作”包装进一个可回滚的事务块（最终由上层 commit/rollback）。
  - 是否可收敛：MAYBE（真正必须的是“每分区一个 savepoint”；外层这层在 `safe_route_call` 存在时可能偏样板）。

- `app/services/partition_management_service.py:166`：创建分区：每张表/每个分区的 `begin_nested()`。
  - 为什么存在：单个分区创建失败要继续尝试其它分区；savepoint 让后续语句仍可执行。
  - 是否可收敛：KEEP。

- `app/services/partition_management_service.py:303`：清理分区：外层 `begin_nested()`。
  - 为什么存在：把“清理分区的一组 DDL/操作”包起来，方便整体 rollback。
  - 是否可收敛：MAYBE（同 142）。

- `app/services/partition_management_service.py:308`：清理分区：每个分区 drop 的 `begin_nested()`。
  - 为什么存在：单个分区 drop 失败要继续处理其它分区；savepoint。
  - 是否可收敛：KEEP。

### `app/services/sync_session_service.py`

- `app/services/sync_session_service.py:106`：`create_session()` 写入 SyncSession 时 `begin_nested()`。
  - 为什么存在：为 flush/写入提供 savepoint，避免异常污染 session。
  - 是否可收敛：MAYBE（异常会向上抛出且上层一般会 rollback；需要确认是否存在“捕获异常继续执行且不 rollback”的调用方）。

- `app/services/sync_session_service.py:163`：`add_instance_records()` 批量创建 SyncInstanceRecord 时 `begin_nested()`。
  - 为什么存在：批量写入时用 savepoint 包裹，减少“部分写入失败导致 session 不可用”的概率。
  - 是否可收敛：MAYBE（同上，取决于调用方是否会捕获后继续）。

- `app/services/sync_session_service.py:209`：`start_instance_sync()` 更新 record 状态并 flush 时 `begin_nested()`。
  - 为什么存在：为状态更新提供 savepoint。
  - 是否可收敛：MAYBE。

- `app/services/sync_session_service.py:258`：`complete_instance_sync()` 更新 record + 更新 session 统计时 `begin_nested()`。
  - 为什么存在：把 record 更新与统计更新作为一个可回滚单元；异常时不污染 session。
  - 是否可收敛：MAYBE（这里包含多次查询/flush，去掉 savepoint 可能会让异常处理更难；需要先确认调用方期望）。

- `app/services/sync_session_service.py:315`：`fail_instance_sync()` 更新 record + 更新 session 统计时 `begin_nested()`。
  - 为什么存在：同 258。
  - 是否可收敛：MAYBE。

- `app/services/sync_session_service.py:443`：`cancel_session()` 更新会话状态并 flush 时 `begin_nested()`。
  - 为什么存在：为取消动作提供 savepoint。
  - 是否可收敛：MAYBE。

### `app/services/accounts_sync/inventory_manager.py`

- `app/services/accounts_sync/inventory_manager.py:93`：实例账户清单同步（创建/激活/停用 + flush）用 `begin_nested()`。
  - 为什么存在：账户同步通常是“按实例循环、失败可记录并继续”；savepoint 让单实例同步失败不会把整个 session 置为 failed。
  - 是否可收敛：KEEP（与“按实例继续跑”的任务语义匹配）。

### `app/services/accounts_sync/permission_manager.py`

- `app/services/accounts_sync/permission_manager.py:202`：权限同步批量处理 + flush 用 `begin_nested()`。
  - 为什么存在：同上，隔离单实例/批量 flush 失败，允许上层记录失败并继续后续实例。
  - 是否可收敛：KEEP。

### `app/services/database_sync/inventory_manager.py`

- `app/services/database_sync/inventory_manager.py:91`：数据库清单同步（创建/激活/停用 + flush）用 `begin_nested()`。
  - 为什么存在：同 inventory/permission，同步任务希望“单实例失败不拖垮整个批次”。
  - 是否可收敛：KEEP。

### `app/repositories/capacity_persistence_repository.py`

- `app/repositories/capacity_persistence_repository.py:47`：批量 upsert `DatabaseSizeStat` 时 `begin_nested()`。
  - 为什么存在：upsert 失败时，若调用方选择捕获并继续，需要 savepoint 让 session 可继续使用。
  - 是否可收敛：MAYBE（如果调用方一律让异常上抛并 rollback，则这里属于可删样板）。

- `app/repositories/capacity_persistence_repository.py:71`：upsert `InstanceSizeStat` 时 `begin_nested()`。
  - 为什么存在：同上。
  - 是否可收敛：MAYBE。

### `app/repositories/database_table_size_stats_repository.py`

- `app/repositories/database_table_size_stats_repository.py:52`：upsert 最新表快照时 `begin_nested()`。
  - 为什么存在：同上，隔离单次 upsert 失败。
  - 是否可收敛：MAYBE。

- `app/repositories/database_table_size_stats_repository.py:74`：清理 removed snapshot 时 `begin_nested()`。
  - 为什么存在：delete+flush 的 savepoint。
  - 是否可收敛：MAYBE。

### `app/repositories/account_classification_daily_stats_repository.py`

- `app/repositories/account_classification_daily_stats_repository.py:61`：upsert 规则命中统计时 `begin_nested()`。
  - 为什么存在：批量 upsert 的 savepoint。
  - 是否可收敛：MAYBE。

- `app/repositories/account_classification_daily_stats_repository.py:87`：upsert 分类去重统计时 `begin_nested()`。
  - 为什么存在：同上。
  - 是否可收敛：MAYBE。

### `app/repositories/account_classification_repository.py`

- `app/repositories/account_classification_repository.py:157`：批量清理旧分配 + bulk_insert 新分配时 `begin_nested()`。
  - 为什么存在：该方法会吞掉 `SQLAlchemyError` 并返回 0；savepoint 用来确保失败后 session 不会被污染。
  - 是否可收敛：KEEP（在维持“吞错返回 0”语义的前提下）。

