# Code Simplicity Review (Minimalism / YAGNI)

生成时间：2026-01-27  
目标：列出本仓库当前代码的“非必要复杂度 / YAGNI 违背点 / 可删除点”，用于后续瘦身与可维护性治理。

> 说明：本报告是“发现清单”，不包含修复提交；其中部分属于“设计选择”而非 bug，但依然会增加维护成本。

---

## Core Purpose（项目必须做的事）

鲸落（WhaleFall）需要做的核心事情：为 DBA 团队提供数据库实例/账户/容量/任务调度的统一管理与审计（Flask 后端 + 任务/调度 + Web UI + `/api/v1/**` API）。

---

## Evidence（本次扫描依据）

- Python lint：`uv run ruff check app --output-format=concise`
- Python typecheck：`uv run pyright`（结果：0 errors）
- JS lint：`npx eslint app/static/js --ext .js`
- 结构与规模：按文件行数统计（Python/JS Top 列表）
- 关键模式扫描：`except Exception`、`fallback=True`、`pragma: no cover` 等关键字全仓 grep

---

## A) 静态分析直接报出的可简化点（完整清单）

### A.1 Python（ruff，共 33 条）

> 原始输出来自：`uv run ruff check app --output-format=concise`

- `app/repositories/account_classification_daily_stats_repository.py:45:29` - `B009`：不要用 `getattr(x, "__table__")` 访问常量属性名；直接 `x.__table__` 更简单。
- `app/repositories/account_classification_daily_stats_repository.py:71:29` - `B009`：同上。
- `app/routes/accounts/__init__.py:21:11` - `RUF022`：`__all__` 未排序（会制造 diff 噪音）。
- `app/services/account_classification/cache.py:58:33` - `UP037`：类型注解不需要引号。
- `app/services/account_classification/cache.py:81:37` - `UP037`：同上。
- `app/services/accounts/account_classifications_write_service.py:239:9` - `PLR0915`：语句过多（51 > 50），函数体过长。
- `app/services/accounts_sync/accounts_sync_service.py:45:44` - `UP037`：类型注解不需要引号。
- `app/services/accounts_sync/accounts_sync_service.py:224:9` - `PLR0912`：分支过多（17 > 12），流程编排/错误处理混杂。
- `app/services/cache/cache_actions_service.py:256:42` - `C420`：不必要的 dict comprehension；可用 `dict.fromkeys(...)`。
- `app/services/common/options_cache.py:83:48` - `UP037`：类型注解不需要引号。
- `app/services/common/options_cache.py:165:53` - `UP037`：类型注解不需要引号。
- `app/services/common/options_cache.py:172:53` - `UP037`：类型注解不需要引号。
- `app/tasks/account_classification_auto_tasks.py:31:5` - `PLR0912`：分支过多（25 > 12）。
- `app/tasks/account_classification_auto_tasks.py:31:5` - `PLR0915`：语句过多（108 > 50）。
- `app/tasks/account_classification_auto_tasks.py:110:33` - `RUF046`：对已经是整数的值重复 `int(...)`。
- `app/tasks/account_classification_auto_tasks.py:145:33` - `RUF046`：同上。
- `app/tasks/account_classification_auto_tasks.py:196:21` - `TRY301`：建议把 `raise` 抽到内部函数以减少主流程噪音。
- `app/tasks/account_classification_auto_tasks.py:199:21` - `TRY301`：同上。
- `app/tasks/account_classification_auto_tasks.py:205:25` - `TRY301`：同上。
- `app/tasks/account_classification_auto_tasks.py:223:31` - `RUF046`：重复 `int(...)`。
- `app/tasks/account_classification_auto_tasks.py:284:29` - `RUF046`：重复 `int(...)`。
- `app/tasks/account_classification_daily_tasks.py:24:5` - `PLR0912`：分支过多（33 > 12）。
- `app/tasks/account_classification_daily_tasks.py:24:5` - `PLR0915`：语句过多（146 > 50）。
- `app/tasks/account_classification_daily_tasks.py:230:35` - `RUF046`：重复 `int(...)`。
- `app/tasks/accounts_sync_tasks.py:166:5` - `PLR0912`：分支过多（21 > 12）。
- `app/tasks/accounts_sync_tasks.py:166:5` - `PLR0915`：语句过多（105 > 50）。
- `app/tasks/accounts_sync_tasks.py:264:13` - `RET505`：`return` 后的 `else` 多余。
- `app/tasks/capacity_aggregation_tasks.py:201:5` - `PLR0915`：语句过多（75 > 50）。
- `app/tasks/capacity_collection_tasks.py:114:5` - `PLR0912`：分支过多（14 > 12）。
- `app/tasks/capacity_collection_tasks.py:114:5` - `PLR0915`：语句过多（76 > 50）。
- `app/tasks/capacity_collection_tasks.py:326:13` - `TRY300`：建议把语句移到 `else` 块（减少 try 作用域）。
- `app/tasks/capacity_current_aggregation_tasks.py:40:5` - `PLR0912`：分支过多（13 > 12）。
- `app/tasks/capacity_current_aggregation_tasks.py:40:5` - `PLR0915`：语句过多（89 > 50）。

### A.2 JavaScript（eslint，共 2 条 warning）

> 原始输出来自：`npx eslint app/static/js --ext .js`

- `app/static/js/common/grid-table.js:29:25` - `security/detect-object-injection`：动态 key 读 `result[key]`。
- `app/static/js/common/grid-table.js:39:7` - `security/detect-object-injection`：动态 key 写 `result[key] = ...`。

---

## B) 单文件过大（高维护成本/天然倾向继续膨胀）

### B.1 Python Top 20（按行数）

- `app/services/accounts_sync/adapters/sqlserver_adapter.py`（1375）
- `app/services/accounts_sync/permission_manager.py`（1102）
- `app/api/v1/namespaces/accounts.py`（966）
- `app/api/v1/namespaces/instances.py`（902）
- `app/services/accounts_sync/adapters/mysql_adapter.py`（891）
- `app/services/aggregation/aggregation_service.py`（841）
- `app/api/v1/namespaces/accounts_classifications.py`（837）
- `app/api/v1/namespaces/tags.py`（722）
- `app/services/partition_management_service.py`（635）
- `app/api/v1/namespaces/databases.py`（634）
- `app/utils/structlog_config.py`（618）
- `app/scheduler.py`（583）
- `app/services/aggregation/instance_aggregation_runner.py`（565）
- `app/services/aggregation/database_aggregation_runner.py`（560）
- `app/settings.py`（558）
- `app/services/accounts/account_classifications_write_service.py`（513）
- `app/services/accounts_sync/accounts_sync_service.py`（503）
- `app/__init__.py`（477）
- `app/schemas/account_classifications.py`（476）
- `app/services/partition/partition_read_service.py`（473）

### B.2 JS Top 20（按行数）

- `app/static/js/modules/views/instances/detail.js`（2123）
- `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js`（1429）
- `app/static/js/modules/views/instances/list.js`（1348）
- `app/static/js/modules/views/accounts/classification_statistics.js`（1055）
- `app/static/js/modules/views/components/charts/manager.js`（982）
- `app/static/js/modules/views/history/sessions/sync-sessions.js`（914）
- `app/static/js/modules/views/admin/scheduler/index.js`（908）
- `app/static/js/modules/stores/instance_store.js`（846）
- `app/static/js/modules/views/components/tags/tag-selector-controller.js`（805）
- `app/static/js/modules/views/accounts/account-classification/index.js`（778）
- `app/static/js/modules/views/accounts/ledgers.js`（776）
- `app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js`（727）
- `app/static/js/modules/views/tags/batch-assign.js`（707）
- `app/static/js/modules/views/admin/partitions/charts/partitions-chart.js`（669）
- `app/static/js/modules/views/history/logs/logs.js`（660）
- `app/static/js/modules/views/history/sessions/session-detail.js`（651）
- `app/static/js/modules/stores/tag_management_store.js`（622）
- `app/static/js/modules/views/instances/statistics.js`（605）
- `app/static/js/modules/views/components/permissions/permission-modal.js`（602）
- `app/static/js/modules/views/tags/index.js`（567）

---

## C) 前端“防御性 fallback”过多（YAGNI / 不确定行为源头）

本节为“全量清单”。扫描范围：`app/static/js/**`（排除 `app/static/vendor/**`、`dist/**`），聚焦“为了缺依赖也能跑”的 fallback/注入/替代实现（这些会扩大不确定行为面，并制造维护噪音）。

### C.1 `toast` 默认实现（fallback 到 `console.*`，共 5 处）

- `app/static/js/modules/views/tags/batch-assign.js:42`
- `app/static/js/modules/views/instances/detail.js:11`
- `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:9`
- `app/static/js/modules/views/admin/scheduler/index.js:11`
- `app/static/js/modules/views/accounts/account-classification/index.js:91`

### C.2 DOM helpers 兜底 stub（`helpersFallback` + 解构回退，共 2 处）

- `app/static/js/modules/views/instances/detail.js:21`
- `app/static/js/modules/views/instances/detail.js:28`

### C.3 `logErrorWithContext` 默认实现（fallback 到 `console.error`，共 1 处）

- `app/static/js/modules/views/accounts/account-classification/index.js:99`

### C.4 其它 fallback 函数/空函数兜底（共 7 处）

- `app/static/js/modules/views/components/change-history/change-history-renderer.js:4`（`escapeHtml` 兜底函数）
- `app/static/js/modules/views/components/tags/tag-selector-view.js:121`（handler 兜底空函数）
- `app/static/js/modules/views/components/tags/tag-selector-view.js:122`（handler 兜底空函数）
- `app/static/js/modules/views/components/tags/tag-selector-view.js:123`（handler 兜底空函数）
- `app/static/js/modules/views/components/tags/tag-selector-modal-adapter.js:51`（modal 方法兜底空函数）
- `app/static/js/modules/views/components/tags/tag-selector-modal-adapter.js:52`（modal 方法兜底空函数）
- `app/static/js/modules/views/components/tags/tag-selector-modal-adapter.js:53`（modal 方法兜底空函数）

### C.5 HTTP client 解析回退链（`client || global.httpU || global.http || null`，共 18 处）

- `app/static/js/modules/services/account_change_logs_service.js:7`
- `app/static/js/modules/services/account_classification_service.js:15`
- `app/static/js/modules/services/account_classification_statistics_service.js:7`
- `app/static/js/modules/services/accounts_statistics_service.js:14`
- `app/static/js/modules/services/auth_service.js:17`
- `app/static/js/modules/services/capacity_stats_service.js:22`
- `app/static/js/modules/services/connection_service.js:14`
- `app/static/js/modules/services/credentials_service.js:14`
- `app/static/js/modules/services/dashboard_service.js:12`
- `app/static/js/modules/services/instance_management_service.js:12`
- `app/static/js/modules/services/instance_service.js:14`
- `app/static/js/modules/services/logs_service.js:14`
- `app/static/js/modules/services/partition_service.js:14`
- `app/static/js/modules/services/permission_service.js:12`
- `app/static/js/modules/services/scheduler_service.js:14`
- `app/static/js/modules/services/tag_management_service.js:23`
- `app/static/js/modules/services/task_runs_service.js:7`
- `app/static/js/modules/services/user_service.js:14`

### C.6 依赖回退到 `null`（显式把“缺依赖”变成“可空继续跑”，共 16 处）

- `app/static/js/modules/stores/tag_batch_store.js:41`（`lodash || window.LodashUtils || null`）
- `app/static/js/modules/views/instances/detail.js:10`（`window.connectionManager || null`）
- `app/static/js/modules/views/components/charts/manager.js:17`（`window.toast || null`）
- `app/static/js/modules/views/components/charts/manager.js:18`（`window.EventBus || null`）
- `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:4`（`window.GridTable || null`）
- `app/static/js/modules/views/grid-page.js:110`（`UI: global.UI || null`）
- `app/static/js/modules/views/grid-page.js:111`（`toast: global.toast || null`）
- `app/static/js/modules/views/accounts/classification_statistics.js:1000`（`global.ColorTokens || null`）
- `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:32`（`global.Views?.GridPage || null`）
- `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:33`（`global.Views?.GridPlugins || null`）
- `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:38`（`global.UI?.escapeHtml || null`）
- `app/static/js/modules/views/history/account-change-logs/account-change-logs.js:39`（`global.GridRowMeta || null`）
- `app/static/js/modules/views/history/logs/logs.js:48`（`global.Views?.GridPage || null`）
- `app/static/js/modules/views/history/logs/logs.js:49`（`global.Views?.GridPlugins || null`）
- `app/static/js/modules/views/history/logs/logs.js:54`（`global.UI?.escapeHtml || null`）
- `app/static/js/modules/views/history/logs/logs.js:55`（`global.GridRowMeta || null`）

### C.7 UI 行为回退（toast 不存在则退回 `alert`，共 2 处）

- `app/static/js/modules/views/admin/partitions/index.js:347`
- `app/static/js/modules/views/admin/partitions/index.js:359`

### C.8 全局命名空间注入（`global/window.X = ... || {}`，共 22 处）

- `app/static/js/common/grid-row-meta.js:11`
- `app/static/js/common/table-query-params.js:103`
- `app/static/js/modules/ui/async-action-feedback.js:132`
- `app/static/js/modules/ui/button-loading.js:149`
- `app/static/js/modules/ui/danger-confirm.js:223`
- `app/static/js/modules/ui/filter-card.js:352`
- `app/static/js/modules/ui/modal.js:204`
- `app/static/js/modules/ui/terms.js:91`
- `app/static/js/modules/ui/terms.js:92`
- `app/static/js/modules/ui/ui-helpers.js:92`
- `app/static/js/modules/views/grid-page.js:286`
- `app/static/js/modules/views/grid-page.js:287`
- `app/static/js/modules/views/grid-plugins/action-delegation.js:46`
- `app/static/js/modules/views/grid-plugins/action-delegation.js:47`
- `app/static/js/modules/views/grid-plugins/export-button.js:55`
- `app/static/js/modules/views/grid-plugins/export-button.js:56`
- `app/static/js/modules/views/grid-plugins/filter-card.js:47`
- `app/static/js/modules/views/grid-plugins/filter-card.js:48`
- `app/static/js/modules/views/grid-plugins/url-sync.js:30`
- `app/static/js/modules/views/grid-plugins/url-sync.js:31`
- `app/static/js/modules/views/components/charts/manager.js:980`
- `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js:290`

### C.9 存在 Tab 缩进/格式噪音的文件（按文件列出，共 4 个）

- `app/static/js/modules/views/accounts/ledgers.js`
- `app/static/js/modules/views/components/connection-manager.js`
- `app/static/js/modules/views/instances/detail.js`
- `app/static/js/modules/views/instances/list.js`

---

## D) catch-all `except Exception`（完整清单）

> 说明：catch-all 并不一定错误，但会显著扩大“不可预期行为”范围；应优先改为捕获已知异常集合，或抽统一失败路径。

- `app/__init__.py:177`
- `app/api/v1/namespaces/instances.py:408`
- `app/infra/logging/queue_worker.py:185`
- `app/infra/route_safety.py:165`
- `app/infra/route_safety.py:180`
- `app/models/account_permission.py:104`（`# pragma: no cover`）
- `app/routes/accounts/statistics.py:46`
- `app/routes/instances/statistics.py:45`
- `app/schemas/capacity_query.py:38`
- `app/schemas/databases_query.py:59`
- `app/schemas/partitions.py:45`
- `app/services/accounts/account_classifications_read_service.py:42`
- `app/services/accounts/account_classifications_read_service.py:49`
- `app/services/accounts/account_classifications_read_service.py:72`
- `app/services/accounts/account_classifications_read_service.py:80`
- `app/services/accounts/account_classifications_read_service.py:108`
- `app/services/accounts/account_classifications_read_service.py:132`
- `app/services/accounts/account_classifications_read_service.py:168`
- `app/services/accounts/account_classifications_read_service.py:198`
- `app/services/accounts/account_classifications_read_service.py:220`
- `app/services/accounts/account_classifications_read_service.py:232`
- `app/services/accounts_sync/accounts_sync_service.py:322`（`# pragma: no cover`）
- `app/services/accounts_sync/permission_manager.py:452`（`# pragma: no cover`）
- `app/services/cache/cache_actions_service.py:179`
- `app/services/cache/cache_actions_service.py:245`
- `app/services/capacity/instance_capacity_sync_actions_service.py:119`
- `app/services/connection_adapters/adapters/oracle_adapter.py:75`（`# pragma: no cover`）
- `app/services/database_sync/table_size_adapters/oracle_adapter.py:80`
- `app/services/history_account_change_logs/history_account_change_logs_read_service.py:73`
- `app/services/history_account_change_logs/history_account_change_logs_read_service.py:129`
- `app/services/history_sessions/history_sessions_read_service.py:124`
- `app/services/ledgers/accounts_ledger_change_history_service.py:78`
- `app/services/ledgers/database_ledger_service.py:90`
- `app/services/ledgers/database_ledger_service.py:141`
- `app/services/partition/partition_read_service.py:50`
- `app/services/partition/partition_read_service.py:74`
- `app/services/partition/partition_read_service.py:155`
- `app/services/scheduler/scheduler_jobs_read_service.py:45`
- `app/services/scheduler/scheduler_jobs_read_service.py:58`
- `app/services/statistics/account_statistics_service.py:47`
- `app/services/statistics/account_statistics_service.py:76`
- `app/services/statistics/account_statistics_service.py:103`
- `app/services/statistics/account_statistics_service.py:126`
- `app/services/statistics/account_statistics_service.py:152`
- `app/services/sync_session_service.py:108`
- `app/services/sync_session_service.py:175`
- `app/services/sync_session_service.py:212`
- `app/services/sync_session_service.py:271`
- `app/services/sync_session_service.py:322`
- `app/services/sync_session_service.py:373`
- `app/services/sync_session_service.py:394`
- `app/services/sync_session_service.py:415`
- `app/services/sync_session_service.py:450`
- `app/tasks/account_classification_auto_tasks.py:246`
- `app/tasks/account_classification_daily_tasks.py:249`
- `app/tasks/account_classification_daily_tasks.py:330`
- `app/tasks/capacity_collection_tasks.py:83`（`# pragma: no cover`）
- `app/tasks/capacity_collection_tasks.py:339`（`# pragma: no cover`）
- `app/tasks/capacity_current_aggregation_tasks.py:200`
- `app/utils/structlog_config.py:591`

---

## E) 显式“回退/降级”日志（`fallback=True`，完整清单）

> 说明：若无法证明这些 fallback 分支在真实环境必需，它们通常属于“以防万一”的 YAGNI；应逐个评估是否该删/该 fail-fast。

- `app/services/accounts_sync/permission_manager.py:457`
- `app/services/accounts_sync/adapters/mysql_adapter.py:80`
- `app/services/accounts_sync/adapters/mysql_adapter.py:252`
- `app/services/history_sessions/history_sessions_read_service.py:115`
- `app/tasks/capacity_collection_tasks.py:94`
- `app/services/capacity/instance_capacity_sync_actions_service.py:124`
- `app/services/connection_adapters/adapters/oracle_adapter.py:81`
- `app/services/connection_adapters/adapters/oracle_adapter.py:240`
- `app/services/connection_adapters/adapters/mysql_adapter.py:192`
- `app/services/connection_adapters/adapters/postgresql_adapter.py:179`
- `app/services/connection_adapters/adapters/sqlserver_adapter.py:231`
- `app/services/ledgers/accounts_ledger_change_history_service.py:69`
- `app/services/database_sync/table_size_adapters/oracle_adapter.py:86`
- `app/utils/cache_utils.py:91`
- `app/utils/cache_utils.py:120`
- `app/utils/cache_utils.py:146`
- `app/utils/cache_utils.py:164`
- `app/__init__.py:184`
- `app/models/account_permission.py:25`

---

## F) `# pragma: no cover`（完整清单）

> 说明：Protocol/纯类型辅助的 no cover 可以接受，但“关键业务流程的 defensive no cover”往往意味着不可测/不可控。

- `app/services/scheduler/scheduler_job_write_service.py:27`
- `app/services/scheduler/scheduler_actions_service.py:128`
- `app/services/accounts_sync/accounts_sync_service.py:322`
- `app/services/tags/tag_write_service.py:166`
- `app/services/accounts_sync/accounts_sync_actions_service.py:94`
- `app/services/database_sync/adapters/mysql_adapter.py:124`
- `app/services/accounts_sync/permission_manager.py:452`
- `app/services/database_sync/database_filters.py:69`
- `app/services/connection_adapters/adapters/oracle_adapter.py:75`
- `app/services/capacity/capacity_collection_actions_service.py:64`
- `app/repositories/ledgers/accounts_ledger_repository.py:189`
- `app/services/capacity/capacity_current_aggregation_actions_service.py:78`
- `app/services/account_classification/auto_classify_actions_service.py:68`
- `app/services/aggregation/aggregation_service.py:157`
- `app/services/aggregation/aggregation_service.py:417`
- `app/services/aggregation/aggregation_service.py:484`
- `app/services/partition_management_service.py:194`
- `app/services/partition_management_service.py:326`
- `app/services/partition_management_service.py:447`
- `app/services/aggregation/instance_aggregation_runner.py:108`
- `app/services/aggregation/instance_aggregation_runner.py:212`
- `app/services/aggregation/instance_aggregation_runner.py:422`
- `app/services/aggregation/instance_aggregation_runner.py:440`
- `app/services/aggregation/instance_aggregation_runner.py:532`
- `app/services/aggregation/capacity_aggregation_task_runner.py:311`
- `app/services/aggregation/database_aggregation_runner.py:105`
- `app/services/aggregation/database_aggregation_runner.py:205`
- `app/services/aggregation/database_aggregation_runner.py:512`
- `app/core/types/credentials.py:24`
- `app/core/types/dbapi.py:11`
- `app/core/types/dbapi.py:15`
- `app/core/types/dbapi.py:19`
- `app/core/types/dbapi.py:27`
- `app/core/types/dbapi.py:31`
- `app/core/types/sync.py:15`
- `app/core/types/sync.py:19`
- `app/api/v1/namespaces/instances_connections.py:222`
- `app/tasks/capacity_aggregation_tasks.py:181`
- `app/models/account_permission.py:104`
- `app/models/permission_config.py:68`
- `app/tasks/capacity_collection_tasks.py:83`
- `app/tasks/capacity_collection_tasks.py:339`

---

## G) 过宽异常集合 + 吞错返回空结果（“把 bug 当成无数据”）

- `app/services/accounts_sync/adapters/sqlserver_adapter.py:31`：`SQLSERVER_ADAPTER_EXCEPTIONS` 含 `KeyError/AttributeError` 等编程错误；并在 `_fetch_raw_accounts` 捕获后直接 `return []`（隐藏真实问题）。
- `app/services/accounts_sync/adapters/mysql_adapter.py:53`：`MYSQL_ADAPTER_EXCEPTIONS` 含 `KeyError/AttributeError`；`_has_mysql_user_column` 捕获后当“不存在列”继续（可能把真实错误当成“兼容差异”）。

---

## H) 魔法字符串 / 常量重复导致语义漂移

- `app/core/constants/status_types.py`：`SyncStatus` 与 `TaskRunStatus` 基本重复（维护两个来源会漂移）。
- `app/models/task_run.py:32`：`TaskRun.status` 默认值直接写 `"running"`，未复用常量（与 `TaskRunItem` 使用 `TaskRunStatus` 不一致）。

---

## I) 统计/聚合实现“复杂但不划算”（且疑似口径错误）

- `app/repositories/account_statistics_repository.py:124`：`fetch_db_type_stats()` 逐 db_type `.all()` 拉全量再 Python 计数；可用 SQL 聚合一次拿齐，代码更短更快。
- `app/repositories/account_statistics_repository.py:104`：`total_instances = active_instances`（看起来像口径错误/字段冗余）。

---

## J) 文档/报告漂移（无效复杂度）

- `README.md:148`：写 `http://localhost:5000`，但本地启动默认端口是 `5001`（`app.py:24-26`）。
- `docs/reports/clean-code-analysis.md:161` / `docs/reports/clean-code-analysis.md:341`：引用不存在的 `services/cache_service.py`（当前仓库无该文件），说明报告已过期。
- `docs/reports/clean-code-analysis.md:52` / `docs/reports/clean-code-analysis.md:693`：提到 Celery，但仓库内未发现 `celery`/`Celery` 实际使用（需确认是否历史遗留/文档误导）。

---

## K) 明确可删（YAGNI，当前仓库未使用/无收益）

- `app/infra/route_safety.py:115` + `app/infra/route_safety.py:116`：`safe_route_call` 的 `func_args/func_kwargs`（仓库内未发现调用方传入，属于“预留扩展点”）。
- `app/static/js/modules/views/errors`：空目录（纯噪音）。

---

## L) 其它“复杂度指标”（用于后续治理量化）

- `getattr(..., "literal")` 类模式在 Python 侧出现约 297 次（排除 `app/static/**`），其中部分属于“过度防御性/动态结构”使用；建议按模块逐步收敛到明确类型与字段访问。
- `db.session.commit()` 在 `app/**` 约出现 69 次（事务边界分散，容易出现“到处 commit”的维护成本）。
- `TaskRun.query.filter_by(run_id=...)` 约出现 35 次（同一套 run 生命周期逻辑在多处复制粘贴的信号）。

---

## 简化优先级建议（不等于修复计划）

1. 先收敛任务类代码：抽一个最小的 TaskRun 执行器（run 创建/取消/失败收敛/finalize）。
2. 收紧适配器异常捕获范围，禁止把 `KeyError/AttributeError` 当成可恢复错误。
3. 统一状态常量来源（减少魔法字符串）。
4. 把统计类 `.all()` + Python loop 改为 SQL 聚合（更短、更快、更不易错）。
5. 前端大文件拆分，并移除“假对象 fallback”，依赖缺失直接 fail-fast。
