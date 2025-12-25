# 001 后端 Repository / Serializer 分层重构 - 进度

> 关联方案：`docs/changes/refactor/001-backend-repository-serializer-boundary-plan.md`
>
> 开始日期：2025-12-25
>
> 最后更新：2025-12-25

## 当前状态

- 已落地样板：`GET /instances/api/instances`（route → service → repository，items 序列化改用 Flask-RESTX marshal）
- 已落地 ledgers：`GET /databases/api/ledgers`、`GET /accounts/api/ledgers`（API items 序列化改用 Flask-RESTX marshal）
- 已落地 tags：`GET /tags/api/list`（route → service → repository，items 序列化改用 Flask-RESTX marshal）
- 已落地 history logs：`GET /history/logs/api/list`、`GET /history/logs/api/search`（route → service → repository，items 序列化改用 Flask-RESTX marshal）
- 已落地 Phase 3：Instance detail/accounts/permissions/change-history/db sizes、instances statistics、accounts statistics/ledger permissions、database capacity trend、history logs modules/statistics/detail、history sessions、tags options
- 待迁移（按页面分批）：CredentialsListPage / AuthListPage / AccountClassificationPage / SchedulerPage / AdminPartitionsPage / Capacity pages / Common filter options / DashboardOverviewPage(可选)

## Checklist

### Phase 0：建立契约与基准

- [x] 引入依赖：`flask-restx`（含锁文件/requirements）
- [x] 契约测试：`GET /instances/api/instances`
- [x] 契约测试：`GET /databases/api/ledgers`
- [x] 契约测试：`GET /accounts/api/ledgers`
- [x] 契约测试：`GET /tags/api/list`
- [x] 契约测试：`GET /history/logs/api/list`
- [x] 门禁脚本：`./scripts/code_review/error_message_drift_guard.sh`
- [x] 门禁脚本：`./scripts/code_review/pagination_param_guard.sh`

### Phase 1：引入目录与最小样板（instances 列表）

- [x] 新增 `app/repositories/` 与 `InstancesRepository.list_instances`
- [x] 新增 `app/services/instances/InstanceListService.list_instances`
- [x] 新增 `app/types/listing.py` / `app/types/instances.py`（filters/DTO/pagination）
- [x] 新增 RestX marshal fields：`app/routes/instances/restx_models.py`
- [x] 收敛 route：`app/routes/instances/manage.py` 的 `list_instances_data`

### Phase 2：核心列表页（ledgers/tags/history logs）

- [x] 新增 `app/repositories/ledgers/DatabaseLedgerRepository.list_ledger`
- [x] 新增 `app/services/ledgers/DatabaseLedgerService.get_ledger`（输出 DTO，route marshal）
- [x] 新增 RestX marshal fields：`app/routes/databases/restx_models.py`
- [x] 收敛 route：`app/routes/databases/ledgers.py` 的 `fetch_ledger`
- [x] 新增 `app/repositories/ledgers/AccountsLedgerRepository.list_accounts`
- [x] 新增 `app/services/ledgers/AccountsLedgerListService.list_accounts`（输出 DTO，route marshal）
- [x] 新增 RestX marshal fields：`app/routes/accounts/restx_models.py`
- [x] 收敛 route：`app/routes/accounts/ledgers.py` 的 `list_accounts_data`
- [x] 新增 `app/repositories/tags_repository.py` 与 `TagListService.list_tags`（输出 DTO，route marshal）
- [x] 新增 RestX marshal fields：`app/routes/tags/restx_models.py`
- [x] 收敛 route：`app/routes/tags/manage.py` 的 `list_tags`
- [x] 新增 `app/repositories/history_logs_repository.py` 与 `HistoryLogsListService.list_logs`（输出 DTO，route marshal）
- [x] 新增 RestX marshal fields：`app/routes/history/restx_models.py`
- [x] 收敛 route：`app/routes/history/logs.py` 的 `list_logs` / `search_logs`

### Phase 3：核心页面补齐（同页剩余 read API）

- [x] InstanceDetailPage：`GET /instances/api/<instance_id>/accounts`
- [x] InstanceDetailPage：`GET /instances/api/<instance_id>/accounts/<account_id>/permissions`
- [x] InstanceDetailPage：`GET /instances/api/<instance_id>/accounts/<account_id>/change-history`
- [x] InstanceDetailPage：`GET /instances/api/databases/<instance_id>/sizes`
- [x] InstanceStatisticsPage：`GET /instances/api/statistics`
- [x] AccountsListPage：`GET /accounts/api/ledgers/<account_id>/permissions`
- [x] AccountsStatisticsPage：`GET /accounts/api/statistics`
- [x] DatabaseLedgerPage：`GET /databases/api/ledgers/<database_id>/capacity-trend`
- [x] LogsPage：`GET /history/logs/api/modules`
- [x] LogsPage：`GET /history/logs/api/statistics`
- [x] LogsPage：`GET /history/logs/api/detail/<log_id>`
- [x] SyncSessionsPage：`GET /history/sessions/api/sessions`
- [x] SyncSessionsPage：`GET /history/sessions/api/sessions/<session_id>`
- [x] SyncSessionsPage：`GET /history/sessions/api/sessions/<session_id>/error-logs`
- [x] TagsBatchAssignPage：`GET /tags/bulk/api/instances`
- [x] TagsBatchAssignPage：`GET /tags/bulk/api/tags`
- [x] TagsIndexPage：`GET /tags/api/tags`
- [x] TagsIndexPage：`GET /tags/api/categories`

### Phase 4：管理台列表页（读链路收敛）

- [ ] CredentialsListPage：`GET /credentials/api/credentials`
- [ ] AuthListPage（用户管理）：`GET /users/api/users`

### Phase 5：后台管理页（复杂查询/多端点）

- [ ] AccountClassificationPage：`GET /accounts/classifications/api/classifications`
- [ ] AccountClassificationPage：`GET /accounts/classifications/api/rules`
- [ ] AccountClassificationPage：`GET /accounts/classifications/api/rules/stats`
- [ ] AccountClassificationPage：`GET /accounts/classifications/api/assignments`
- [ ] AccountClassificationPage：`GET /accounts/classifications/api/permissions/<db_type>`
- [ ] SchedulerPage：`GET /scheduler/api/jobs`
- [ ] SchedulerPage：`GET /scheduler/api/jobs/<job_id>`
- [ ] AdminPartitionsPage：`GET /partition/api/partitions`
- [ ] AdminPartitionsPage：`GET /partition/api/info`
- [ ] AdminPartitionsPage：`GET /partition/api/status`
- [ ] AdminPartitionsPage：`GET /partition/api/aggregations/core-metrics`

### Phase 6：容量统计页（查询复杂/大 payload）

- [ ] InstanceAggregationsPage：`GET /capacity/instances/api/instances`
- [ ] InstanceAggregationsPage：`GET /capacity/instances/api/instances/summary`
- [ ] CapacityDatabasesPage：`GET /capacity/databases/api/databases`
- [ ] CapacityDatabasesPage：`GET /capacity/databases/api/databases/summary`
- [ ] Capacity pages：`POST /capacity/api/aggregations/current`

### Phase 7：FilterOptions 收敛（query_filter_utils → repository）

- [ ] Common：`GET /common/api/instances-options`
- [ ] Common：`GET /common/api/databases-options`
- [ ] Common：`GET /common/api/dbtypes-options`
- [ ] 清理/降级：`app/utils/query_filter_utils.py`（仅保留纯函数/格式化）

### Phase 8：可选收尾（视需求）

- [ ] DashboardOverviewPage：`GET /dashboard/api/charts`

## 变更记录

- 2025-12-25：完成 instances 列表样板迁移（新增 repository/service/types/restx marshal + 契约测试）
- 2025-12-25：完成 databases/accounts ledgers 列表迁移（新增 repository/service/types/restx marshal + 契约测试）
- 2025-12-25：完成 tags 列表与 history logs 列表/搜索迁移（新增 repository/service/types/restx marshal + 契约测试）
- 2025-12-25：完成 Phase 3 读接口补齐（instances/accounts/databases/history/tags：route → service → repository，route marshal）
