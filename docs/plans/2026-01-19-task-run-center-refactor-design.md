# TaskRun Center Refactor Design

**Date:** 2026-01-19

## 背景/问题

当前“会话中心”只展示 `SyncSession/SyncInstanceRecord`（同步会话）。
新加入的定时任务（如账户分类每日统计）不创建 `SyncSession`，因此无法在会话中心被跟踪与定位。

本方案将会话中心升级为“通用任务运行中心”，引入 `TaskRun/TaskRunItem` 作为所有后台任务（scheduler/API action/手动触发）的统一观测面。

## 目标(Goals)

- 以 `TaskRun/TaskRunItem` 统一承载异步/定时/批量任务的可观测性：列表、详情、进度、错误、取消。
- `run_id` 作为统一标识（对外接口统一返回/使用 `run_id`，不再使用 `session_id`）。
- 账户分类每日统计：以“规则”为粒度生成 `TaskRunItem`，能在运行中心看到每条规则的执行结果。
- 所有页面按钮/动作入口统一改为**异步模式**：action endpoint 立即返回 `run_id`，不阻塞等待任务完成；UI 不做轮询（模式 1），统一 toast + 提供运行中心入口。
- 不迁移历史 `sync_sessions/sync_instance_records` 数据（新系统上线后历史不可见/不需要）。

## 非目标(Non-goals)

- 不做历史数据迁移/合并展示。
- 不在本阶段实现“强制终止线程/进程”的取消（只做 DB 状态标记 + 循环边界尽力提前退出）。

## 核心概念

- `TaskRun`：一次任务执行（一个 run）。
- `TaskRunItem`：run 内的子执行单元（实例/规则/步骤）。
  - 实例型任务：一台实例一个 item。
  - 规则型任务：一条规则一个 item。
  - 单体任务：一个 `step` item（保证 UI 统一）。

状态集合建议复用现有字符串（减少 UI/Terms 适配成本）：
- run.status：`running/completed/failed/cancelled`
- item.status：`pending/running/completed/failed/cancelled`

## 数据模型设计

### 1) 表：`task_runs`

字段建议：
- `id` (int, pk)
- `run_id` (String(36), unique, index)  # uuid
- `task_key` (String(128), index)  # 稳定标识：scheduler job_id / action 名
- `task_name` (String(255))  # 展示名
- `task_category` (String(50), index)  # account/capacity/aggregation/classification/other
- `trigger_source` (String(20), index)  # scheduled/manual/api
- `status` (String(20), index)
- `started_at` (timestamptz, index)
- `completed_at` (timestamptz, nullable)
- `created_by` (int, nullable)
- `progress_total` (int, default 0)
- `progress_completed` (int, default 0)
- `progress_failed` (int, default 0)
- `summary_json` (JSON/JSONB, nullable)  # 任务级摘要（stat_date、总量等）
- `result_url` (String(255), nullable)  # 结果入口
- `error_message` (Text, nullable)  # run 级摘要错误
- `created_at/updated_at` (timestamptz)

约束/索引：
- Unique(`run_id`)
- Index(`task_key`, `started_at`)

### 2) 表：`task_run_items`

字段建议：
- `id` (int, pk)
- `run_id` (String(36), fk -> task_runs.run_id, index)
- `item_type` (String(20), index)  # instance/rule/step
- `item_key` (String(128), index)  # instance_id / rule_id / step_name
- `item_name` (String(255), nullable)  # 展示名
- `instance_id` (int, nullable, index)  # 仅 instance item 使用
- `status` (String(20), index)
- `started_at/completed_at` (timestamptz)
- `metrics_json` (JSON/JSONB, nullable)  # 关键指标（命中数、写入行数、耗时等）
- `details_json` (JSON/JSONB, nullable)  # 明细（规则表达式摘要、db_type、错误上下文等）
- `error_message` (Text, nullable)
- `created_at/updated_at` (timestamptz)

约束/索引：
- Unique(`run_id`, `item_type`, `item_key`)  # 同一 run 内同一子单元只保留一条
- Index(`run_id`, `status`)

## 服务层(Write/Read)

### Write Service（任务侧接入）

提供一个统一写入门面（示例命名）：`TaskRunsWriteService`
- `start_run(task_key, task_name, task_category, trigger_source, created_by, summary_json, result_url) -> run_id`
- `init_items(run_id, items: list[{item_type,item_key,item_name,instance_id?}])`  # 批量创建 pending items，并同步 progress_total
- `start_item(run_id, item_type, item_key)`
- `complete_item(run_id, item_type, item_key, metrics_json=None, details_json=None)`
- `fail_item(run_id, item_type, item_key, error_message, details_json=None)`
- `finalize_run(run_id)`：根据 items 聚合写入 run 的 `progress_completed/progress_failed` 与 `status/completed_at`
- `cancel_run(run_id)`：仅允许 `running` -> `cancelled`，并把未开始/运行中的 items 标为 `cancelled`

实现要点：
- 所有写操作在“任务边界”明确 commit/rollback（任务函数与 action service 控制）。
- 进度聚合：优先从 items count 聚合，run 内冗余字段用于列表页快速展示。

### Read Service（会话中心/运行中心）

- `list_runs(filters) -> PaginatedResult[TaskRunListItem]`
- `get_run_detail(run_id) -> TaskRunDetail`（包含 items 列表）
- `get_run_error_logs(run_id)`：从 failed items 聚合输出（用于详情 modal 的“错误堆栈”区域）

## API 设计（v1）

新增 namespace：`/api/v1/task-runs`

- `GET /api/v1/task-runs`
  - query：`task_key`、`task_category`、`trigger_source`、`status`、`page/limit/sort/order`
  - 返回：items/total/page/pages（封套同现有 API）

- `GET /api/v1/task-runs/{run_id}`
  - 返回：run + items

- `GET /api/v1/task-runs/{run_id}/error-logs`
  - 返回：failed items 列表 + error_count

- `POST /api/v1/task-runs/{run_id}/actions/cancel`
  - admin 权限 + CSRF
  - 语义：标记取消（不强杀）

**run_id 字段统一：**
- 所有触发异步任务的 action endpoint：统一返回 `data.run_id`。
- 前端 async outcome helper：支持读取 `run_id` 并携带到 meta/埋点。

## 异步动作统一契约（UI 按钮/Action Endpoint）

统一要求：
- action endpoint **不得阻塞**等待任务完成；必须“创建 run -> 返回 run_id -> 后台执行”。
- UI（模式 1）：不轮询 `run_id`；只提示“已启动”并提供 `/history/sessions` 入口；需要查看结果/错误统一去运行中心。

推荐返回结构（封套以现有 API 标准为准）：
- success: `True`
- data: `{ "run_id": "<uuid>" }`
- message: “任务已在后台启动，请稍后在运行中心查看”

## Web UI（/history/sessions 复用路径）

保持入口路径不变（`/history/sessions`），但语义/文案升级为“运行中心”。

列表页：
- 数据源从 `/api/v1/sync-sessions` 切换为 `/api/v1/task-runs`。
- 筛选项：`trigger_source`、`task_category`、`status`。
- 列建议：`run_id(截断)`、`status`、`progress`、`task_name/task_key`、`trigger_source`、`task_category`、`started_at`、`duration`、`actions(view/cancel)`。

详情 modal：
- Header：任务名 + run_id + 状态
- 摘要：summary_json（如 stat_date、counts）
- Items：按 `item_type` 分组/列表展示（规则/实例/步骤）
- 错误堆栈：聚合 failed items 的 `error_message/details_json`（与现有样式一致）
- CTA：若 `result_url` 存在，展示“前往结果页”链接

## 任务接入清单（Scheduler + 页面按钮）

> 约定：页面按钮触发的均归类为 `trigger_source=manual`（由 `created_by` 记录操作者）；scheduler cron 触发为 `trigger_source=scheduled`。

### A) Scheduler jobs（内置任务）

这些任务来自 `app/config/scheduler_tasks.yaml`，需统一写入 `TaskRun`：
- `sync_accounts`: 账户同步 (items=instance)
- `sync_databases`: 数据库同步 (items=instance; 包含 inventory + 容量采集)
- `calculate_database_aggregations`: 统计数据库聚合 (items=instance)
- `calculate_account_classification`: 统计账户分类 (items=rule, 见下节)

### B) 页面按钮（本次重构必须覆盖）

1) 账户台账「同步所有账户」
- task_key：`sync_accounts`
- items：instance（每实例一个 item）
- result_url：`/accounts/ledgers`

2) 数据库台账「同步所有数据库」(新增按钮, 清单 + 容量)
- task_key: `sync_databases`
- items: instance
- result_url: `/databases/ledgers`

3) 账户分类管理「自动分类」
- task_key：`auto_classify_accounts`
- items：rule（每条 active rule 一个 item；几十条规则可完整展示）
- result_url：`/accounts/classifications`

4) 容量统计（实例/数据库两个页面）「统计当前周期」
- task_key：`capacity_aggregate_current`
- items：instance（聚合回调按实例推进）
- result_url：按入口页面：`/capacity/instances` 或 `/capacity/databases`
- UI 交互（模式 1）：点击后仅提示“已启动”，不阻塞等待聚合完成；用户可在运行中心查看进度/失败项，完成后手动刷新页面数据。

## 任务接入：账户分类每日统计（规则粒度）

将 `calculate_account_classification` 接入 TaskRun:
- `TaskRun.task_key = "calculate_account_classification"`
- `TaskRun.task_category = "classification"`
- `TaskRun.trigger_source = scheduled/manual`
- `TaskRun.summary_json`：`stat_date/rules_count/accounts_count/rule_match_rows/classification_match_rows`
- items：每条 active rule 1 个 `TaskRunItem`
  - `item_type="rule"`
  - `item_key=str(rule_id)`
  - `item_name=rule_name`（或 `classification_code + rule_version`）
  - `metrics_json`：`matched_accounts_total`、`rule_match_rows_written`、`duration_ms`、`instances_covered`

失败语义（建议 fail-fast）：
- 任意 rule item failed -> run 标记 failed，任务结束返回失败（避免统计口径“部分成功但用户不知情”）。

## 迁移策略（不迁移历史）

- 一次性切换：会话中心 UI 与所有任务写入全面改为 TaskRun。
- 不读取/不展示 `sync_sessions` 历史。
- 旧表是否删除：作为后续运维清理任务单独处理（避免一次 PR 做破坏性变更）。

## 验收标准(DoD)

- 会话中心(运行中心)能展示: 账户同步/数据库同步/聚合/统计账户分类(至少覆盖现有 builtin jobs).
- 任意任务触发成功返回 `run_id`，前端提示与结果入口指向 `/history/sessions`。
- 账户分类统计 run 里能看到按规则的 item 列表，失败时能定位到具体 rule。
- cancel action 能把 run 标记 cancelled，并在任务循环边界尽力提前退出。
- 单测覆盖：API contract（list/detail/error-logs/cancel）+ write service 状态流转。
