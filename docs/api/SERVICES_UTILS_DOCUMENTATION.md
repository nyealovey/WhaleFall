# TaifishingV4 服务与工具函数索引

> 生成时间：2025-11-06；列出 `app/services` 与 `app/utils` 目录下所有函数 / 方法的引用概览。`引用情况` 基于 `rg` 搜索，若标记为“仅所在文件内部使用”，表示当前仅在声明文件内被调用。`用途` 字段提供简要描述，后续可按需补充详细语义。

## `app/services/account_classification_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AccountClassificationService.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `AccountClassificationService.auto_classify_accounts_optimized` | 仅所在文件内部使用 | 负责 auto classify accounts optimized 相关逻辑 |
| `AccountClassificationService._get_rules_sorted_by_priority` | 仅所在文件内部使用 | 负责 get rules sorted by priority 相关逻辑 |
| `AccountClassificationService._get_accounts_to_classify` | 仅所在文件内部使用 | 负责 get accounts to classify 相关逻辑 |
| `AccountClassificationService._group_accounts_by_db_type` | 仅所在文件内部使用 | 负责 group accounts by db type 相关逻辑 |
| `AccountClassificationService._group_rules_by_db_type` | 仅所在文件内部使用 | 负责 group rules by db type 相关逻辑 |
| `AccountClassificationService._classify_accounts_by_db_type_optimized` | 仅所在文件内部使用 | 负责 classify accounts by db type optimized 相关逻辑 |
| `AccountClassificationService._classify_single_db_type` | 仅所在文件内部使用 | 负责 classify single db type 相关逻辑 |
| `AccountClassificationService._find_accounts_matching_rule_optimized` | 仅所在文件内部使用 | 负责 find accounts matching rule optimized 相关逻辑 |
| `AccountClassificationService._evaluate_rule` | 仅所在文件内部使用 | 负责 evaluate rule 相关逻辑 |
| `AccountClassificationService._evaluate_mysql_rule` | 仅所在文件内部使用 | 负责 evaluate mysql rule 相关逻辑 |
| `AccountClassificationService._evaluate_sqlserver_rule` | 仅所在文件内部使用 | 负责 evaluate sqlserver rule 相关逻辑 |
| `AccountClassificationService._evaluate_postgresql_rule` | 仅所在文件内部使用 | 负责 evaluate postgresql rule 相关逻辑 |
| `AccountClassificationService._evaluate_oracle_rule` | 仅所在文件内部使用 | 负责 evaluate oracle rule 相关逻辑 |
| `AccountClassificationService._add_classification_to_accounts_batch` | 仅所在文件内部使用 | 负责 add classification to accounts batch 相关逻辑 |
| `AccountClassificationService._cleanup_all_old_assignments` | 仅所在文件内部使用 | 负责 cleanup all old assignments 相关逻辑 |
| `AccountClassificationService._log_performance_stats` | 仅所在文件内部使用 | 负责 log performance stats 相关逻辑 |
| `AccountClassificationService._rules_to_cache_data` | 仅所在文件内部使用 | 负责 rules to cache data 相关逻辑 |
| `AccountClassificationService._rules_from_cache_data` | 仅所在文件内部使用 | 负责 rules from cache data 相关逻辑 |
| `AccountClassificationService._accounts_to_cache_data` | 仅所在文件内部使用 | 负责 accounts to cache data 相关逻辑 |
| `AccountClassificationService.invalidate_cache` | 仅所在文件内部使用 | 负责 invalidate cache 相关逻辑 |
| `AccountClassificationService.invalidate_db_type_cache` | 仅所在文件内部使用 | 负责 invalidate db type cache 相关逻辑 |
| `AccountClassificationService.get_rule_matched_accounts_count` | 仅所在文件内部使用 | 负责 get rule matched accounts count 相关逻辑 |

## `app/services/statistics/account_statistics_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `_is_account_locked` | 仅所在文件内部使用 | 负责 is account locked 相关逻辑 |
| `fetch_summary` | 仅所在文件内部使用 | 负责 fetch summary 相关逻辑 |
| `fetch_db_type_stats` | 仅所在文件内部使用 | 负责 fetch db type stats 相关逻辑 |
| `fetch_classification_stats` | 仅所在文件内部使用 | 负责 fetch classification stats 相关逻辑 |
| `build_aggregated_statistics` | 仅所在文件内部使用 | 负责 build aggregated statistics 相关逻辑 |
| `empty_statistics` | 仅所在文件内部使用 | 负责 empty statistics 相关逻辑 |

## `app/services/statistics/log_statistics_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `fetch_log_trend_data` | `app/routes/dashboard.py` | 最近若干天日志趋势（错误/告警计数） |
| `fetch_log_level_distribution` | `app/routes/dashboard.py` | 日志级别分布统计 |

## `app/services/account_sync/account_query_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `get_accounts_by_instance` | 仅所在文件内部使用 | 负责 get accounts by instance 相关逻辑 |

## `app/services/account_sync/account_sync_filters.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseFilterManager.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `DatabaseFilterManager._load_filter_rules` | 仅所在文件内部使用 | 负责 load filter rules 相关逻辑 |
| `DatabaseFilterManager.get_safe_sql_filter_conditions` | 仅所在文件内部使用 | 负责 get safe sql filter conditions 相关逻辑 |
| `DatabaseFilterManager._match_pattern` | 仅所在文件内部使用 | 负责 match pattern 相关逻辑 |
| `DatabaseFilterManager.get_filter_rules` | 仅所在文件内部使用 | 负责 get filter rules 相关逻辑 |

## `app/services/account_sync/account_sync_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AccountSyncService.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `AccountSyncService.sync_accounts` | 仅所在文件内部使用 | 负责 sync accounts 相关逻辑 |
| `AccountSyncService._sync_single_instance` | 仅所在文件内部使用 | 负责 sync single instance 相关逻辑 |
| `AccountSyncService._sync_with_session` | 仅所在文件内部使用 | 负责 sync with session 相关逻辑 |
| `AccountSyncService._sync_with_existing_session` | 仅所在文件内部使用 | 负责 sync with existing session 相关逻辑 |
| `AccountSyncService._build_result` | 仅所在文件内部使用 | 负责 build result 相关逻辑 |
| `AccountSyncService._emit_completion_log` | 仅所在文件内部使用 | 负责 emit completion log 相关逻辑 |

## `app/services/account_sync/adapters/base_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `BaseAccountAdapter.fetch_remote_accounts` | 仅所在文件内部使用 | 负责 fetch remote accounts 相关逻辑 |
| `BaseAccountAdapter.enrich_permissions` | 仅所在文件内部使用 | 负责 enrich permissions 相关逻辑 |
| `BaseAccountAdapter._fetch_raw_accounts` | 仅所在文件内部使用 | 负责 fetch raw accounts 相关逻辑 |
| `BaseAccountAdapter._normalize_account` | 仅所在文件内部使用 | 负责 normalize account 相关逻辑 |

## `app/services/account_sync/adapters/factory.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `get_account_adapter` | 仅所在文件内部使用 | 负责 get account adapter 相关逻辑 |

## `app/services/account_sync/adapters/mysql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `MySQLAccountAdapter.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `MySQLAccountAdapter._fetch_raw_accounts` | 仅所在文件内部使用 | 负责 fetch raw accounts 相关逻辑 |
| `MySQLAccountAdapter._normalize_account` | 仅所在文件内部使用 | 负责 normalize account 相关逻辑 |
| `MySQLAccountAdapter._build_filter_conditions` | 仅所在文件内部使用 | 负责 build filter conditions 相关逻辑 |
| `MySQLAccountAdapter._get_user_permissions` | 仅所在文件内部使用 | 负责 get user permissions 相关逻辑 |
| `MySQLAccountAdapter.enrich_permissions` | 仅所在文件内部使用 | 负责 enrich permissions 相关逻辑 |
| `MySQLAccountAdapter._parse_grant_statement` | 仅所在文件内部使用 | 负责 parse grant statement 相关逻辑 |
| `MySQLAccountAdapter._extract_privileges` | 仅所在文件内部使用 | 负责 extract privileges 相关逻辑 |
| `MySQLAccountAdapter._expand_all_privileges` | 仅所在文件内部使用 | 负责 expand all privileges 相关逻辑 |

## `app/services/account_sync/adapters/oracle_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `OracleAccountAdapter.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `OracleAccountAdapter._fetch_raw_accounts` | 仅所在文件内部使用 | 负责 fetch raw accounts 相关逻辑 |
| `OracleAccountAdapter._normalize_account` | 仅所在文件内部使用 | 负责 normalize account 相关逻辑 |
| `OracleAccountAdapter._fetch_users` | 仅所在文件内部使用 | 负责 fetch users 相关逻辑 |
| `OracleAccountAdapter._get_user_permissions` | 仅所在文件内部使用 | 负责 get user permissions 相关逻辑 |
| `OracleAccountAdapter.enrich_permissions` | 仅所在文件内部使用 | 负责 enrich permissions 相关逻辑 |
| `OracleAccountAdapter._get_roles` | 仅所在文件内部使用 | 负责 get roles 相关逻辑 |
| `OracleAccountAdapter._get_system_privileges` | 仅所在文件内部使用 | 负责 get system privileges 相关逻辑 |
| `OracleAccountAdapter._get_tablespace_privileges` | 仅所在文件内部使用 | 负责 get tablespace privileges 相关逻辑 |

## `app/services/account_sync/adapters/postgresql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PostgreSQLAccountAdapter.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `PostgreSQLAccountAdapter._fetch_raw_accounts` | 仅所在文件内部使用 | 负责 fetch raw accounts 相关逻辑 |
| `PostgreSQLAccountAdapter._normalize_account` | 仅所在文件内部使用 | 负责 normalize account 相关逻辑 |
| `PostgreSQLAccountAdapter._build_filter_conditions` | 仅所在文件内部使用 | 负责 build filter conditions 相关逻辑 |
| `PostgreSQLAccountAdapter._get_role_permissions` | 仅所在文件内部使用 | 负责 get role permissions 相关逻辑 |
| `PostgreSQLAccountAdapter.enrich_permissions` | 仅所在文件内部使用 | 负责 enrich permissions 相关逻辑 |
| `PostgreSQLAccountAdapter._get_role_attributes` | 仅所在文件内部使用 | 负责 get role attributes 相关逻辑 |
| `PostgreSQLAccountAdapter._get_predefined_roles` | 仅所在文件内部使用 | 负责 get predefined roles 相关逻辑 |
| `PostgreSQLAccountAdapter._get_database_privileges` | 仅所在文件内部使用 | 负责 get database privileges 相关逻辑 |
| `PostgreSQLAccountAdapter._get_tablespace_privileges` | 仅所在文件内部使用 | 负责 get tablespace privileges 相关逻辑 |

## `app/services/account_sync/adapters/sqlserver_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLServerAccountAdapter.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `SQLServerAccountAdapter._fetch_raw_accounts` | 仅所在文件内部使用 | 负责 fetch raw accounts 相关逻辑 |
| `SQLServerAccountAdapter._normalize_account` | 仅所在文件内部使用 | 负责 normalize account 相关逻辑 |
| `SQLServerAccountAdapter.enrich_permissions` | 仅所在文件内部使用 | 负责 enrich permissions 相关逻辑 |
| `SQLServerAccountAdapter._fetch_logins` | 仅所在文件内部使用 | 负责 fetch logins 相关逻辑 |
| `SQLServerAccountAdapter._compile_like_patterns` | 仅所在文件内部使用 | 负责 compile like patterns 相关逻辑 |
| `SQLServerAccountAdapter._get_login_permissions` | 仅所在文件内部使用 | 负责 get login permissions 相关逻辑 |
| `SQLServerAccountAdapter._deduplicate_preserve_order` | 仅所在文件内部使用 | 负责 deduplicate preserve order 相关逻辑 |
| `SQLServerAccountAdapter._copy_database_permissions` | 仅所在文件内部使用 | 负责 copy database permissions 相关逻辑 |
| `SQLServerAccountAdapter._get_server_roles` | 仅所在文件内部使用 | 负责 get server roles 相关逻辑 |
| `SQLServerAccountAdapter._get_server_permissions` | 仅所在文件内部使用 | 负责 get server permissions 相关逻辑 |
| `SQLServerAccountAdapter._get_server_roles_bulk` | 仅所在文件内部使用 | 负责 get server roles bulk 相关逻辑 |
| `SQLServerAccountAdapter._get_server_permissions_bulk` | 仅所在文件内部使用 | 负责 get server permissions bulk 相关逻辑 |
| `SQLServerAccountAdapter._get_database_roles` | 仅所在文件内部使用 | 负责 get database roles 相关逻辑 |
| `SQLServerAccountAdapter._get_database_permissions` | 仅所在文件内部使用 | 负责 get database permissions 相关逻辑 |
| `SQLServerAccountAdapter._get_all_users_database_permissions_batch_optimized` | 仅所在文件内部使用 | 负责 get all users database permissions batch optimized 相关逻辑 |
| `SQLServerAccountAdapter._normalize_sid` | 仅所在文件内部使用 | 负责 normalize sid 相关逻辑 |
| `SQLServerAccountAdapter._sid_to_hex_literal` | 仅所在文件内部使用 | 负责 sid to hex literal 相关逻辑 |
| `SQLServerAccountAdapter._quote_identifier` | 仅所在文件内部使用 | 负责 quote identifier 相关逻辑 |
| `SQLServerAccountAdapter.clear_user_cache` | 仅所在文件内部使用 | 负责 clear user cache 相关逻辑 |
| `SQLServerAccountAdapter.clear_instance_cache` | 仅所在文件内部使用 | 负责 clear instance cache 相关逻辑 |

## `app/services/account_sync/coordinator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AccountSyncCoordinator.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `AccountSyncCoordinator.__enter__` | 仅所在文件内部使用 | 负责 enter 相关逻辑 |
| `AccountSyncCoordinator.__exit__` | 仅所在文件内部使用 | 负责 exit 相关逻辑 |
| `AccountSyncCoordinator.connect` | 仅所在文件内部使用 | 负责 connect 相关逻辑 |
| `AccountSyncCoordinator.disconnect` | 仅所在文件内部使用 | 负责 disconnect 相关逻辑 |
| `AccountSyncCoordinator._ensure_connection` | 仅所在文件内部使用 | 负责 ensure connection 相关逻辑 |
| `AccountSyncCoordinator.fetch_remote_accounts` | 仅所在文件内部使用 | 负责 fetch remote accounts 相关逻辑 |
| `AccountSyncCoordinator.synchronize_inventory` | 仅所在文件内部使用 | 负责 synchronize inventory 相关逻辑 |
| `AccountSyncCoordinator.synchronize_permissions` | 仅所在文件内部使用 | 负责 synchronize permissions 相关逻辑 |
| `AccountSyncCoordinator.sync_all` | 仅所在文件内部使用 | 负责 sync all 相关逻辑 |

## `app/services/account_sync/inventory_manager.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AccountInventoryManager.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `AccountInventoryManager.synchronize` | 仅所在文件内部使用 | 负责 synchronize 相关逻辑 |

## `app/services/account_sync/permission_manager.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PermissionSyncError.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `AccountPermissionManager.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `AccountPermissionManager.synchronize` | 仅所在文件内部使用 | 负责 synchronize 相关逻辑 |
| `AccountPermissionManager._apply_permissions` | 仅所在文件内部使用 | 负责 apply permissions 相关逻辑 |
| `AccountPermissionManager._calculate_diff` | 仅所在文件内部使用 | 负责 calculate diff 相关逻辑 |
| `AccountPermissionManager._log_change` | 仅所在文件内部使用 | 负责 log change 相关逻辑 |
| `AccountPermissionManager._build_initial_diff_payload` | 仅所在文件内部使用 | 负责 build initial diff payload 相关逻辑 |
| `AccountPermissionManager._build_privilege_diff_entries` | 仅所在文件内部使用 | 负责 build privilege diff entries 相关逻辑 |
| `AccountPermissionManager._build_other_diff_entry` | 仅所在文件内部使用 | 负责 build other diff entry 相关逻辑 |
| `AccountPermissionManager._build_other_description` | 仅所在文件内部使用 | 负责 build other description 相关逻辑 |
| `AccountPermissionManager._build_change_summary` | 仅所在文件内部使用 | 负责 build change summary 相关逻辑 |
| `AccountPermissionManager._is_mapping` | 仅所在文件内部使用 | 负责 is mapping 相关逻辑 |
| `AccountPermissionManager._normalize_mapping` | 仅所在文件内部使用 | 负责 normalize mapping 相关逻辑 |
| `AccountPermissionManager._normalize_sequence` | 仅所在文件内部使用 | 负责 normalize sequence 相关逻辑 |
| `AccountPermissionManager._repr_value` | 仅所在文件内部使用 | 负责 repr value 相关逻辑 |
| `AccountPermissionManager._count_permissions_by_action` | 仅所在文件内部使用 | 负责 count permissions by action 相关逻辑 |

## `app/services/aggregation/aggregation_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `AggregationService.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `AggregationService._get_instance_or_raise` | 仅所在文件内部使用 | 负责 get instance or raise 相关逻辑 |
| `AggregationService._ensure_partition_for_date` | 仅所在文件内部使用 | 负责 ensure partition for date 相关逻辑 |
| `AggregationService._commit_with_partition_retry` | 仅所在文件内部使用 | 负责 commit with partition retry 相关逻辑 |
| `AggregationService.calculate_all_aggregations` | 仅所在文件内部使用 | 负责 calculate all aggregations 相关逻辑 |
| `AggregationService.calculate_daily_aggregations` | 仅所在文件内部使用 | 负责 calculate daily aggregations 相关逻辑 |
| `AggregationService.aggregate_current_period` | 仅所在文件内部使用 | 负责 aggregate current period 相关逻辑 |
| `AggregationService.calculate_weekly_aggregations` | 仅所在文件内部使用 | 负责 calculate weekly aggregations 相关逻辑 |
| `AggregationService.calculate_monthly_aggregations` | 仅所在文件内部使用 | 负责 calculate monthly aggregations 相关逻辑 |
| `AggregationService.calculate_quarterly_aggregations` | 仅所在文件内部使用 | 负责 calculate quarterly aggregations 相关逻辑 |
| `AggregationService.calculate_daily_database_aggregations_for_instance` | 仅所在文件内部使用 | 负责 calculate daily database aggregations for instance 相关逻辑 |
| `AggregationService.calculate_weekly_database_aggregations_for_instance` | 仅所在文件内部使用 | 负责 calculate weekly database aggregations for instance 相关逻辑 |
| `AggregationService.calculate_monthly_database_aggregations_for_instance` | 仅所在文件内部使用 | 负责 calculate monthly database aggregations for instance 相关逻辑 |
| `AggregationService.calculate_quarterly_database_aggregations_for_instance` | 仅所在文件内部使用 | 负责 calculate quarterly database aggregations for instance 相关逻辑 |
| `AggregationService.calculate_daily_instance_aggregations` | 仅所在文件内部使用 | 负责 calculate daily instance aggregations 相关逻辑 |
| `AggregationService.calculate_weekly_instance_aggregations` | 仅所在文件内部使用 | 负责 calculate weekly instance aggregations 相关逻辑 |
| `AggregationService.calculate_monthly_instance_aggregations` | 仅所在文件内部使用 | 负责 calculate monthly instance aggregations 相关逻辑 |
| `AggregationService.calculate_quarterly_instance_aggregations` | 仅所在文件内部使用 | 负责 calculate quarterly instance aggregations 相关逻辑 |
| `AggregationService.calculate_instance_aggregations` | 仅所在文件内部使用 | 负责 calculate instance aggregations 相关逻辑 |
| `AggregationService.calculate_daily_aggregations_for_instance` | 仅所在文件内部使用 | 负责 calculate daily aggregations for instance 相关逻辑 |
| `AggregationService.calculate_weekly_aggregations_for_instance` | 仅所在文件内部使用 | 负责 calculate weekly aggregations for instance 相关逻辑 |
| `AggregationService.calculate_monthly_aggregations_for_instance` | 仅所在文件内部使用 | 负责 calculate monthly aggregations for instance 相关逻辑 |
| `AggregationService.calculate_quarterly_aggregations_for_instance` | 仅所在文件内部使用 | 负责 calculate quarterly aggregations for instance 相关逻辑 |
| `AggregationService.calculate_period_aggregations` | 仅所在文件内部使用 | 负责 calculate period aggregations 相关逻辑 |
| `AggregationService.get_aggregations` | 仅所在文件内部使用 | 负责 get aggregations 相关逻辑 |
| `AggregationService.get_instance_aggregations` | 仅所在文件内部使用 | 负责 get instance aggregations 相关逻辑 |
| `AggregationService._format_aggregation` | 仅所在文件内部使用 | 负责 format aggregation 相关逻辑 |
| `AggregationService._format_instance_aggregation` | 仅所在文件内部使用 | 负责 format instance aggregation 相关逻辑 |

## `app/services/aggregation/calculator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PeriodCalculator.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `PeriodCalculator.today` | 仅所在文件内部使用 | 负责 today 相关逻辑 |
| `PeriodCalculator.get_last_period` | 仅所在文件内部使用 | 负责 get last period 相关逻辑 |
| `PeriodCalculator.get_current_period` | 仅所在文件内部使用 | 负责 get current period 相关逻辑 |
| `PeriodCalculator.get_previous_period` | 仅所在文件内部使用 | 负责 get previous period 相关逻辑 |
| `PeriodCalculator._normalize` | 仅所在文件内部使用 | 负责 normalize 相关逻辑 |

## `app/services/aggregation/database_aggregation_runner.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseAggregationRunner.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `DatabaseAggregationRunner._invoke_callback` | 仅所在文件内部使用 | 负责 invoke callback 相关逻辑 |
| `DatabaseAggregationRunner.aggregate_period` | 仅所在文件内部使用 | 负责 aggregate period 相关逻辑 |
| `DatabaseAggregationRunner.aggregate_database_period` | 仅所在文件内部使用 | 负责 aggregate database period 相关逻辑 |
| `DatabaseAggregationRunner.aggregate_daily_for_instance` | 仅所在文件内部使用 | 负责 aggregate daily for instance 相关逻辑 |
| `DatabaseAggregationRunner._query_database_stats` | 仅所在文件内部使用 | 负责 query database stats 相关逻辑 |
| `DatabaseAggregationRunner._group_by_database` | 仅所在文件内部使用 | 负责 group by database 相关逻辑 |
| `DatabaseAggregationRunner._persist_database_aggregation` | 仅所在文件内部使用 | 负责 persist database aggregation 相关逻辑 |
| `DatabaseAggregationRunner._apply_change_statistics` | 仅所在文件内部使用 | 负责 apply change statistics 相关逻辑 |

## `app/services/aggregation/instance_aggregation_runner.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `InstanceAggregationRunner.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `InstanceAggregationRunner._invoke_callback` | 仅所在文件内部使用 | 负责 invoke callback 相关逻辑 |
| `InstanceAggregationRunner.aggregate_period` | 仅所在文件内部使用 | 负责 aggregate period 相关逻辑 |
| `InstanceAggregationRunner.aggregate_instance_period` | 仅所在文件内部使用 | 负责 aggregate instance period 相关逻辑 |
| `InstanceAggregationRunner._query_instance_stats` | 仅所在文件内部使用 | 负责 query instance stats 相关逻辑 |
| `InstanceAggregationRunner._persist_instance_aggregation` | 仅所在文件内部使用 | 负责 persist instance aggregation 相关逻辑 |
| `InstanceAggregationRunner._apply_change_statistics` | 仅所在文件内部使用 | 负责 apply change statistics 相关逻辑 |

## `app/services/aggregation/results.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PeriodSummary.status` | 仅所在文件内部使用 | 负责 status 相关逻辑 |
| `PeriodSummary.to_dict` | 仅所在文件内部使用 | 负责 to dict 相关逻辑 |
| `InstanceSummary.status` | 仅所在文件内部使用 | 负责 status 相关逻辑 |
| `InstanceSummary.to_dict` | 仅所在文件内部使用 | 负责 to dict 相关逻辑 |

## `app/services/cache_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CacheService.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `CacheService._generate_cache_key` | 仅所在文件内部使用 | 负责 generate cache key 相关逻辑 |
| `CacheService.invalidate_user_cache` | 仅所在文件内部使用 | 负责 invalidate user cache 相关逻辑 |
| `CacheService.invalidate_instance_cache` | 仅所在文件内部使用 | 负责 invalidate instance cache 相关逻辑 |
| `CacheService.get_cache_stats` | 仅所在文件内部使用 | 负责 get cache stats 相关逻辑 |
| `CacheService.get_rule_evaluation_cache` | 仅所在文件内部使用 | 负责 get rule evaluation cache 相关逻辑 |
| `CacheService.set_rule_evaluation_cache` | 仅所在文件内部使用 | 负责 set rule evaluation cache 相关逻辑 |
| `CacheService.get_classification_rules_cache` | 仅所在文件内部使用 | 负责 get classification rules cache 相关逻辑 |
| `CacheService.set_classification_rules_cache` | 仅所在文件内部使用 | 负责 set classification rules cache 相关逻辑 |
| `CacheService.invalidate_account_cache` | 仅所在文件内部使用 | 负责 invalidate account cache 相关逻辑 |
| `CacheService.invalidate_classification_cache` | 仅所在文件内部使用 | 负责 invalidate classification cache 相关逻辑 |
| `CacheService.invalidate_all_rule_evaluation_cache` | 仅所在文件内部使用 | 负责 invalidate all rule evaluation cache 相关逻辑 |
| `CacheService.get_classification_rules_by_db_type_cache` | 仅所在文件内部使用 | 负责 get classification rules by db type cache 相关逻辑 |
| `CacheService.set_classification_rules_by_db_type_cache` | 仅所在文件内部使用 | 负责 set classification rules by db type cache 相关逻辑 |
| `CacheService.get_accounts_by_db_type_cache` | 仅所在文件内部使用 | 负责 get accounts by db type cache 相关逻辑 |
| `CacheService.set_accounts_by_db_type_cache` | 仅所在文件内部使用 | 负责 set accounts by db type cache 相关逻辑 |
| `CacheService.invalidate_db_type_cache` | 仅所在文件内部使用 | 负责 invalidate db type cache 相关逻辑 |
| `CacheService.invalidate_all_db_type_cache` | 仅所在文件内部使用 | 负责 invalidate all db type cache 相关逻辑 |
| `CacheService.health_check` | 仅所在文件内部使用 | 负责 health check 相关逻辑 |
| `init_cache_service` | 仅所在文件内部使用 | 负责 init cache service 相关逻辑 |
| `init_cache_manager` | 仅所在文件内部使用 | 负责 init cache manager 相关逻辑 |

## `app/services/connection_adapters/connection_factory.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `_get_default_schema` | 仅所在文件内部使用 | 负责 get default schema 相关逻辑 |
| `DatabaseConnection.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `DatabaseConnection.connect` | 仅所在文件内部使用 | 负责 connect 相关逻辑 |
| `DatabaseConnection.disconnect` | 仅所在文件内部使用 | 负责 disconnect 相关逻辑 |
| `DatabaseConnection.test_connection` | 仅所在文件内部使用 | 负责 test connection 相关逻辑 |
| `DatabaseConnection.execute_query` | 仅所在文件内部使用 | 负责 execute query 相关逻辑 |
| `DatabaseConnection.get_version` | 仅所在文件内部使用 | 负责 get version 相关逻辑 |
| `MySQLConnection.connect` | 仅所在文件内部使用 | 负责 connect 相关逻辑 |
| `MySQLConnection.disconnect` | 仅所在文件内部使用 | 负责 disconnect 相关逻辑 |
| `MySQLConnection.test_connection` | 仅所在文件内部使用 | 负责 test connection 相关逻辑 |
| `MySQLConnection.execute_query` | 仅所在文件内部使用 | 负责 execute query 相关逻辑 |
| `MySQLConnection.get_version` | 仅所在文件内部使用 | 负责 get version 相关逻辑 |
| `PostgreSQLConnection.connect` | 仅所在文件内部使用 | 负责 connect 相关逻辑 |
| `PostgreSQLConnection.disconnect` | 仅所在文件内部使用 | 负责 disconnect 相关逻辑 |
| `PostgreSQLConnection.test_connection` | 仅所在文件内部使用 | 负责 test connection 相关逻辑 |
| `PostgreSQLConnection.execute_query` | 仅所在文件内部使用 | 负责 execute query 相关逻辑 |
| `PostgreSQLConnection.get_version` | 仅所在文件内部使用 | 负责 get version 相关逻辑 |
| `SQLServerConnection.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `SQLServerConnection.connect` | 仅所在文件内部使用 | 负责 connect 相关逻辑 |
| `SQLServerConnection._try_pymssql_connection` | 仅所在文件内部使用 | 负责 try pymssql connection 相关逻辑 |
| `SQLServerConnection.disconnect` | 仅所在文件内部使用 | 负责 disconnect 相关逻辑 |
| `SQLServerConnection.test_connection` | 仅所在文件内部使用 | 负责 test connection 相关逻辑 |
| `SQLServerConnection.execute_query` | 仅所在文件内部使用 | 负责 execute query 相关逻辑 |
| `SQLServerConnection.get_version` | 仅所在文件内部使用 | 负责 get version 相关逻辑 |
| `OracleConnection.connect` | 仅所在文件内部使用 | 负责 connect 相关逻辑 |
| `OracleConnection.disconnect` | 仅所在文件内部使用 | 负责 disconnect 相关逻辑 |
| `OracleConnection.test_connection` | 仅所在文件内部使用 | 负责 test connection 相关逻辑 |
| `OracleConnection.execute_query` | 仅所在文件内部使用 | 负责 execute query 相关逻辑 |
| `OracleConnection.get_version` | 仅所在文件内部使用 | 负责 get version 相关逻辑 |
| `ConnectionFactory.create_connection` | 仅所在文件内部使用 | 负责 create connection 相关逻辑 |
| `ConnectionFactory.test_connection` | 仅所在文件内部使用 | 负责 test connection 相关逻辑 |
| `ConnectionFactory.get_supported_types` | 仅所在文件内部使用 | 负责 get supported types 相关逻辑 |
| `ConnectionFactory.is_type_supported` | 仅所在文件内部使用 | 负责 is type supported 相关逻辑 |

## `app/services/connection_adapters/connection_test_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `ConnectionTestService.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `ConnectionTestService.test_connection` | 仅所在文件内部使用 | 负责 test connection 相关逻辑 |
| `ConnectionTestService._update_last_connected` | 仅所在文件内部使用 | 负责 update last connected 相关逻辑 |
| `ConnectionTestService._get_database_version` | 仅所在文件内部使用 | 负责 get database version 相关逻辑 |

## `app/services/database_sync/adapters/base_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `BaseCapacityAdapter.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `BaseCapacityAdapter.fetch_inventory` | 仅所在文件内部使用 | 负责 fetch inventory 相关逻辑 |
| `BaseCapacityAdapter.fetch_capacity` | 仅所在文件内部使用 | 负责 fetch capacity 相关逻辑 |
| `BaseCapacityAdapter._normalize_targets` | 仅所在文件内部使用 | 负责 normalize targets 相关逻辑 |

## `app/services/database_sync/adapters/factory.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `get_capacity_adapter` | 仅所在文件内部使用 | 负责 get capacity adapter 相关逻辑 |

## `app/services/database_sync/adapters/mysql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `MySQLCapacityAdapter.fetch_inventory` | 仅所在文件内部使用 | 负责 fetch inventory 相关逻辑 |
| `MySQLCapacityAdapter.fetch_capacity` | 仅所在文件内部使用 | 负责 fetch capacity 相关逻辑 |
| `MySQLCapacityAdapter._assert_permission` | 仅所在文件内部使用 | 负责 assert permission 相关逻辑 |
| `MySQLCapacityAdapter._collect_tablespace_sizes` | 仅所在文件内部使用 | 负责 collect tablespace sizes 相关逻辑 |
| `MySQLCapacityAdapter._build_stats_from_tablespaces` | 仅所在文件内部使用 | 负责 build stats from tablespaces 相关逻辑 |
| `MySQLCapacityAdapter._build_tablespace_queries` | 仅所在文件内部使用 | 负责 build tablespace queries 相关逻辑 |

## `app/services/database_sync/adapters/oracle_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `OracleCapacityAdapter.fetch_inventory` | 仅所在文件内部使用 | 负责 fetch inventory 相关逻辑 |
| `OracleCapacityAdapter.fetch_capacity` | 仅所在文件内部使用 | 负责 fetch capacity 相关逻辑 |

## `app/services/database_sync/adapters/postgresql_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PostgreSQLCapacityAdapter.fetch_inventory` | 仅所在文件内部使用 | 负责 fetch inventory 相关逻辑 |
| `PostgreSQLCapacityAdapter.fetch_capacity` | 仅所在文件内部使用 | 负责 fetch capacity 相关逻辑 |

## `app/services/database_sync/adapters/sqlserver_adapter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLServerCapacityAdapter.fetch_inventory` | 仅所在文件内部使用 | 负责 fetch inventory 相关逻辑 |
| `SQLServerCapacityAdapter.fetch_capacity` | 仅所在文件内部使用 | 负责 fetch capacity 相关逻辑 |

## `app/services/database_sync/coordinator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CapacitySyncCoordinator.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `CapacitySyncCoordinator.inventory_manager` | 仅所在文件内部使用 | 负责 inventory manager 相关逻辑 |
| `CapacitySyncCoordinator.persistence` | 仅所在文件内部使用 | 负责 persistence 相关逻辑 |
| `CapacitySyncCoordinator.connect` | 仅所在文件内部使用 | 负责 connect 相关逻辑 |
| `CapacitySyncCoordinator.disconnect` | 仅所在文件内部使用 | 负责 disconnect 相关逻辑 |
| `CapacitySyncCoordinator.synchronize_inventory` | 仅所在文件内部使用 | 负责 synchronize inventory 相关逻辑 |
| `CapacitySyncCoordinator.fetch_inventory` | 仅所在文件内部使用 | 负责 fetch inventory 相关逻辑 |
| `CapacitySyncCoordinator.sync_instance_databases` | 仅所在文件内部使用 | 负责 sync instance databases 相关逻辑 |
| `CapacitySyncCoordinator.collect_capacity` | 仅所在文件内部使用 | 负责 collect capacity 相关逻辑 |
| `CapacitySyncCoordinator.save_database_stats` | 仅所在文件内部使用 | 负责 save database stats 相关逻辑 |
| `CapacitySyncCoordinator.save_instance_stats` | 仅所在文件内部使用 | 负责 save instance stats 相关逻辑 |
| `CapacitySyncCoordinator.update_instance_total_size` | 仅所在文件内部使用 | 负责 update instance total size 相关逻辑 |
| `CapacitySyncCoordinator.collect_and_save` | 仅所在文件内部使用 | 负责 collect and save 相关逻辑 |
| `CapacitySyncCoordinator._ensure_connection` | 仅所在文件内部使用 | 负责 ensure connection 相关逻辑 |

## `app/services/database_sync/database_filters.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseSyncFilterManager.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `DatabaseSyncFilterManager.config_path` | 仅所在文件内部使用 | 负责 config path 相关逻辑 |
| `DatabaseSyncFilterManager.reload` | 仅所在文件内部使用 | 负责 reload 相关逻辑 |
| `DatabaseSyncFilterManager._compile_pattern` | 仅所在文件内部使用 | 负责 compile pattern 相关逻辑 |
| `DatabaseSyncFilterManager.should_exclude_database` | 仅所在文件内部使用 | 负责 should exclude database 相关逻辑 |
| `DatabaseSyncFilterManager.filter_database_names` | 仅所在文件内部使用 | 负责 filter database names 相关逻辑 |
| `DatabaseSyncFilterManager.filter_capacity_payload` | 仅所在文件内部使用 | 负责 filter capacity payload 相关逻辑 |

## `app/services/database_sync/database_sync_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseSizeCollectorService.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `DatabaseSizeCollectorService.__enter__` | 仅所在文件内部使用 | 负责 enter 相关逻辑 |
| `DatabaseSizeCollectorService.__exit__` | 仅所在文件内部使用 | 负责 exit 相关逻辑 |
| `DatabaseSizeCollectorService.connect` | 仅所在文件内部使用 | 负责 connect 相关逻辑 |
| `DatabaseSizeCollectorService.disconnect` | 仅所在文件内部使用 | 负责 disconnect 相关逻辑 |
| `DatabaseSizeCollectorService.fetch_databases_metadata` | 仅所在文件内部使用 | 负责 fetch databases metadata 相关逻辑 |
| `DatabaseSizeCollectorService.sync_instance_databases` | 仅所在文件内部使用 | 负责 sync instance databases 相关逻辑 |
| `DatabaseSizeCollectorService.synchronize_database_inventory` | 仅所在文件内部使用 | 负责 synchronize database inventory 相关逻辑 |
| `DatabaseSizeCollectorService.collect_database_sizes` | 仅所在文件内部使用 | 负责 collect database sizes 相关逻辑 |
| `DatabaseSizeCollectorService.save_collected_data` | 仅所在文件内部使用 | 负责 save collected data 相关逻辑 |
| `DatabaseSizeCollectorService.save_instance_size_stat` | 仅所在文件内部使用 | 负责 save instance size stat 相关逻辑 |
| `DatabaseSizeCollectorService.update_instance_total_size` | 仅所在文件内部使用 | 负责 update instance total size 相关逻辑 |
| `DatabaseSizeCollectorService.collect_and_save` | 仅所在文件内部使用 | 负责 collect and save 相关逻辑 |
| `collect_all_instances_database_sizes` | 仅所在文件内部使用 | 负责 collect all instances database sizes 相关逻辑 |

## `app/services/database_sync/inventory_manager.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `InventoryManager.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `InventoryManager.synchronize` | 仅所在文件内部使用 | 负责 synchronize 相关逻辑 |

## `app/services/database_sync/persistence.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CapacityPersistence.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `CapacityPersistence.save_database_stats` | 仅所在文件内部使用 | 负责 save database stats 相关逻辑 |
| `CapacityPersistence.save_instance_stats` | 仅所在文件内部使用 | 负责 save instance stats 相关逻辑 |
| `CapacityPersistence.update_instance_total_size` | 仅所在文件内部使用 | 负责 update instance total size 相关逻辑 |

## `app/services/database_type_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseTypeService.get_all_types` | 仅所在文件内部使用 | 负责 get all types 相关逻辑 |
| `DatabaseTypeService.get_active_types` | 仅所在文件内部使用 | 负责 get active types 相关逻辑 |
| `DatabaseTypeService.get_type_by_name` | 仅所在文件内部使用 | 负责 get type by name 相关逻辑 |
| `DatabaseTypeService.get_database_types_for_form` | 仅所在文件内部使用 | 负责 get database types for form 相关逻辑 |

## `app/services/partition_management_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PartitionAction.to_dict` | 仅所在文件内部使用 | 负责 to dict 相关逻辑 |
| `PartitionManagementService.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `PartitionManagementService.create_partition` | 仅所在文件内部使用 | 负责 create partition 相关逻辑 |
| `PartitionManagementService.create_future_partitions` | 仅所在文件内部使用 | 负责 create future partitions 相关逻辑 |
| `PartitionManagementService.cleanup_old_partitions` | 仅所在文件内部使用 | 负责 cleanup old partitions 相关逻辑 |
| `PartitionManagementService._month_window` | 仅所在文件内部使用 | 负责 month window 相关逻辑 |
| `PartitionManagementService._get_table_partitions` | 仅所在文件内部使用 | 负责 get table partitions 相关逻辑 |
| `PartitionManagementService._partition_exists` | 仅所在文件内部使用 | 负责 partition exists 相关逻辑 |
| `PartitionManagementService._get_partitions_to_cleanup` | 仅所在文件内部使用 | 负责 get partitions to cleanup 相关逻辑 |
| `PartitionManagementService._extract_date_from_partition_name` | 仅所在文件内部使用 | 负责 extract date from partition name 相关逻辑 |
| `PartitionManagementService._get_partition_record_count` | 仅所在文件内部使用 | 负责 get partition record count 相关逻辑 |
| `PartitionManagementService._get_partition_status` | 仅所在文件内部使用 | 负责 get partition status 相关逻辑 |
| `PartitionManagementService._create_partition_indexes` | 仅所在文件内部使用 | 负责 create partition indexes 相关逻辑 |
| `PartitionManagementService._format_size` | 仅所在文件内部使用 | 负责 format size 相关逻辑 |
| `PartitionManagementService._rollback_on_error` | 仅所在文件内部使用 | 负责 rollback on error 相关逻辑 |

## `app/services/sync_session_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SyncSessionService.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `SyncSessionService._clean_sync_details` | 仅所在文件内部使用 | 负责 clean sync details 相关逻辑 |
| `SyncSessionService.create_session` | 仅所在文件内部使用 | 负责 create session 相关逻辑 |
| `SyncSessionService.add_instance_records` | 仅所在文件内部使用 | 负责 add instance records 相关逻辑 |
| `SyncSessionService.start_instance_sync` | 仅所在文件内部使用 | 负责 start instance sync 相关逻辑 |
| `SyncSessionService.complete_instance_sync` | 仅所在文件内部使用 | 负责 complete instance sync 相关逻辑 |
| `SyncSessionService.fail_instance_sync` | 仅所在文件内部使用 | 负责 fail instance sync 相关逻辑 |
| `SyncSessionService._update_session_statistics` | 仅所在文件内部使用 | 负责 update session statistics 相关逻辑 |
| `SyncSessionService.get_session_records` | 仅所在文件内部使用 | 负责 get session records 相关逻辑 |
| `SyncSessionService.get_session_by_id` | 仅所在文件内部使用 | 负责 get session by id 相关逻辑 |
| `SyncSessionService.get_sessions_by_type` | 仅所在文件内部使用 | 负责 get sessions by type 相关逻辑 |
| `SyncSessionService.get_sessions_by_category` | 仅所在文件内部使用 | 负责 get sessions by category 相关逻辑 |
| `SyncSessionService.get_recent_sessions` | 仅所在文件内部使用 | 负责 get recent sessions 相关逻辑 |
| `SyncSessionService.cancel_session` | 仅所在文件内部使用 | 负责 cancel session 相关逻辑 |

## `app/utils/cache_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `CacheManager.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `CacheManager._generate_key` | 仅所在文件内部使用 | 负责 generate key 相关逻辑 |
| `CacheManager.get` | 仅所在文件内部使用 | 负责 get 相关逻辑 |
| `CacheManager.set` | 仅所在文件内部使用 | 负责 set 相关逻辑 |
| `CacheManager.delete` | 仅所在文件内部使用 | 负责 delete 相关逻辑 |
| `CacheManager.clear` | 仅所在文件内部使用 | 负责 clear 相关逻辑 |
| `CacheManager.get_or_set` | 仅所在文件内部使用 | 负责 get or set 相关逻辑 |
| `CacheManager.invalidate_pattern` | 仅所在文件内部使用 | 负责 invalidate pattern 相关逻辑 |
| `init_cache_manager` | 仅所在文件内部使用 | 负责 init cache manager 相关逻辑 |
| `cached` | 仅所在文件内部使用 | 负责 cached 相关逻辑 |
| `dashboard_cache` | 仅所在文件内部使用 | 负责 dashboard cache 相关逻辑 |

## `app/utils/data_validator.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DataValidator.validate_instance_data` | 仅所在文件内部使用 | 负责 validate instance data 相关逻辑 |
| `DataValidator._validate_name` | 仅所在文件内部使用 | 负责 validate name 相关逻辑 |
| `DataValidator._validate_db_type` | 仅所在文件内部使用 | 负责 validate db type 相关逻辑 |
| `DataValidator._validate_host` | 仅所在文件内部使用 | 负责 validate host 相关逻辑 |
| `DataValidator._validate_port` | 仅所在文件内部使用 | 负责 validate port 相关逻辑 |
| `DataValidator._validate_database_name` | 仅所在文件内部使用 | 负责 validate database name 相关逻辑 |
| `DataValidator._validate_description` | 仅所在文件内部使用 | 负责 validate description 相关逻辑 |
| `DataValidator._validate_credential_id` | 仅所在文件内部使用 | 负责 validate credential id 相关逻辑 |
| `DataValidator._is_valid_host` | 仅所在文件内部使用 | 负责 is valid host 相关逻辑 |
| `DataValidator.validate_batch_data` | 仅所在文件内部使用 | 负责 validate batch data 相关逻辑 |
| `DataValidator.sanitize_string` | 仅所在文件内部使用 | 负责 sanitize string 相关逻辑 |
| `DataValidator.sanitize_input` | 仅所在文件内部使用 | 负责 sanitize input 相关逻辑 |
| `DataValidator.sanitize_form_data` | 仅所在文件内部使用 | 负责 sanitize form data 相关逻辑 |
| `DataValidator.validate_required_fields` | 仅所在文件内部使用 | 负责 validate required fields 相关逻辑 |
| `DataValidator.validate_db_type` | 仅所在文件内部使用 | 负责 validate db type 相关逻辑 |
| `DataValidator.validate_credential_type` | 仅所在文件内部使用 | 负责 validate credential type 相关逻辑 |
| `DataValidator.validate_username` | 仅所在文件内部使用 | 负责 validate username 相关逻辑 |
| `DataValidator.validate_password` | 仅所在文件内部使用 | 负责 validate password 相关逻辑 |
| `sanitize_form_data` | 仅所在文件内部使用 | 负责 sanitize form data 相关逻辑 |
| `validate_required_fields` | 仅所在文件内部使用 | 负责 validate required fields 相关逻辑 |
| `validate_db_type` | 仅所在文件内部使用 | 负责 validate db type 相关逻辑 |
| `validate_credential_type` | 仅所在文件内部使用 | 负责 validate credential type 相关逻辑 |
| `validate_username` | 仅所在文件内部使用 | 负责 validate username 相关逻辑 |
| `validate_password` | 仅所在文件内部使用 | 负责 validate password 相关逻辑 |

## `app/utils/database_batch_manager.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseBatchManager.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `DatabaseBatchManager.add_operation` | 仅所在文件内部使用 | 负责 add operation 相关逻辑 |
| `DatabaseBatchManager.commit_batch` | 仅所在文件内部使用 | 负责 commit batch 相关逻辑 |
| `DatabaseBatchManager.flush_remaining` | 仅所在文件内部使用 | 负责 flush remaining 相关逻辑 |
| `DatabaseBatchManager.rollback` | 仅所在文件内部使用 | 负责 rollback 相关逻辑 |
| `DatabaseBatchManager.get_statistics` | 仅所在文件内部使用 | 负责 get statistics 相关逻辑 |
| `DatabaseBatchManager.__enter__` | 仅所在文件内部使用 | 负责 enter 相关逻辑 |
| `DatabaseBatchManager.__exit__` | 仅所在文件内部使用 | 负责 exit 相关逻辑 |

## `app/utils/decorators.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `admin_required` | 仅所在文件内部使用 | 负责 admin required 相关逻辑 |
| `login_required` | 仅所在文件内部使用 | 负责 login required 相关逻辑 |
| `permission_required` | 仅所在文件内部使用 | 负责 permission required 相关逻辑 |
| `_extract_csrf_token` | 仅所在文件内部使用 | 负责 extract csrf token 相关逻辑 |
| `require_csrf` | 仅所在文件内部使用 | 负责 require csrf 相关逻辑 |
| `has_permission` | 仅所在文件内部使用 | 负责 has permission 相关逻辑 |
| `view_required` | 仅所在文件内部使用 | 负责 view required 相关逻辑 |
| `create_required` | 仅所在文件内部使用 | 负责 create required 相关逻辑 |
| `update_required` | 仅所在文件内部使用 | 负责 update required 相关逻辑 |
| `delete_required` | 仅所在文件内部使用 | 负责 delete required 相关逻辑 |
| `scheduler_view_required` | 仅所在文件内部使用 | 负责 scheduler view required 相关逻辑 |
| `scheduler_manage_required` | 仅所在文件内部使用 | 负责 scheduler manage required 相关逻辑 |

## `app/utils/password_crypto_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PasswordManager.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `PasswordManager._get_or_create_key` | 仅所在文件内部使用 | 负责 get or create key 相关逻辑 |
| `PasswordManager.encrypt_password` | 仅所在文件内部使用 | 负责 encrypt password 相关逻辑 |
| `PasswordManager.decrypt_password` | 仅所在文件内部使用 | 负责 decrypt password 相关逻辑 |
| `PasswordManager.is_encrypted` | 仅所在文件内部使用 | 负责 is encrypted 相关逻辑 |
| `get_password_manager` | 仅所在文件内部使用 | 负责 get password manager 相关逻辑 |

## `app/utils/query_filter_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `get_active_tags` | 仅所在文件内部使用 | 负责 get active tags 相关逻辑 |
| `get_active_tag_options` | 仅所在文件内部使用 | 负责 get active tag options 相关逻辑 |
| `get_tag_categories` | 仅所在文件内部使用 | 负责 get tag categories 相关逻辑 |
| `get_classifications` | 仅所在文件内部使用 | 负责 get classifications 相关逻辑 |
| `get_classification_options` | 仅所在文件内部使用 | 负责 get classification options 相关逻辑 |
| `get_instances_by_db_type` | 仅所在文件内部使用 | 负责 get instances by db type 相关逻辑 |
| `get_instance_options` | 仅所在文件内部使用 | 负责 get instance options 相关逻辑 |
| `get_databases_by_instance` | 仅所在文件内部使用 | 负责 get databases by instance 相关逻辑 |
| `get_database_options` | 仅所在文件内部使用 | 负责 get database options 相关逻辑 |
| `get_log_modules` | 仅所在文件内部使用 | 负责 get log modules 相关逻辑 |

## `app/utils/rate_limiter.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `RateLimiter.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `RateLimiter._get_key` | 仅所在文件内部使用 | 负责 get key 相关逻辑 |
| `RateLimiter._get_memory_key` | 仅所在文件内部使用 | 负责 get memory key 相关逻辑 |
| `RateLimiter.is_allowed` | 仅所在文件内部使用 | 负责 is allowed 相关逻辑 |
| `RateLimiter._check_cache` | 仅所在文件内部使用 | 负责 check cache 相关逻辑 |
| `RateLimiter._check_memory` | 仅所在文件内部使用 | 负责 check memory 相关逻辑 |
| `login_rate_limit` | 仅所在文件内部使用 | 负责 login rate limit 相关逻辑 |
| `password_reset_rate_limit` | 仅所在文件内部使用 | 负责 password reset rate limit 相关逻辑 |
| `init_rate_limiter` | 仅所在文件内部使用 | 负责 init rate limiter 相关逻辑 |

## `app/utils/response_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `unified_success_response` | 仅所在文件内部使用 | 负责 unified success response 相关逻辑 |
| `unified_error_response` | 仅所在文件内部使用 | 负责 unified error response 相关逻辑 |
| `jsonify_unified_success` | 仅所在文件内部使用 | 负责 jsonify unified success 相关逻辑 |
| `jsonify_unified_error` | 仅所在文件内部使用 | 负责 jsonify unified error 相关逻辑 |
| `jsonify_unified_error_message` | 仅所在文件内部使用 | 负责 jsonify unified error message 相关逻辑 |

## `app/utils/safe_query_builder.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SafeQueryBuilder.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `SafeQueryBuilder.add_condition` | 仅所在文件内部使用 | 负责 add condition 相关逻辑 |
| `SafeQueryBuilder._generate_placeholder` | 仅所在文件内部使用 | 负责 generate placeholder 相关逻辑 |
| `SafeQueryBuilder.add_in_condition` | 仅所在文件内部使用 | 负责 add in condition 相关逻辑 |
| `SafeQueryBuilder.add_not_in_condition` | 仅所在文件内部使用 | 负责 add not in condition 相关逻辑 |
| `SafeQueryBuilder.add_like_condition` | 仅所在文件内部使用 | 负责 add like condition 相关逻辑 |
| `SafeQueryBuilder.add_not_like_condition` | 仅所在文件内部使用 | 负责 add not like condition 相关逻辑 |
| `SafeQueryBuilder.build_where_clause` | 仅所在文件内部使用 | 负责 build where clause 相关逻辑 |
| `SafeQueryBuilder.add_database_specific_condition` | 仅所在文件内部使用 | 负责 add database specific condition 相关逻辑 |
| `SafeQueryBuilder.reset` | 仅所在文件内部使用 | 负责 reset 相关逻辑 |
| `build_safe_filter_conditions` | 仅所在文件内部使用 | 负责 build safe filter conditions 相关逻辑 |
| `build_safe_filter_conditions_list` | 仅所在文件内部使用 | 负责 build safe filter conditions list 相关逻辑 |

## `app/utils/sqlserver_connection_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLServerConnectionDiagnostics.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `SQLServerConnectionDiagnostics.diagnose_connection_error` | 仅所在文件内部使用 | 负责 diagnose connection error 相关逻辑 |
| `SQLServerConnectionDiagnostics._check_network_connectivity` | 仅所在文件内部使用 | 负责 check network connectivity 相关逻辑 |
| `SQLServerConnectionDiagnostics._check_port_accessibility` | 仅所在文件内部使用 | 负责 check port accessibility 相关逻辑 |
| `SQLServerConnectionDiagnostics.get_connection_string_suggestions` | 仅所在文件内部使用 | 负责 get connection string suggestions 相关逻辑 |
| `SQLServerConnectionDiagnostics.analyze_error_patterns` | 仅所在文件内部使用 | 负责 analyze error patterns 相关逻辑 |

## `app/utils/structlog_config.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `SQLAlchemyLogHandler.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `SQLAlchemyLogHandler.__call__` | 仅所在文件内部使用 | 负责 call 相关逻辑 |
| `SQLAlchemyLogHandler._build_log_entry` | 仅所在文件内部使用 | 负责 build log entry 相关逻辑 |
| `SQLAlchemyLogHandler._build_context` | 仅所在文件内部使用 | 负责 build context 相关逻辑 |
| `SQLAlchemyLogHandler._process_logs` | 仅所在文件内部使用 | 负责 process logs 相关逻辑 |
| `SQLAlchemyLogHandler._flush_logs` | 仅所在文件内部使用 | 负责 flush logs 相关逻辑 |
| `SQLAlchemyLogHandler.shutdown` | 仅所在文件内部使用 | 负责 shutdown 相关逻辑 |
| `StructlogConfig.__init__` | 仅所在文件内部使用 | 负责 init 相关逻辑 |
| `StructlogConfig.configure` | 仅所在文件内部使用 | 负责 configure 相关逻辑 |
| `StructlogConfig._filter_log_level` | 仅所在文件内部使用 | 负责 filter log level 相关逻辑 |
| `StructlogConfig._add_request_context` | 仅所在文件内部使用 | 负责 add request context 相关逻辑 |
| `StructlogConfig._add_user_context` | 仅所在文件内部使用 | 负责 add user context 相关逻辑 |
| `StructlogConfig._add_global_context` | 仅所在文件内部使用 | 负责 add global context 相关逻辑 |
| `StructlogConfig._get_console_renderer` | 仅所在文件内部使用 | 负责 get console renderer 相关逻辑 |
| `StructlogConfig._get_handler` | 仅所在文件内部使用 | 负责 get handler 相关逻辑 |
| `StructlogConfig.shutdown` | 仅所在文件内部使用 | 负责 shutdown 相关逻辑 |
| `get_logger` | 仅所在文件内部使用 | 负责 get logger 相关逻辑 |
| `configure_structlog` | 仅所在文件内部使用 | 负责 configure structlog 相关逻辑 |
| `should_log_debug` | 仅所在文件内部使用 | 负责 should log debug 相关逻辑 |
| `log_info` | 仅所在文件内部使用 | 负责 log info 相关逻辑 |
| `log_warning` | 仅所在文件内部使用 | 负责 log warning 相关逻辑 |
| `log_error` | 仅所在文件内部使用 | 负责 log error 相关逻辑 |
| `log_critical` | 仅所在文件内部使用 | 负责 log critical 相关逻辑 |
| `log_debug` | 仅所在文件内部使用 | 负责 log debug 相关逻辑 |
| `get_system_logger` | 仅所在文件内部使用 | 负责 get system logger 相关逻辑 |
| `get_api_logger` | 仅所在文件内部使用 | 负责 get api logger 相关逻辑 |
| `get_auth_logger` | 仅所在文件内部使用 | 负责 get auth logger 相关逻辑 |
| `get_db_logger` | 仅所在文件内部使用 | 负责 get db logger 相关逻辑 |
| `get_sync_logger` | 仅所在文件内部使用 | 负责 get sync logger 相关逻辑 |
| `get_task_logger` | 仅所在文件内部使用 | 负责 get task logger 相关逻辑 |
| `ErrorContext.__post_init__` | 仅所在文件内部使用 | 负责 post init 相关逻辑 |
| `enhanced_error_handler` | 仅所在文件内部使用 | 负责 enhanced error handler 相关逻辑 |
| `_derive_error_metadata` | 仅所在文件内部使用 | 负责 derive error metadata 相关逻辑 |
| `_build_public_context` | 仅所在文件内部使用 | 负责 build public context 相关逻辑 |
| `_log_enhanced_error` | 仅所在文件内部使用 | 负责 log enhanced error 相关逻辑 |
| `_get_error_suggestions` | 仅所在文件内部使用 | 负责 get error suggestions 相关逻辑 |
| `error_handler` | 仅所在文件内部使用 | 负责 error handler 相关逻辑 |

## `app/utils/time_utils.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `TimeUtils.now` | 仅所在文件内部使用 | 负责 now 相关逻辑 |
| `TimeUtils.now_china` | 仅所在文件内部使用 | 负责 now china 相关逻辑 |
| `TimeUtils.to_china` | 仅所在文件内部使用 | 负责 to china 相关逻辑 |
| `TimeUtils.to_utc` | 仅所在文件内部使用 | 负责 to utc 相关逻辑 |
| `TimeUtils.format_china_time` | 仅所在文件内部使用 | 负责 format china time 相关逻辑 |
| `TimeUtils.format_utc_time` | 仅所在文件内部使用 | 负责 format utc time 相关逻辑 |
| `TimeUtils.get_relative_time` | 仅所在文件内部使用 | 负责 get relative time 相关逻辑 |
| `TimeUtils.is_today` | 仅所在文件内部使用 | 负责 is today 相关逻辑 |
| `TimeUtils.get_time_range` | 仅所在文件内部使用 | 负责 get time range 相关逻辑 |
| `TimeUtils.to_json_serializable` | 仅所在文件内部使用 | 负责 to json serializable 相关逻辑 |

## `app/utils/version_parser.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `DatabaseVersionParser.parse_version` | 仅所在文件内部使用 | 负责 parse version 相关逻辑 |
| `DatabaseVersionParser._extract_main_version` | 仅所在文件内部使用 | 负责 extract main version 相关逻辑 |
| `DatabaseVersionParser.format_version_display` | 仅所在文件内部使用 | 负责 format version display 相关逻辑 |
## `app/services/statistics/partition_statistics_service.py`

| 条目 | 引用情况 | 用途 |
| --- | --- | --- |
| `PartitionStatisticsService.get_partition_info` | `app/routes/partition.py`, `app/tasks/partition_management_tasks.py` | 汇总分区信息（含容量、数量等） |
| `PartitionStatisticsService.get_partition_statistics` | 同上 | 返回概要统计（总数/容量/记录数） |
