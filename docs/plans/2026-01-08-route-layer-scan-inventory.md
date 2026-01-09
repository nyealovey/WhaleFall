# Route Layer Scan Inventory (2026-01-08)

> [!note]
> 目的：提供“路由层清单 + 热点定位”，用于落实“路由层只负责鉴权/封套，业务逻辑由 service 层承载”的约束。
>
> 扫描范围：
> - API 路由层：`app/api/v1/namespaces/**`
> - 页面路由层：`app/routes/**`

## 1) 总览

### API v1（Flask-RESTX）

- 挂载点：`/api/v1/**`（见 `app/api/v1/__init__.py`）
- 资源类（`@ns.route`）数量：105

| Module | File | Base | Resources | `.query` |
| --- | --- | --- | ---: | ---: |
| `accounts` | `app/api/v1/namespaces/accounts.py` | `/api/v1/accounts` | 9 | 0 |
| `accounts_classifications` | `app/api/v1/namespaces/accounts_classifications.py` | `/api/v1/accounts/classifications` | 11 | 9 |
| `auth` | `app/api/v1/namespaces/auth.py` | `/api/v1/auth` | 6 | 2 |
| `cache` | `app/api/v1/namespaces/cache.py` | `/api/v1/cache` | 6 | 3 |
| `capacity` | `app/api/v1/namespaces/capacity.py` | `/api/v1/capacity` | 5 | 0 |
| `credentials` | `app/api/v1/namespaces/credentials.py` | `/api/v1/credentials` | 2 | 0 |
| `dashboard` | `app/api/v1/namespaces/dashboard.py` | `/api/v1/dashboard` | 4 | 0 |
| `databases` | `app/api/v1/namespaces/databases.py` | `/api/v1/databases` | 6 | 4 |
| `health` | `app/api/v1/namespaces/health.py` | `/api/v1/health` | 5 | 0 |
| `instances` | `app/api/v1/namespaces/instances.py` | `/api/v1/instances` | 10 | 1 |
| `instances_accounts_sync` | `app/api/v1/namespaces/instances_accounts_sync.py` | `/api/v1/instances` | 2 | 0 |
| `instances_connections` | `app/api/v1/namespaces/instances_connections.py` | `/api/v1/instances` | 4 | 3 |
| `logs` | `app/api/v1/namespaces/logs.py` | `/api/v1/logs` | 5 | 0 |
| `partition` | `app/api/v1/namespaces/partition.py` | `/api/v1/partitions` | 6 | 0 |
| `scheduler` | `app/api/v1/namespaces/scheduler.py` | `/api/v1/scheduler` | 6 | 0 |
| `sessions` | `app/api/v1/namespaces/sessions.py` | `/api/v1/sync-sessions` | 4 | 0 |
| `tags` | `app/api/v1/namespaces/tags.py` | `/api/v1/tags` | 11 | 7 |
| `users` | `app/api/v1/namespaces/users.py` | `/api/v1/users` | 3 | 0 |

> [!info]
> `instances_accounts_sync.py / instances_connections.py` 通过 `from app.api.v1.namespaces.instances import ns` 绑定到同一个 `/api/v1/instances` namespace（side effects 注册）。

### 页面路由（Flask Blueprints）

- 蓝图注册入口：`app/__init__.py::configure_blueprints()`
- 路由条目数量（decorator + `add_url_rule`）：37

| File | `.query` | Notes |
| --- | ---: | --- |
| `app/routes/accounts/classifications.py` | 0 |  |
| `app/routes/accounts/ledgers.py` | 0 |  |
| `app/routes/accounts/statistics.py` | 2 | WARN: direct ORM query |
| `app/routes/auth.py` | 1 | WARN: direct ORM query |
| `app/routes/capacity/databases.py` | 0 |  |
| `app/routes/capacity/instances.py` | 0 |  |
| `app/routes/credentials.py` | 1 | WARN: direct ORM query |
| `app/routes/dashboard.py` | 0 |  |
| `app/routes/databases/ledgers.py` | 0 |  |
| `app/routes/history/logs.py` | 0 |  |
| `app/routes/history/sessions.py` | 0 |  |
| `app/routes/instances/detail.py` | 0 |  |
| `app/routes/instances/manage.py` | 1 | WARN: direct ORM query |
| `app/routes/instances/statistics.py` | 0 |  |
| `app/routes/main.py` | 0 |  |
| `app/routes/partition.py` | 0 |  |
| `app/routes/scheduler.py` | 0 |  |
| `app/routes/tags/bulk.py` | 0 |  |
| `app/routes/tags/manage.py` | 0 |  |
| `app/routes/users.py` | 0 |  |

## 2) 热点（与“薄路由”约束冲突的主要点）

> [!warning]
> 这里的“热点”指：路由层内出现“动作编排/批量循环/直接 ORM 查询/导出序列化/线程后台执行”等业务逻辑。

### API（高优先级）

- `app/api/v1/namespaces/instances.py:744`：`POST /api/v1/instances/{instance_id}/actions/sync-capacity`（协调器编排 + 失败仍需 commit 的特殊语义）
- `app/api/v1/namespaces/tags.py:572/655/728/784`：`/api/v1/tags/bulk/*`（批量循环 + ORM 读写）
- `app/api/v1/namespaces/cache.py:103/164/215/276/335`：cache actions + stats（实例校验/兼容/吞错范围）
- `app/api/v1/namespaces/scheduler.py:230/302`：scheduler actions（后台线程 + reload/delete）

### API（中优先级）

- `app/api/v1/namespaces/databases.py:305`：`GET /api/v1/databases/ledgers/exports`（CSV 序列化）
- `app/api/v1/namespaces/auth.py:136`：`POST /api/v1/auth/login`（User.query + 密码校验 + token 生成）
- `app/api/v1/namespaces/accounts_classifications.py:594`：`POST /api/v1/accounts/classifications/rules/actions/validate-expression`（JSON/DSL v4 parse + 校验）

### 页面路由（低优先级，可 Phase 2）

- `app/routes/auth.py`：页面登录（User.query + check_password）
- `app/routes/instances/manage.py`：实例页面（直接 ORM query Credential）
- `app/routes/credentials.py`：详情页（直接 ORM query）
- `app/routes/accounts/statistics.py`：统计页（direct ORM query + fallback/兜底）

> [!tip]
> 对应的重构计划见：`docs/plans/2026-01-08-route-layer-thin-service-refactor.md`（含每个热点 endpoint 的 service 拆分建议与测试/文档同步要求）。

## Appendix A: API v1 Endpoints（按文件）

## `app/api/v1/namespaces/accounts.py`
- base: `/api/v1/accounts`
- app/api/v1/namespaces/accounts.py:256 `GET` `/api/v1/accounts/ledgers` (`AccountsLedgersResource`)
- app/api/v1/namespaces/accounts.py:307 `GET` `/api/v1/accounts/ledgers/<int:account_id>/permissions` (`AccountsLedgersPermissionsResource`)
- app/api/v1/namespaces/accounts.py:337 `GET` `/api/v1/accounts/ledgers/<int:account_id>/change-history` (`AccountsLedgersChangeHistoryResource`)
- app/api/v1/namespaces/accounts.py:368 `GET` `/api/v1/accounts/ledgers/exports` (`AccountsLedgersExportResource`)
- app/api/v1/namespaces/accounts.py:405 `GET` `/api/v1/accounts/statistics` (`AccountsStatisticsResource`)
- app/api/v1/namespaces/accounts.py:431 `GET` `/api/v1/accounts/statistics/summary` (`AccountsStatisticsSummaryResource`)
- app/api/v1/namespaces/accounts.py:459 `GET` `/api/v1/accounts/statistics/db-types` (`AccountsStatisticsByDbTypeResource`)
- app/api/v1/namespaces/accounts.py:484 `GET` `/api/v1/accounts/statistics/classifications` (`AccountsStatisticsByClassificationResource`)
- app/api/v1/namespaces/accounts.py:509 `GET` `/api/v1/accounts/statistics/rules` (`AccountsStatisticsRulesResource`)

## `app/api/v1/namespaces/accounts_classifications.py`
- base: `/api/v1/accounts/classifications`
- app/api/v1/namespaces/accounts_classifications.py:297 `GET` `/api/v1/accounts/classifications/colors` (`AccountClassificationColorsResource`)
- app/api/v1/namespaces/accounts_classifications.py:326 `GET,POST` `/api/v1/accounts/classifications` (`AccountClassificationsResource`)
- app/api/v1/namespaces/accounts_classifications.py:385 `GET,PUT,DELETE` `/api/v1/accounts/classifications/<int:classification_id>` (`AccountClassificationDetailResource`)
- app/api/v1/namespaces/accounts_classifications.py:484 `GET,POST` `/api/v1/accounts/classifications/rules` (`AccountClassificationRulesResource`)
- app/api/v1/namespaces/accounts_classifications.py:562 `GET` `/api/v1/accounts/classifications/rules/filter` (`AccountClassificationRulesFilterResource`)
- app/api/v1/namespaces/accounts_classifications.py:594 `POST` `/api/v1/accounts/classifications/rules/actions/validate-expression` (`AccountClassificationRuleExpressionValidateResource`)
- app/api/v1/namespaces/accounts_classifications.py:644 `GET,PUT,DELETE` `/api/v1/accounts/classifications/rules/<int:rule_id>` (`AccountClassificationRuleDetailResource`)
- app/api/v1/namespaces/accounts_classifications.py:726 `GET` `/api/v1/accounts/classifications/assignments` (`AccountClassificationAssignmentsResource`)
- app/api/v1/namespaces/accounts_classifications.py:755 `DELETE` `/api/v1/accounts/classifications/assignments/<int:assignment_id>` (`AccountClassificationAssignmentResource`)
- app/api/v1/namespaces/accounts_classifications.py:786 `GET` `/api/v1/accounts/classifications/permissions/<string:db_type>` (`AccountClassificationPermissionsResource`)
- app/api/v1/namespaces/accounts_classifications.py:816 `POST` `/api/v1/accounts/classifications/actions/auto-classify` (`AccountClassificationAutoClassifyActionResource`)

## `app/api/v1/namespaces/auth.py`
- base: `/api/v1/auth`
- app/api/v1/namespaces/auth.py:122 `GET` `/api/v1/auth/csrf-token` (`CsrfTokenResource`)
- app/api/v1/namespaces/auth.py:136 `POST` `/api/v1/auth/login` (`LoginResource`)
- app/api/v1/namespaces/auth.py:189 `POST` `/api/v1/auth/logout` (`LogoutResource`)
- app/api/v1/namespaces/auth.py:205 `POST` `/api/v1/auth/change-password` (`ChangePasswordResource`)
- app/api/v1/namespaces/auth.py:236 `POST` `/api/v1/auth/refresh` (`RefreshResource`)
- app/api/v1/namespaces/auth.py:270 `GET` `/api/v1/auth/me` (`MeResource`)

## `app/api/v1/namespaces/cache.py`
- base: `/api/v1/cache`
- app/api/v1/namespaces/cache.py:68 `GET` `/api/v1/cache/stats` (`CacheStatsResource`)
- app/api/v1/namespaces/cache.py:103 `POST` `/api/v1/cache/actions/clear-user` (`CacheClearUserResource`)
- app/api/v1/namespaces/cache.py:164 `POST` `/api/v1/cache/actions/clear-instance` (`CacheClearInstanceResource`)
- app/api/v1/namespaces/cache.py:215 `POST` `/api/v1/cache/actions/clear-all` (`CacheClearAllResource`)
- app/api/v1/namespaces/cache.py:276 `POST` `/api/v1/cache/actions/clear-classification` (`CacheClearClassificationActionResource`)
- app/api/v1/namespaces/cache.py:335 `GET` `/api/v1/cache/classification/stats` (`CacheClassificationStatsResource`)

## `app/api/v1/namespaces/capacity.py`
- base: `/api/v1/capacity`
- app/api/v1/namespaces/capacity.py:196 `POST` `/api/v1/capacity/aggregations/current` (`CapacityCurrentAggregationResource`)
- app/api/v1/namespaces/capacity.py:240 `GET` `/api/v1/capacity/databases` (`CapacityDatabasesAggregationsResource`)
- app/api/v1/namespaces/capacity.py:303 `GET` `/api/v1/capacity/databases/summary` (`CapacityDatabasesSummaryResource`)
- app/api/v1/namespaces/capacity.py:350 `GET` `/api/v1/capacity/instances` (`CapacityInstancesAggregationsResource`)
- app/api/v1/namespaces/capacity.py:408 `GET` `/api/v1/capacity/instances/summary` (`CapacityInstancesSummaryResource`)

## `app/api/v1/namespaces/credentials.py`
- base: `/api/v1/credentials`
- app/api/v1/namespaces/credentials.py:154 `GET,POST` `/api/v1/credentials` (`CredentialsResource`)
- app/api/v1/namespaces/credentials.py:231 `GET,PUT,DELETE` `/api/v1/credentials/<int:credential_id>` (`CredentialDetailResource`)

## `app/api/v1/namespaces/dashboard.py`
- base: `/api/v1/dashboard`
- app/api/v1/namespaces/dashboard.py:219 `GET` `/api/v1/dashboard/overview` (`DashboardOverviewResource`)
- app/api/v1/namespaces/dashboard.py:246 `GET` `/api/v1/dashboard/charts` (`DashboardChartsResource`)
- app/api/v1/namespaces/dashboard.py:277 `GET` `/api/v1/dashboard/activities` (`DashboardActivitiesResource`)
- app/api/v1/namespaces/dashboard.py:300 `GET` `/api/v1/dashboard/status` (`DashboardStatusResource`)

## `app/api/v1/namespaces/databases.py`
- base: `/api/v1/databases`
- app/api/v1/namespaces/databases.py:178 `GET` `/api/v1/databases/options` (`DatabasesOptionsResource`)
- app/api/v1/namespaces/databases.py:245 `GET` `/api/v1/databases/ledgers` (`DatabaseLedgersResource`)
- app/api/v1/namespaces/databases.py:305 `GET` `/api/v1/databases/ledgers/exports` (`DatabaseLedgersExportResource`)
- app/api/v1/namespaces/databases.py:388 `GET` `/api/v1/databases/sizes` (`DatabasesSizesResource`)
- app/api/v1/namespaces/databases.py:496 `GET` `/api/v1/databases/<int:database_id>/tables/sizes` (`DatabaseTableSizesSnapshotResource`)
- app/api/v1/namespaces/databases.py:584 `POST` `/api/v1/databases/<int:database_id>/tables/sizes/actions/refresh` (`DatabaseTableSizesRefreshResource`)

## `app/api/v1/namespaces/health.py`
- base: `/api/v1/health`
- app/api/v1/namespaces/health.py:108 `GET` `/api/v1/health/ping` (`HealthPingResource`)
- app/api/v1/namespaces/health.py:119 `GET` `/api/v1/health/basic` (`HealthBasicResource`)
- app/api/v1/namespaces/health.py:138 `GET` `/api/v1/health` (`HealthCheckResource`)
- app/api/v1/namespaces/health.py:214 `GET` `/api/v1/health/cache` (`HealthCacheResource`)
- app/api/v1/namespaces/health.py:241 `GET` `/api/v1/health/detailed` (`HealthDetailedResource`)

## `app/api/v1/namespaces/instances.py`
- base: `/api/v1/instances`
- app/api/v1/namespaces/instances.py:470 `GET` `/api/v1/instances/options` (`InstancesOptionsResource`)
- app/api/v1/namespaces/instances.py:500 `GET,POST` `/api/v1/instances` (`InstancesResource`)
- app/api/v1/namespaces/instances.py:584 `GET` `/api/v1/instances/exports` (`InstancesExportResource`)
- app/api/v1/namespaces/instances.py:617 `GET` `/api/v1/instances/imports/template` (`InstancesImportTemplateResource`)
- app/api/v1/namespaces/instances.py:655 `GET,PUT,DELETE` `/api/v1/instances/<int:instance_id>` (`InstanceDetailResource`)
- app/api/v1/namespaces/instances.py:744 `POST` `/api/v1/instances/<int:instance_id>/actions/sync-capacity` (`InstanceSyncCapacityActionResource`)
- app/api/v1/namespaces/instances.py:856 `POST` `/api/v1/instances/<int:instance_id>/actions/restore` (`InstanceRestoreActionResource`)
- app/api/v1/namespaces/instances.py:891 `POST` `/api/v1/instances/actions/batch-create` (`InstancesBatchCreateResource`)
- app/api/v1/namespaces/instances.py:938 `POST` `/api/v1/instances/actions/batch-delete` (`InstancesBatchDeleteResource`)
- app/api/v1/namespaces/instances.py:987 `GET` `/api/v1/instances/statistics` (`InstancesStatisticsResource`)

## `app/api/v1/namespaces/instances_accounts_sync.py`
- base: `/api/v1/instances`
- app/api/v1/namespaces/instances_accounts_sync.py:60 `POST` `/api/v1/instances/actions/sync-accounts` (`InstancesSyncAccountsActionResource`)
- app/api/v1/namespaces/instances_accounts_sync.py:104 `POST` `/api/v1/instances/<int:instance_id>/actions/sync-accounts` (`InstancesSyncInstanceAccountsActionResource`)

## `app/api/v1/namespaces/instances_connections.py`
- base: `/api/v1/instances`
- app/api/v1/namespaces/instances_connections.py:315 `POST` `/api/v1/instances/actions/test-connection` (`InstancesConnectionsTestResource`)
- app/api/v1/namespaces/instances_connections.py:363 `POST` `/api/v1/instances/actions/validate-connection-params` (`InstancesConnectionsValidateParamsResource`)
- app/api/v1/namespaces/instances_connections.py:396 `POST` `/api/v1/instances/actions/batch-test-connections` (`InstancesConnectionsBatchTestResource`)
- app/api/v1/namespaces/instances_connections.py:450 `GET` `/api/v1/instances/<int:instance_id>/connection-status` (`InstancesConnectionsStatusResource`)

## `app/api/v1/namespaces/logs.py`
- base: `/api/v1/logs`
- app/api/v1/namespaces/logs.py:219 `GET` `/api/v1/logs` (`HistoryLogsResource`)
- app/api/v1/namespaces/logs.py:258 `GET` `/api/v1/logs/statistics` (`HistoryLogStatisticsResource`)
- app/api/v1/namespaces/logs.py:301 `GET` `/api/v1/logs/modules` (`HistoryLogModulesResource`)
- app/api/v1/namespaces/logs.py:328 `GET` `/api/v1/logs/<int:log_id>` (`HistoryLogDetailResource`)

## `app/api/v1/namespaces/partition.py`
- base: `/api/v1/partitions`
- app/api/v1/namespaces/partition.py:118 `GET` `/api/v1/partitions/info` (`PartitionInfoResource`)
- app/api/v1/namespaces/partition.py:149 `GET` `/api/v1/partitions/status` (`PartitionStatusResource`)
- app/api/v1/namespaces/partition.py:195 `GET,POST` `/api/v1/partitions` (`PartitionsResource`)
- app/api/v1/namespaces/partition.py:325 `POST` `/api/v1/partitions/actions/cleanup` (`PartitionCleanupResource`)
- app/api/v1/namespaces/partition.py:370 `GET` `/api/v1/partitions/statistics` (`PartitionStatisticsResource`)
- app/api/v1/namespaces/partition.py:397 `GET` `/api/v1/partitions/core-metrics` (`PartitionCoreMetricsResource`)

## `app/api/v1/namespaces/scheduler.py`
- base: `/api/v1/scheduler`
- app/api/v1/namespaces/scheduler.py:79 `GET` `/api/v1/scheduler/jobs` (`SchedulerJobsResource`)
- app/api/v1/namespaces/scheduler.py:109 `GET,PUT` `/api/v1/scheduler/jobs/<string:job_id>` (`SchedulerJobDetailResource`)
- app/api/v1/namespaces/scheduler.py:168 `POST` `/api/v1/scheduler/jobs/<string:job_id>/actions/pause` (`SchedulerJobPauseResource`)
- app/api/v1/namespaces/scheduler.py:199 `POST` `/api/v1/scheduler/jobs/<string:job_id>/actions/resume` (`SchedulerJobResumeResource`)
- app/api/v1/namespaces/scheduler.py:230 `POST` `/api/v1/scheduler/jobs/<string:job_id>/actions/run` (`SchedulerJobRunResource`)
- app/api/v1/namespaces/scheduler.py:302 `POST` `/api/v1/scheduler/jobs/actions/reload` (`SchedulerJobsReloadResource`)

## `app/api/v1/namespaces/sessions.py`
- base: `/api/v1/sync-sessions`
- app/api/v1/namespaces/sessions.py:52 `GET` `/api/v1/sync-sessions` (`HistorySessionsListResource`)
- app/api/v1/namespaces/sessions.py:111 `GET` `/api/v1/sync-sessions/<string:session_id>` (`HistorySessionDetailResource`)
- app/api/v1/namespaces/sessions.py:140 `GET` `/api/v1/sync-sessions/<string:session_id>/error-logs` (`HistorySessionErrorLogsResource`)
- app/api/v1/namespaces/sessions.py:169 `POST` `/api/v1/sync-sessions/<string:session_id>/actions/cancel` (`HistorySessionCancelResource`)

## `app/api/v1/namespaces/tags.py`
- base: `/api/v1/tags`
- app/api/v1/namespaces/tags.py:248 `GET,POST` `/api/v1/tags` (`TagsResource`)
- app/api/v1/namespaces/tags.py:319 `GET` `/api/v1/tags/options` (`TagOptionsResource`)
- app/api/v1/namespaces/tags.py:352 `GET` `/api/v1/tags/categories` (`TagCategoriesResource`)
- app/api/v1/namespaces/tags.py:378 `GET,PUT,DELETE` `/api/v1/tags/<int:tag_id>` (`TagDetailResource`)
- app/api/v1/namespaces/tags.py:472 `POST` `/api/v1/tags/batch-delete` (`TagBatchDeleteResource`)
- app/api/v1/namespaces/tags.py:512 `GET` `/api/v1/tags/bulk/instances` (`TagsBulkInstancesResource`)
- app/api/v1/namespaces/tags.py:539 `GET` `/api/v1/tags/bulk/tags` (`TagsBulkTagsResource`)
- app/api/v1/namespaces/tags.py:572 `POST` `/api/v1/tags/bulk/actions/assign` (`TagsBulkAssignResource`)
- app/api/v1/namespaces/tags.py:655 `POST` `/api/v1/tags/bulk/actions/remove` (`TagsBulkRemoveResource`)
- app/api/v1/namespaces/tags.py:728 `POST` `/api/v1/tags/bulk/instance-tags` (`TagsBulkInstanceTagsResource`)
- app/api/v1/namespaces/tags.py:784 `POST` `/api/v1/tags/bulk/actions/remove-all` (`TagsBulkRemoveAllResource`)

## `app/api/v1/namespaces/users.py`
- base: `/api/v1/users`
- app/api/v1/namespaces/users.py:151 `GET,POST` `/api/v1/users` (`UsersResource`)
- app/api/v1/namespaces/users.py:234 `GET,PUT,DELETE` `/api/v1/users/<int:user_id>` (`UserDetailResource`)
- app/api/v1/namespaces/users.py:323 `GET` `/api/v1/users/stats` (`UsersStatsResource`)

## Appendix B: Page Routes（按文件，含 decorator / add_url_rule）

## `app/routes/accounts/classifications.py`
- app/routes/accounts/classifications.py:27 `GET` `/` (`index`) [decorator]
- app/routes/accounts/classifications.py:39 `GET,POST` `/classifications/create` (`<add_url_rule>`) [add_url_rule]
- app/routes/accounts/classifications.py:52 `GET,POST` `/classifications/<int:resource_id>/edit` (`<add_url_rule>`) [add_url_rule]
- app/routes/accounts/classifications.py:64 `GET,POST` `/rules/create` (`<add_url_rule>`) [add_url_rule]
- app/routes/accounts/classifications.py:77 `GET,POST` `/rules/<int:resource_id>/edit` (`<add_url_rule>`) [add_url_rule]

## `app/routes/accounts/ledgers.py`
- app/routes/accounts/ledgers.py:69 `GET` `/ledgers` (`list_accounts`) [decorator]
- app/routes/accounts/ledgers.py:69 `GET` `/ledgers/<db_type>` (`list_accounts`) [decorator]

## `app/routes/accounts/statistics.py`
- app/routes/accounts/statistics.py:66 `GET` `/statistics` (`statistics`) [decorator]

## `app/routes/auth.py`
- app/routes/auth.py:28 `GET,POST` `/change-password` (`change_password`) [add_url_rule]
- app/routes/auth.py:116 `GET,POST` `/login` (`<add_url_rule>`) [add_url_rule]
- app/routes/auth.py:147 `POST` `/logout` (`<add_url_rule>`) [add_url_rule]

## `app/routes/capacity/databases.py`
- app/routes/capacity/databases.py:21 `GET` `/databases` (`list_databases`) [decorator]

## `app/routes/capacity/instances.py`
- app/routes/capacity/instances.py:20 `GET` `/instances` (`list_instances`) [decorator]

## `app/routes/credentials.py`
- app/routes/credentials.py:120 `GET` `/` (`index`) [decorator]
- app/routes/credentials.py:180 `GET` `/<int:credential_id>` (`detail`) [decorator]

## `app/routes/dashboard.py`
- app/routes/dashboard.py:19 `GET` `/` (`index`) [decorator]

## `app/routes/databases/ledgers.py`
- app/routes/databases/ledgers.py:48 `GET` `/ledgers` (`list_databases`) [decorator]

## `app/routes/history/logs.py`
- app/routes/history/logs.py:21 `GET` `/` (`logs_dashboard`) [decorator]

## `app/routes/history/sessions.py`
- app/routes/history/sessions.py:18 `GET` `/` (`index`) [decorator]

## `app/routes/instances/detail.py`
- app/routes/instances/detail.py:22 `GET` `/<int:instance_id>` (`detail`) [decorator]

## `app/routes/instances/manage.py`
- app/routes/instances/manage.py:29 `GET` `/` (`index`) [decorator]
- app/routes/instances/manage.py:85 `GET,POST` `/create` (`create`) [add_url_rule]
- app/routes/instances/manage.py:98 `GET,POST` `/<int:instance_id>/edit` (`edit`) [add_url_rule]

## `app/routes/instances/statistics.py`
- app/routes/instances/statistics.py:19 `GET` `/statistics` (`statistics`) [decorator]

## `app/routes/main.py`
- app/routes/main.py:15 `GET` `/` (`index`) [decorator]
- app/routes/main.py:26 `GET` `/about` (`about`) [decorator]
- app/routes/main.py:37 `GET` `/favicon.ico` (`favicon`) [decorator]
- app/routes/main.py:50 `GET` `/apple-touch-icon.png` (`apple_touch_icon`) [decorator]
- app/routes/main.py:50 `GET` `/apple-touch-icon-precomposed.png` (`apple_touch_icon`) [decorator]
- app/routes/main.py:64 `GET` `/.well-known/appspecific/com.chrome.devtools.json` (`chrome_devtools`) [decorator]

## `app/routes/partition.py`
- app/routes/partition.py:17 `GET` `/` (`partitions_page`) [decorator]

## `app/routes/scheduler.py`
- app/routes/scheduler.py:17 `GET` `/` (`index`) [decorator]

## `app/routes/tags/bulk.py`
- app/routes/tags/bulk.py:19 `GET` `/assign` (`batch_assign`) [decorator]

## `app/routes/tags/manage.py`
- app/routes/tags/manage.py:24 `GET` `/` (`index`) [decorator]

## `app/routes/users.py`
- app/routes/users.py:25 `GET` `/` (`index`) [decorator]
- app/routes/users.py:62 `GET,POST` `/create` (`create`) [add_url_rule]
- app/routes/users.py:76 `GET,POST` `/<int:user_id>/edit` (`edit`) [add_url_rule]
