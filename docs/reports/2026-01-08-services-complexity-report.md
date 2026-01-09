# Services 层复杂度清单 (静态扫描)
> 状态: Draft
> 负责人: team
> 创建: 2026-01-08
> 更新: 2026-01-08
> 范围: `app/services/**` (含 adapters/coordinator/orchestrator), 并以 `docs/Obsidian/API/*.md` 的 Service 引用作为对外服务清单
> 生成: 静态 AST + 正则统计 (本地生成时间: 2026-01-08 21:36:15)

## 摘要
- API contract 覆盖服务: 56 个 (未匹配: 0 个).
- services 目录 Python 文件(排除 `__init__.py`): 117 个.

## 评分口径(简述)
本报告基于静态指标做相对评分,用于挑选后续需要画时序图的候选服务.

使用的核心指标: `loc`, `total_cc`, `max_cc`, `service_imports`, `imports_total`, `db_ops`, `try_nodes`, `method_count/func_count`.
评分方式: 对每个指标在同一集合内计算 percentile(0..1),按权重加权求和后映射到 0..100.
等级: S(>=80), A(60-79.9), B(40-59.9), C(<40).

注意: 这是"静态复杂度"而非运行时复杂度,最终以链路/依赖/错误处理分支为准.

## A. API contract 覆盖的服务复杂度排名 (推荐作为时序图候选池)
| Rank | Score | Level | Service | Kind | LOC | Methods | Total CC | Max CC | DB Ops | Service Imports | API Docs | File | Top Method(CC) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 96.2 | S | `AccountClassificationsWriteService` | class | 383 | 19 | 69 | 15 | 19 | 2 | accounts-api-contract.md | `app/services/accounts/account_classifications_write_service.py` | _validate_and_normalize_rule(15) |
| 2 | 90.2 | S | `TableSizeCoordinator` | class | 187 | 10 | 36 | 9 | 10 | 9 | databases-api-contract.md | `app/services/database_sync/table_size_coordinator.py` | _upsert_and_cleanup(9) |
| 3 | 88.0 | S | `CurrentAggregationService` | class | 212 | 10 | 39 | 8 | 8 | 3 | capacity-api-contract.md | `app/services/capacity/current_aggregation_service.py` | aggregate_current(8) |
| 4 | 82.8 | S | `PartitionManagementService` | class | 609 | 14 | 58 | 7 | 22 | 0 | partition-api-contract.md | `app/services/partition_management_service.py` | create_partition(7) |
| 5 | 78.1 | A | `sync_session_service` | instance | 421 | 14 | 41 | 5 | 37 | 0 | sessions-api-contract.md | `app/services/sync_session_service.py` | _clean_sync_details(5) |
| 6 | 75.9 | A | `PartitionReadService` | class | 383 | 16 | 69 | 8 | 0 | 0 | partition-api-contract.md | `app/services/partition/partition_read_service.py` | list_partitions(8) |
| 7 | 75.4 | A | `TagWriteService` | class | 155 | 8 | 28 | 9 | 6 | 0 | tags-api-contract.md | `app/services/tags/tag_write_service.py` | update(9) |
| 8 | 74.9 | A | `SchedulerJobWriteService` | class | 168 | 13 | 44 | 8 | 0 | 0 | scheduler-api-contract.md | `app/services/scheduler/scheduler_job_write_service.py` | upsert(8) |
| 9 | 72.3 | A | `InstanceWriteService` | class | 145 | 7 | 26 | 12 | 6 | 0 | instances-api-contract.md | `app/services/instances/instance_write_service.py` | update(12) |
| 11 | 71.5 | A | `CacheActionsService` | class | 132 | 7 | 26 | 6 | 4 | 2 | cache-api-contract.md | `app/services/cache/cache_actions_service.py` | clear_classification_cache(6) |
| 12 | 68.8 | A | `ConnectionTestService` | class | 169 | 4 | 17 | 9 | 0 | 2 | instances-api-contract.md | `app/services/connection_adapters/connection_test_service.py` | test_connection(9) |
| 13 | 68.7 | A | `InstanceBatchCreationService` | class | 142 | 6 | 25 | 7 | 5 | 0 | instances-api-contract.md | `app/services/instances/batch_service.py` | _create_valid_instances(7) |
| 14 | 68.0 | A | `UserWriteService` | class | 113 | 11 | 32 | 6 | 2 | 0 | users-api-contract.md | `app/services/users/user_write_service.py` | update(6) |
| 15 | 67.8 | A | `CredentialWriteService` | class | 127 | 10 | 26 | 7 | 4 | 0 | credentials-api-contract.md | `app/services/credentials/credential_write_service.py` | update(7) |
| 16 | 66.9 | A | `DatabaseLedgerService` | class | 170 | 7 | 25 | 6 | 2 | 0 | databases-api-contract.md | `app/services/ledgers/database_ledger_service.py` | get_ledger(6) |
| 17 | 64.2 | A | `InstanceBatchDeletionService` | class | 146 | 2 | 12 | 10 | 26 | 0 | instances-api-contract.md | `app/services/instances/batch_service.py` | delete_instances(10) |
| 18 | 64.0 | A | `SchedulerJobsReadService` | class | 93 | 5 | 29 | 14 | 0 | 0 | scheduler-api-contract.md | `app/services/scheduler/scheduler_jobs_read_service.py` | _collect_trigger_args(14) |
| 19 | 63.2 | A | `AccountClassificationsReadService` | class | 146 | 8 | 31 | 6 | 0 | 0 | accounts-api-contract.md | `app/services/accounts/account_classifications_read_service.py` | list_rules(6) |
| 20 | 62.5 | A | `AutoClassifyService` | class | 144 | 6 | 21 | 6 | 0 | 1 | accounts-api-contract.md | `app/services/account_classification/auto_classify_service.py` | auto_classify(6) |
| 21 | 61.2 | A | `HistorySessionsReadService` | class | 91 | 6 | 33 | 13 | 0 | 0 | sessions-api-contract.md | `app/services/history_sessions/history_sessions_read_service.py` | _to_session_item(13) |
| 22 | 61.1 | A | `DatabaseAggregationsReadService` | class | 109 | 3 | 28 | 25 | 0 | 0 | capacity-api-contract.md | `app/services/capacity/database_aggregations_read_service.py` | list_aggregations(25) |
| 23 | 58.4 | B | `InstanceCapacitySyncActionsService` | class | 92 | 2 | 9 | 7 | 2 | 2 | instances-api-contract.md | `app/services/capacity/instance_capacity_sync_actions_service.py` | sync_instance_capacity(7) |
| 24 | 58.1 | B | `DatabaseLedgerExportService` | class | 64 | 3 | 14 | 11 | 1 | 1 | databases-api-contract.md | `app/services/files/database_ledger_export_service.py` | _render_csv(11) |
| 25 | 55.6 | B | `InstanceAggregationsReadService` | class | 91 | 3 | 24 | 20 | 0 | 0 | capacity-api-contract.md | `app/services/capacity/instance_aggregations_read_service.py` | list_aggregations(20) |
| 26 | 55.6 | B | `AccountExportService` | class | 51 | 3 | 18 | 15 | 2 | 0 | accounts-api-contract.md | `app/services/files/account_export_service.py` | _render_accounts_csv(15) |
| 27 | 55.0 | B | `AccountsSyncActionsService` | class | 133 | 6 | 16 | 5 | 4 | 0 | instances-api-contract.md | `app/services/accounts_sync/accounts_sync_actions_service.py` | _normalize_sync_result(5) |
| 28 | 52.2 | B | `health_checks_service` | module | 112 | 6 | 12 | 3 | 0 | 1 | health-api-contract.md | `app/services/health/health_checks_service.py` | check_cache_health(3) |
| 29 | 51.6 | B | `InstancesExportService` | class | 61 | 2 | 15 | 13 | 1 | 0 | instances-api-contract.md | `app/services/files/instances_export_service.py` | export_instances_csv(13) |
| 30 | 51.6 | B | `SchedulerActionsService` | class | 89 | 3 | 14 | 8 | 0 | 0 | scheduler-api-contract.md | `app/services/scheduler/scheduler_actions_service.py` | run_job_in_background(8) |
| 31 | 50.6 | B | `TagsBulkActionsService` | class | 95 | 6 | 17 | 4 | 4 | 0 | tags-api-contract.md | `app/services/tags/tags_bulk_actions_service.py` | assign(4) |
| 32 | 50.1 | B | `FilterOptionsService` | class | 84 | 9 | 21 | 7 | 0 | 0 | databases-api-contract.md,instances-api-contract.md | `app/services/common/filter_options_service.py` | get_common_databases_options(7) |
| 33 | 49.7 | B | `TagOptionsService` | class | 54 | 7 | 24 | 11 | 0 | 0 | tags-api-contract.md | `app/services/tags/tag_options_service.py` | _to_tag(11) |
| 34 | 42.3 | B | `InstanceConnectionStatusService` | class | 45 | 3 | 13 | 9 | 0 | 0 | instances-api-contract.md | `app/services/connections/instance_connection_status_service.py` | _build_connection_status_payload(9) |
| 35 | 37.1 | C | `LoginService` | class | 61 | 3 | 7 | 3 | 2 | 0 | auth-api-contract.md | `app/services/auth/login_service.py` | authenticate(3) |
| 36 | 35.4 | C | `HistoryLogsExtrasService` | class | 47 | 4 | 10 | 5 | 0 | 0 | logs-api-contract.md | `app/services/history_logs/history_logs_extras_service.py` | get_log_detail(5) |
| 37 | 35.4 | C | `ChangePasswordService` | class | 28 | 1 | 6 | 6 | 3 | 0 | auth-api-contract.md | `app/services/auth/change_password_service.py` | change_password(6) |
| 38 | 34.9 | C | `AccountsLedgerPermissionsService` | class | 31 | 2 | 7 | 5 | 0 | 1 | accounts-api-contract.md | `app/services/ledgers/accounts_ledger_permissions_service.py` | get_permissions(5) |
| 39 | 34.4 | C | `InstanceListService` | class | 37 | 2 | 9 | 7 | 0 | 0 | instances-api-contract.md | `app/services/instances/instance_list_service.py` | list_instances(7) |
| 40 | 33.8 | C | `InstanceStatisticsReadService` | class | 60 | 3 | 8 | 5 | 0 | 0 | instances-api-contract.md | `app/services/instances/instance_statistics_read_service.py` | build_statistics(5) |
| 41 | 32.8 | C | `AccountClassificationExpressionValidationService` | class | 29 | 1 | 6 | 6 | 0 | 1 | accounts-api-contract.md | `app/services/accounts/account_classification_expression_validation_service.py` | parse_and_validate(6) |
| 42 | 32.0 | C | `HistoryLogsListService` | class | 33 | 2 | 8 | 6 | 0 | 0 | logs-api-contract.md | `app/services/history_logs/history_logs_list_service.py` | list_logs(6) |
| 43 | 29.6 | C | `CredentialsListService` | class | 39 | 2 | 7 | 5 | 0 | 0 | credentials-api-contract.md | `app/services/credentials/credentials_list_service.py` | list_credentials(5) |
| 44 | 29.0 | C | `AccountsStatisticsReadService` | class | 52 | 6 | 7 | 2 | 0 | 0 | accounts-api-contract.md | `app/services/accounts/accounts_statistics_read_service.py` | __init__(2) |
| 45 | 28.9 | C | `AccountsLedgerListService` | class | 41 | 2 | 7 | 5 | 0 | 0 | accounts-api-contract.md | `app/services/ledgers/accounts_ledger_list_service.py` | list_accounts(5) |
| 46 | 27.1 | C | `AuthMeReadService` | class | 31 | 1 | 5 | 5 | 1 | 0 | auth-api-contract.md | `app/services/auth/auth_me_read_service.py` | get_me(5) |
| 47 | 26.2 | C | `PartitionStatisticsService` | class | 49 | 2 | 3 | 2 | 0 | 1 | partition-api-contract.md | `app/services/statistics/partition_statistics_service.py` | get_partition_info(2) |
| 48 | 24.5 | C | `TagListService` | class | 37 | 2 | 6 | 4 | 0 | 0 | tags-api-contract.md | `app/services/tags/tag_list_service.py` | list_tags(4) |
| 49 | 22.7 | C | `AccountsLedgerChangeHistoryService` | class | 35 | 2 | 5 | 3 | 0 | 0 | accounts-api-contract.md | `app/services/ledgers/accounts_ledger_change_history_service.py` | get_change_history(3) |
| 50 | 22.5 | C | `UsersListService` | class | 29 | 2 | 6 | 4 | 0 | 0 | users-api-contract.md | `app/services/users/users_list_service.py` | list_users(4) |
| 51 | 20.4 | C | `InstancesImportTemplateService` | class | 13 | 1 | 1 | 1 | 0 | 1 | instances-api-contract.md | `app/services/files/instances_import_template_service.py` | build_template_csv(1) |
| 52 | 16.5 | C | `InstanceDatabaseSizesService` | class | 13 | 2 | 4 | 2 | 0 | 0 | databases-api-contract.md | `app/services/instances/instance_database_sizes_service.py` | __init__(2) |
| 53 | 14.3 | C | `InstanceDatabaseTableSizesService` | class | 8 | 2 | 3 | 2 | 0 | 0 | databases-api-contract.md | `app/services/instances/instance_database_table_sizes_service.py` | __init__(2) |
| 54 | 14.3 | C | `InstanceDetailReadService` | class | 8 | 2 | 3 | 2 | 0 | 0 | instances-api-contract.md | `app/services/instances/instance_detail_read_service.py` | __init__(2) |
| 55 | 13.9 | C | `UsersStatsService` | class | 8 | 2 | 3 | 2 | 0 | 0 | users-api-contract.md | `app/services/users/users_stats_service.py` | __init__(2) |
| 56 | 10.1 | C | `DashboardActivitiesService` | class | 5 | 1 | 1 | 1 | 0 | 0 | dashboard-api-contract.md | `app/services/dashboard/dashboard_activities_service.py` | list_activities(1) |

## B. services 全量文件复杂度排名 (附录)
说明: 本表仅展示 Top 38,并新增 `图建议` 列,用于确定 coordinator 内部复杂模块应该补哪类图(流程/泳道/状态/数据流/决策).

| Rank | Score | Level | LOC | Funcs | Classes | Total CC | Max CC | DB Ops | Service Imports | API Docs | File | 图建议 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 95.7 | Very High | 963 | 37 | 6 | 150 | 17 | 13 | 2 | - | `app/services/accounts_sync/permission_manager.py` | 泳道流程图 + 决策表(权限规则) |
| 2 | 93.7 | Very High | 1190 | 45 | 2 | 204 | 14 | 3 | 3 | - | `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 数据流图 + 流程图(SQL 分支/异常) |
| 3 | 93.3 | Very High | 428 | 19 | 4 | 69 | 15 | 19 | 2 | accounts-api-contract.md | `app/services/accounts/account_classifications_write_service.py` | 泳道流程图 + 决策表(规则校验/归一化) |
| 4 | 91.4 | Very High | 870 | 43 | 2 | 97 | 10 | 3 | 6 | - | `app/services/aggregation/aggregation_service.py` | 泳道流程图 + 数据流图(聚合流水线) |
| 5 | 86.7 | Very High | 483 | 9 | 2 | 38 | 9 | 11 | 3 | - | `app/services/aggregation/instance_aggregation_runner.py` | 数据流图 + 流程图(采集/落库/错误) |
| 6 | 86.6 | Very High | 523 | 13 | 2 | 46 | 7 | 15 | 3 | - | `app/services/aggregation/database_aggregation_runner.py` | 数据流图 + 流程图(采集/落库/错误) |
| 7 | 85.0 | Very High | 274 | 16 | 3 | 55 | 8 | 8 | 3 | capacity-api-contract.md | `app/services/capacity/current_aggregation_service.py` | 泳道流程图 + 状态机(Session/Record) |
| 8 | 85.0 | Very High | 235 | 10 | 3 | 36 | 9 | 10 | 9 | databases-api-contract.md | `app/services/database_sync/table_size_coordinator.py` | 泳道流程图 + 数据流图(采集->upsert->cleanup) |
| 9 | 84.1 | Very High | 422 | 7 | 1 | 39 | 11 | 1 | 4 | - | `app/services/accounts_sync/accounts_sync_service.py` | 泳道流程图 + 状态机(Session/Record) |
| 10 | 83.8 | Very High | 465 | 10 | 2 | 59 | 25 | 0 | 2 | - | `app/services/accounts_sync/adapters/mysql_adapter.py` | 数据流图 + 流程图(SQL 分支/异常) |
| 11 | 79.8 | High | 655 | 15 | 2 | 59 | 7 | 22 | 0 | partition-api-contract.md | `app/services/partition_management_service.py` | 流程图 + 决策表(日期/retention 规则) |
| 12 | 79.6 | High | 405 | 10 | 1 | 37 | 10 | 0 | 5 | - | `app/services/accounts_sync/coordinator.py` | 泳道流程图(编排/回调/并发) |
| 13 | 78.4 | High | 395 | 12 | 1 | 47 | 8 | 0 | 2 | - | `app/services/accounts_sync/adapters/postgresql_adapter.py` | 数据流图 + 流程图(SQL 分支/异常) |
| 14 | 78.1 | High | 380 | 14 | 1 | 42 | 4 | 1 | 3 | - | `app/services/account_classification/orchestrator.py` | 泳道流程图 + 决策表(匹配/优先级) |
| 15 | 78.0 | High | 331 | 9 | 2 | 38 | 10 | 31 | 0 | instances-api-contract.md | `app/services/instances/batch_service.py` | 泳道流程图 + 决策表(CSV 行校验) |
| 16 | 77.2 | High | 357 | 11 | 1 | 55 | 8 | 0 | 2 | - | `app/services/database_sync/adapters/mysql_adapter.py` | 数据流图 + 流程图(SQL 分支/异常) |
| 17 | 77.0 | High | 252 | 8 | 1 | 30 | 11 | 1 | 3 | - | `app/services/accounts_sync/adapters/oracle_adapter.py` | 数据流图 + 流程图(SQL 分支/异常) |
| 18 | 75.0 | High | 443 | 15 | 2 | 45 | 5 | 37 | 0 | sessions-api-contract.md | `app/services/sync_session_service.py` | 状态机图 + 流程图(取消/失败/完成) |
| 19 | 74.4 | High | 195 | 5 | 1 | 42 | 15 | 0 | 2 | - | `app/services/database_sync/table_size_adapters/oracle_adapter.py` | 数据流图 + 流程图(SQL 分支/异常) |
| 20 | 74.0 | High | 321 | 21 | 3 | 149 | 37 | 0 | 0 | - | `app/services/account_classification/dsl_v4.py` | 决策表/规则树(DSL 语义) |
| 21 | 73.3 | High | 268 | 16 | 1 | 34 | 6 | 0 | 6 | - | `app/services/database_sync/coordinator.py` | 泳道流程图(编排/分发/汇总) |
| 22 | 72.0 | High | 405 | 16 | 1 | 69 | 8 | 0 | 0 | partition-api-contract.md | `app/services/partition/partition_read_service.py` | 流程图(查询构造/筛选/分页) |
| 23 | 70.8 | High | 179 | 11 | 5 | 30 | 6 | 4 | 2 | cache-api-contract.md | `app/services/cache/cache_actions_service.py` | 流程图(清理路径 + scope) |
| 24 | 70.6 | High | 190 | 9 | 3 | 30 | 9 | 6 | 0 | tags-api-contract.md | `app/services/tags/tag_write_service.py` | 流程图(批量/冲突/207) |
| 25 | 70.4 | High | 208 | 14 | 2 | 46 | 8 | 0 | 0 | scheduler-api-contract.md | `app/services/scheduler/scheduler_job_write_service.py` | 流程图(校验->upsert) |
| 26 | 70.4 | High | 179 | 10 | 2 | 26 | 8 | 5 | 1 | - | `app/services/database_sync/inventory_manager.py` | 泳道流程图(采集 inventory->持久化) |
| 27 | 70.0 | High | 341 | 19 | 0 | 114 | 14 | 0 | 0 | - | `app/services/accounts_permissions/facts_builder.py` | 数据流图 + 决策表(事实模型) |
| 28 | 69.9 | High | 426 | 18 | 1 | 59 | 8 | 0 | 0 | - | `app/services/cache_service.py` | 流程图(读写/失效/异常) |
| 29 | 69.2 | High | 175 | 5 | 1 | 35 | 17 | 1 | 0 | - | `app/services/connection_adapters/adapters/oracle_adapter.py` | 数据流图 + 流程图(连接参数/异常) |
| 30 | 67.5 | High | 176 | 7 | 3 | 26 | 12 | 6 | 0 | instances-api-contract.md | `app/services/instances/instance_write_service.py` | 状态机图(Instance 生命周期) + 流程图 |
| 32 | 63.9 | High | 176 | 3 | 1 | 25 | 13 | 0 | 2 | - | `app/services/database_sync/adapters/oracle_adapter.py` | 数据流图 + 流程图(SQL 分支/异常) |
| 33 | 63.3 | High | 154 | 10 | 2 | 26 | 7 | 4 | 0 | credentials-api-contract.md | `app/services/credentials/credential_write_service.py` | 数据流图(明文->加密->存储) + 流程图 |
| 34 | 63.2 | High | 195 | 4 | 1 | 17 | 9 | 0 | 2 | instances-api-contract.md | `app/services/connection_adapters/connection_test_service.py` | 泳道流程图(payload->adapter->test->归一化错误) |
| 35 | 62.9 | High | 141 | 11 | 2 | 32 | 6 | 2 | 0 | users-api-contract.md | `app/services/users/user_write_service.py` | 流程图(校验->写入/更新) |
| 36 | 62.7 | High | 199 | 7 | 1 | 25 | 6 | 2 | 0 | databases-api-contract.md | `app/services/ledgers/database_ledger_service.py` | 数据流图(ledger 口径) + 流程图(query build) |
| 37 | 62.2 | High | 154 | 7 | 3 | 34 | 14 | 0 | 0 | - | `app/services/database_sync/database_filters.py` | 决策表(过滤参数->查询片段) |
| 38 | 61.1 | High | 189 | 7 | 1 | 26 | 6 | 1 | 0 | - | `app/services/connection_adapters/adapters/sqlserver_adapter.py` | 数据流图 + 流程图(连接参数/异常) |
