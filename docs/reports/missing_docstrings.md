# 缺失 Docstring 统计报告

- 生成时间：2025-11-25 15:10:44
- 扫描文件：297
- 模块缺失：0
- 类缺失：0
- 函数/方法缺失：100

> 说明：仅统计对外/公共定义（排除了私有、`__init__`、测试函数等），请按需补充 docstring。

## app/__init__.py
- 函数/方法文档不完整：
  - `configure_app` (行 134) 缺少 Returns
  - `configure_session_security` (行 267) 缺少 Returns
  - `initialize_extensions` (行 291) 缺少 Returns
  - `register_blueprints` (行 365) 缺少 Returns
  - `configure_logging` (行 454) 缺少 Returns
  - `configure_error_handlers` (行 483) 缺少 Args, Returns
  - `configure_template_filters` (行 489) 缺少 Returns

## app/models/account_change_log.py
- 函数/方法缺少 docstring：
  - `AccountChangeLog.__repr__` (行 65)

## app/models/account_classification.py
- 函数/方法缺少 docstring：
  - `AccountClassification.__repr__` (行 66)
  - `ClassificationRule.__repr__` (行 123)
  - `AccountClassificationAssignment.__repr__` (行 183)
- 函数/方法文档不完整：
  - `AccountClassification.color_value` (行 70) 缺少 Returns
  - `AccountClassification.color_name` (行 75) 缺少 Returns
  - `AccountClassification.css_class` (行 80) 缺少 Returns
  - `AccountClassification.to_dict` (行 84) 缺少 Returns
  - `ClassificationRule.to_dict` (行 126) 缺少 Returns
  - `ClassificationRule.get_rule_expression` (行 139) 缺少 Returns
  - `ClassificationRule.set_rule_expression` (行 146) 缺少 Args, Returns
  - `AccountClassificationAssignment.to_dict` (行 186) 缺少 Returns

## app/models/account_permission.py
- 函数/方法缺少 docstring：
  - `AccountPermission.__repr__` (行 87)
- 函数/方法文档不完整：
  - `AccountPermission.to_dict` (行 90) 缺少 Returns
  - `AccountPermission.get_permissions_by_db_type` (行 120) 缺少 Returns

## app/models/credential.py
- 函数/方法缺少 docstring：
  - `Credential.__repr__` (行 186)
- 函数/方法文档不完整：
  - `Credential.set_password` (行 79) 缺少 Returns

## app/models/database_size_aggregation.py
- 函数/方法缺少 docstring：
  - `DatabaseSizeAggregation.__repr__` (行 120)
- 函数/方法文档不完整：
  - `DatabaseSizeAggregation.to_dict` (行 123) 缺少 Returns

## app/models/database_size_stat.py
- 函数/方法缺少 docstring：
  - `DatabaseSizeStat.__repr__` (行 89)
- 函数/方法文档不完整：
  - `DatabaseSizeStat.to_dict` (行 92) 缺少 Returns

## app/models/database_type_config.py
- 函数/方法缺少 docstring：
  - `DatabaseTypeConfig.__repr__` (行 62)
- 函数/方法文档不完整：
  - `DatabaseTypeConfig.features_list` (行 66) 缺少 Returns
  - `DatabaseTypeConfig.features_list` (行 76) 缺少 Args, Returns
  - `DatabaseTypeConfig.to_dict` (行 80) 缺少 Returns
  - `DatabaseTypeConfig.get_active_types` (行 102) 缺少 Returns
  - `DatabaseTypeConfig.get_by_name` (行 107) 缺少 Args, Returns

## app/models/instance.py
- 函数/方法缺少 docstring：
  - `Instance.__repr__` (行 180)

## app/models/instance_account.py
- 函数/方法缺少 docstring：
  - `InstanceAccount.__repr__` (行 56)

## app/models/instance_database.py
- 函数/方法缺少 docstring：
  - `InstanceDatabase.__repr__` (行 55)

## app/models/instance_size_aggregation.py
- 函数/方法缺少 docstring：
  - `InstanceSizeAggregation.__repr__` (行 114)
- 函数/方法文档不完整：
  - `InstanceSizeAggregation.to_dict` (行 117) 缺少 Returns

## app/models/instance_size_stat.py
- 函数/方法缺少 docstring：
  - `InstanceSizeStat.__repr__` (行 47)

## app/models/permission_config.py
- 函数/方法缺少 docstring：
  - `PermissionConfig.__repr__` (行 53)

## app/models/sync_instance_record.py
- 函数/方法缺少 docstring：
  - `SyncInstanceRecord.__repr__` (行 195)
- 函数/方法文档不完整：
  - `SyncInstanceRecord.start_sync` (行 119) 缺少 Returns
  - `SyncInstanceRecord.complete_sync` (行 127) 缺少 Returns
  - `SyncInstanceRecord.fail_sync` (行 154) 缺少 Returns

## app/models/sync_session.py
- 函数/方法缺少 docstring：
  - `SyncSession.__repr__` (行 146)
- 函数/方法文档不完整：
  - `SyncSession.to_dict` (行 85) 缺少 Returns
  - `SyncSession.update_statistics` (行 103) 缺少 Returns
  - `SyncSession.get_progress_percentage` (行 122) 缺少 Returns
  - `SyncSession.get_sessions_by_type` (行 130) 缺少 Args, Returns
  - `SyncSession.get_sessions_by_category` (行 137) 缺少 Args, Returns

## app/models/tag.py
- 函数/方法缺少 docstring：
  - `Tag.__repr__` (行 175)

## app/models/unified_log.py
- 函数/方法缺少 docstring：
  - `UnifiedLog.__repr__` (行 67)
- 函数/方法文档不完整：
  - `UnifiedLog.to_dict` (行 70) 缺少 Returns
  - `UnifiedLog.create_log_entry` (行 88) 缺少 Args, Returns
  - `UnifiedLog.get_log_statistics` (行 117) 缺少 Args, Returns

## app/models/user.py
- 函数/方法缺少 docstring：
  - `User.__repr__` (行 117)
- 函数/方法文档不完整：
  - `User.set_password` (行 56) 缺少 Returns

## app/routes/account_classification.py
- 函数/方法文档不完整：
  - `get_color_options` (行 65) 缺少 Returns
  - `get_classification` (行 161) 缺少 Args, Returns
  - `update_classification` (行 186) 缺少 Args, Returns
  - `list_rules` (行 299) 缺少 Returns
  - `get_rule_stats` (行 342) 缺少 Returns
  - `get_rule` (行 404) 缺少 Args, Returns
  - `update_rule` (行 432) 缺少 Args, Returns
  - `delete_rule` (行 446) 缺少 Args, Returns
  - `get_assignments` (行 502) 缺少 Returns
  - `remove_assignment` (行 537) 缺少 Args, Returns
  - `get_permissions` (行 561) 缺少 Args, Returns

## app/routes/credentials.py
- 函数/方法缺少 docstring：
  - `_normalize_db_error` (行 54)
  - `_handle_db_exception` (行 64)
  - `_save_via_service` (行 89)
- 函数/方法文档不完整：
  - `edit_api` (行 269) 缺少 Args, Returns
  - `detail` (行 451) 缺少 Args, Returns
  - `api_detail` (行 460) 缺少 Args, Returns

## app/routes/dashboard.py
- 函数/方法文档不完整：
  - `api_charts` (行 122) 缺少 Returns
  - `api_activities` (行 149) 缺少 Returns
  - `api_status` (行 159) 缺少 Returns
  - `get_chart_data` (行 258) 缺少 Args, Returns
  - `get_task_status_distribution` (行 308) 缺少 Returns
  - `get_sync_trend_data` (行 332) 缺少 Returns

## app/routes/instance.py
- 函数/方法文档不完整：
  - `batch_delete` (行 257) 缺少 Returns
  - `batch_create` (行 277) 缺少 Returns
  - `_process_csv_file` (行 292) 缺少 Args, Returns
  - `_create_instances` (行 321) 缺少 Args, Returns
  - `list_instances_api` (行 334) 缺少 Returns
  - `api_detail` (行 517) 缺少 Args, Returns
  - `api_get_accounts` (行 529) 缺少 Args, Returns

## app/routes/instance_detail.py
- 函数/方法缺少 docstring：
  - `_build_capacity_query` (行 453)
  - `_normalize_active_flag` (行 486)
  - `_serialize_capacity_entry` (行 492)
  - `_fetch_latest_database_sizes` (行 512)
  - `_fetch_historical_database_sizes` (行 592)
- 函数/方法文档不完整：
  - `get_account_change_history` (行 155) 缺少 Args, Returns

## app/routes/instance_statistics.py
- 函数/方法文档不完整：
  - `statistics` (行 22) 缺少 Returns
  - `api_statistics` (行 35) 缺少 Returns

## app/routes/logs.py
- 函数/方法缺少 docstring：
  - `_safe_int` (行 55)
  - `_parse_iso_datetime` (行 67)
- 函数/方法文档不完整：
  - `list_logs` (行 208) 缺少 Returns
  - `get_log_statistics` (行 309) 缺少 Returns
  - `get_log_modules_api` (行 333) 缺少 Returns
  - `get_log_stats` (行 352) 缺少 Returns
  - `get_log_detail` (行 439) 缺少 Args, Returns

## app/routes/main.py
- 函数/方法文档不完整：
  - `about` (行 39) 缺少 Returns
  - `favicon` (行 45) 缺少 Returns
  - `apple_touch_icon` (行 53) 缺少 Returns
  - `chrome_devtools` (行 61) 缺少 Returns

## app/routes/partition.py
- 函数/方法缺少 docstring：
  - `_build_partition_status` (行 87)
- 函数/方法文档不完整：
  - `get_core_aggregation_metrics` (行 358) 缺少 Returns

## app/routes/scheduler.py
- 函数/方法文档不完整：
  - `get_job` (行 243) 缺少 Args, Returns
  - `pause_job` (行 281) 缺少 Args, Returns
  - `resume_job` (行 297) 缺少 Args, Returns
  - `run_job` (行 313) 缺少 Args, Returns

## app/routes/tags.py
- 函数/方法文档不完整：
  - `edit_api` (行 90) 缺少 Args, Returns
  - `api_tags` (行 270) 缺少 Returns
  - `api_categories` (行 291) 缺少 Returns
  - `api_tag_detail` (行 300) 缺少 Args, Returns
  - `api_tag_detail_by_id` (行 318) 缺少 Args, Returns

## app/routes/tags_batch.py
- 函数/方法文档不完整：
  - `api_instances` (行 391) 缺少 Returns
  - `api_all_tags` (行 410) 缺少 Returns

## app/routes/users.py
- 函数/方法文档不完整：
  - `api_update_user` (行 215) 缺少 Args, Returns
  - `api_get_stats` (行 325) 缺少 Returns

## app/scheduler.py
- 函数/方法缺少 docstring：
  - `_release_scheduler_lock` (行 183)
- 函数/方法文档不完整：
  - `TaskScheduler._setup_scheduler` (行 37) 缺少 Returns
  - `TaskScheduler._job_executed` (行 73) 缺少 Args, Returns
  - `TaskScheduler._job_error` (行 77) 缺少 Args, Returns
  - `TaskScheduler.start` (行 82) 缺少 Returns
  - `TaskScheduler.stop` (行 90) 缺少 Returns
  - `TaskScheduler.add_job` (行 96) 缺少 Args, Returns
  - `TaskScheduler.remove_job` (行 100) 缺少 Args, Returns
  - `TaskScheduler.get_jobs` (行 109) 缺少 Returns
  - `TaskScheduler.get_job` (行 113) 缺少 Args, Returns
  - `TaskScheduler.pause_job` (行 117) 缺少 Args, Returns
  - `TaskScheduler.resume_job` (行 122) 缺少 Args, Returns
  - `get_scheduler` (行 133) 缺少 Returns
  - `_acquire_scheduler_lock` (行 138) 缺少 Returns
  - `_should_start_scheduler` (行 203) 缺少 Returns
  - `init_scheduler` (行 225) 缺少 Args, Returns
  - `_load_existing_jobs` (行 270) 缺少 Returns
  - `_add_default_jobs` (行 309) 缺少 Returns
  - `_reload_all_jobs` (行 314) 缺少 Returns
  - `_load_tasks_from_config` (行 319) 缺少 Args, Returns

## app/services/account_classification/auto_classify_service.py
- 函数/方法缺少 docstring：
  - `AutoClassifyService._run_engine` (行 150)
  - `AutoClassifyService._as_int` (行 169)
  - `AutoClassifyService._normalize_instance_id` (行 175)
  - `AutoClassifyService._coerce_bool` (行 185)
  - `AutoClassifyService._normalize_errors` (行 203)
- 函数/方法文档不完整：
  - `AutoClassifyResult.to_payload` (行 43) 缺少 Returns

## app/services/account_classification/cache.py
- 函数/方法文档不完整：
  - `ClassificationCache.get_rules` (行 18) 缺少 Returns
  - `ClassificationCache.set_rules` (行 32) 缺少 Args, Returns

## app/services/account_classification/classifiers/oracle_classifier.py
- 函数/方法缺少 docstring：
  - `OracleRuleClassifier._combine_results` (行 141)
- 函数/方法文档不完整：
  - `OracleRuleClassifier._normalize_tablespace_privileges` (行 149) 缺少 Args, Returns

## app/services/account_classification/classifiers/postgresql_classifier.py
- 函数/方法缺少 docstring：
  - `PostgreSQLRuleClassifier._extract_priv_names` (行 108)
  - `PostgreSQLRuleClassifier._combine_results` (行 125)

## app/services/account_classification/classifiers/sqlserver_classifier.py
- 函数/方法缺少 docstring：
  - `SQLServerRuleClassifier._combine_results` (行 118)

## app/services/account_classification/orchestrator.py
- 函数/方法缺少 docstring：
  - `AccountClassificationService._classify_single_db_type` (行 272)
  - `AccountClassificationService._find_accounts_matching_rule` (行 317)
  - `AccountClassificationService._evaluate_rule` (行 333)
  - `AccountClassificationService._log_performance_stats` (行 343)

## app/services/account_sync/account_sync_filters.py
- 函数/方法文档不完整：
  - `DatabaseFilterManager._load_filter_rules` (行 29) 缺少 Returns

## app/services/account_sync/account_sync_service.py
- 函数/方法文档不完整：
  - `AccountSyncService._emit_completion_log` (行 368) 缺少 Returns

## app/services/account_sync/adapters/base_adapter.py
- 函数/方法文档不完整：
  - `BaseAccountAdapter.fetch_remote_accounts` (行 14) 缺少 Args, Returns
  - `BaseAccountAdapter.enrich_permissions` (行 31) 缺少 Args, Returns
  - `BaseAccountAdapter._fetch_raw_accounts` (行 49) 缺少 Args, Returns
  - `BaseAccountAdapter._normalize_account` (行 53) 缺少 Args, Returns

## app/services/account_sync/adapters/mysql_adapter.py
- 函数/方法缺少 docstring：
  - `MySQLAccountAdapter._expand_all_privileges` (行 407)
- 函数/方法文档不完整：
  - `MySQLAccountAdapter._parse_grant_statement` (行 334) 缺少 Returns

## app/services/account_sync/adapters/oracle_adapter.py
- 函数/方法缺少 docstring：
  - `OracleAccountAdapter._fetch_users` (行 117)
  - `OracleAccountAdapter._get_user_permissions` (行 141)
  - `OracleAccountAdapter._get_roles` (行 207)
  - `OracleAccountAdapter._get_system_privileges` (行 212)

## app/services/account_sync/adapters/postgresql_adapter.py
- 函数/方法缺少 docstring：
  - `PostgreSQLAccountAdapter._build_filter_conditions` (行 167)
  - `PostgreSQLAccountAdapter._get_role_permissions` (行 177)
  - `PostgreSQLAccountAdapter._get_role_attributes` (行 320)
  - `PostgreSQLAccountAdapter._get_predefined_roles` (行 339)
  - `PostgreSQLAccountAdapter._get_database_privileges` (行 349)
  - `PostgreSQLAccountAdapter._get_tablespace_privileges` (行 377)

## app/services/account_sync/adapters/sqlserver_adapter.py
- 函数/方法缺少 docstring：
  - `SQLServerAccountAdapter._fetch_logins` (行 204)
  - `SQLServerAccountAdapter._compile_like_patterns` (行 241)
  - `SQLServerAccountAdapter._get_login_permissions` (行 260)
  - `SQLServerAccountAdapter._deduplicate_preserve_order` (行 294)
  - `SQLServerAccountAdapter._copy_database_permissions` (行 307)
  - `SQLServerAccountAdapter._get_server_roles_bulk` (行 345)
  - `SQLServerAccountAdapter._get_server_permissions_bulk` (行 368)
  - `SQLServerAccountAdapter._normalize_sid` (行 633)
  - `SQLServerAccountAdapter._sid_to_hex_literal` (行 645)
  - `SQLServerAccountAdapter._quote_identifier` (行 651)

## app/services/account_sync/coordinator.py
- 函数/方法缺少 docstring：
  - `AccountSyncCoordinator.__enter__` (行 54)
  - `AccountSyncCoordinator.__exit__` (行 60)
- 函数/方法文档不完整：
  - `AccountSyncCoordinator._ensure_connection` (行 166) 缺少 Returns

## app/services/account_sync/permission_manager.py
- 函数/方法缺少 docstring：
  - `AccountPermissionManager._apply_permissions` (行 276)
  - `AccountPermissionManager._calculate_diff` (行 294)
  - `AccountPermissionManager._log_change` (行 351)
  - `AccountPermissionManager._build_initial_diff_payload` (行 383)
  - `AccountPermissionManager._build_privilege_diff_entries` (行 415)
  - `AccountPermissionManager._build_other_diff_entry` (行 509)
  - `AccountPermissionManager._build_other_description` (行 528)
  - `AccountPermissionManager._build_change_summary` (行 539)
  - `AccountPermissionManager._is_mapping` (行 580)
  - `AccountPermissionManager._normalize_mapping` (行 584)
  - `AccountPermissionManager._normalize_sequence` (行 593)
  - `AccountPermissionManager._repr_value` (行 601)
  - `AccountPermissionManager._count_permissions_by_action` (行 616)

## app/services/aggregation/aggregation_service.py
- 函数/方法缺少 docstring：
  - `AggregationService._get_instance_or_raise` (行 72)
  - `AggregationService._period_range` (行 115)
  - `AggregationService._aggregate_database_for_instance` (行 122)
  - `AggregationService._aggregate_instance_for_instance` (行 142)
  - `AggregationService._inactive_instance_summary` (行 159)
  - `AggregationService._aggregate_period` (行 175)
  - `AggregationService._normalize_periods` (行 187)
- 函数/方法文档不完整：
  - `AggregationService._ensure_partition_for_date` (行 81) 缺少 Args, Returns
  - `AggregationService._commit_with_partition_retry` (行 85) 缺少 Args, Returns
  - `AggregationService.calculate_daily_aggregations` (行 320) 缺少 Returns
  - `AggregationService.aggregate_current_period` (行 329) 缺少 Args, Returns
  - `AggregationService.calculate_weekly_aggregations` (行 430) 缺少 Returns
  - `AggregationService.calculate_monthly_aggregations` (行 439) 缺少 Returns
  - `AggregationService.calculate_quarterly_aggregations` (行 448) 缺少 Returns
  - `AggregationService.calculate_daily_database_aggregations_for_instance` (行 457) 缺少 Args, Returns
  - `AggregationService.calculate_weekly_database_aggregations_for_instance` (行 465) 缺少 Args, Returns
  - `AggregationService.calculate_monthly_database_aggregations_for_instance` (行 473) 缺少 Args, Returns
  - `AggregationService.calculate_quarterly_database_aggregations_for_instance` (行 481) 缺少 Args, Returns
  - `AggregationService.calculate_daily_instance_aggregations` (行 489) 缺少 Returns
  - `AggregationService.calculate_weekly_instance_aggregations` (行 498) 缺少 Returns
  - `AggregationService.calculate_monthly_instance_aggregations` (行 507) 缺少 Returns
  - `AggregationService.calculate_quarterly_instance_aggregations` (行 516) 缺少 Returns
  - `AggregationService.calculate_instance_aggregations` (行 525) 缺少 Args, Returns
  - `AggregationService.calculate_daily_aggregations_for_instance` (行 608) 缺少 Args, Returns
  - `AggregationService.calculate_weekly_aggregations_for_instance` (行 616) 缺少 Args, Returns
  - `AggregationService.calculate_monthly_aggregations_for_instance` (行 624) 缺少 Args, Returns
  - `AggregationService.calculate_quarterly_aggregations_for_instance` (行 632) 缺少 Args, Returns
  - `AggregationService.calculate_period_aggregations` (行 640) 缺少 Args, Returns
  - `AggregationService.get_aggregations` (行 663) 缺少 Args, Returns
  - `AggregationService.get_instance_aggregations` (行 680) 缺少 Args, Returns

## app/services/aggregation/database_aggregation_runner.py
- 函数/方法缺少 docstring：
  - `DatabaseAggregationRunner._invoke_callback` (行 58)
  - `DatabaseAggregationRunner._query_database_stats` (行 316)
  - `DatabaseAggregationRunner._group_by_database` (行 323)
  - `DatabaseAggregationRunner._persist_database_aggregation` (行 329)
  - `DatabaseAggregationRunner._apply_change_statistics` (行 451)

## app/services/aggregation/instance_aggregation_runner.py
- 函数/方法缺少 docstring：
  - `InstanceAggregationRunner._invoke_callback` (行 58)
  - `InstanceAggregationRunner._query_instance_stats` (行 280)
  - `InstanceAggregationRunner._persist_instance_aggregation` (行 288)
  - `InstanceAggregationRunner._apply_change_statistics` (行 405)

## app/services/connection_adapters/adapters/base.py
- 函数/方法文档不完整：
  - `DatabaseConnection.disconnect` (行 66) 缺少 Returns

## app/services/connection_adapters/adapters/mysql_adapter.py
- 函数/方法文档不完整：
  - `MySQLConnection.disconnect` (行 50) 缺少 Returns

## app/services/connection_adapters/adapters/oracle_adapter.py
- 函数/方法文档不完整：
  - `OracleConnection.connect` (行 13) 缺少 Returns
  - `OracleConnection.disconnect` (行 85) 缺少 Returns
  - `OracleConnection.execute_query` (行 121) 缺少 Args, Returns
  - `OracleConnection.get_version` (行 134) 缺少 Returns

## app/services/connection_adapters/adapters/postgresql_adapter.py
- 函数/方法文档不完整：
  - `PostgreSQLConnection.disconnect` (行 46) 缺少 Returns
  - `PostgreSQLConnection.execute_query` (行 82) 缺少 Args, Returns
  - `PostgreSQLConnection.get_version` (行 95) 缺少 Returns

## app/services/connection_adapters/adapters/sqlserver_adapter.py
- 函数/方法文档不完整：
  - `SQLServerConnection.connect` (行 19) 缺少 Returns
  - `SQLServerConnection._try_pymssql_connection` (行 43) 缺少 Args, Returns
  - `SQLServerConnection.disconnect` (行 89) 缺少 Returns
  - `SQLServerConnection.execute_query` (行 125) 缺少 Args, Returns
  - `SQLServerConnection.get_version` (行 138) 缺少 Returns

## app/services/database_sync/adapters/mysql_adapter.py
- 函数/方法缺少 docstring：
  - `MySQLCapacityAdapter._build_stats_from_tablespaces` (行 229)
- 函数/方法文档不完整：
  - `MySQLCapacityAdapter.fetch_capacity` (行 71) 缺少 Args, Returns
  - `MySQLCapacityAdapter._assert_permission` (行 118) 缺少 Returns

## app/services/database_sync/coordinator.py
- 函数/方法文档不完整：
  - `CapacitySyncCoordinator.inventory_manager` (行 45) 缺少 Returns
  - `CapacitySyncCoordinator.persistence` (行 51) 缺少 Returns
  - `CapacitySyncCoordinator.disconnect` (行 103) 缺少 Returns
  - `CapacitySyncCoordinator._ensure_connection` (行 281) 缺少 Returns

## app/services/database_sync/database_filters.py
- 函数/方法缺少 docstring：
  - `DatabaseSyncFilterManager._compile_pattern` (行 84)
- 函数/方法文档不完整：
  - `DatabaseSyncFilterManager.config_path` (行 34) 缺少 Returns
  - `DatabaseSyncFilterManager.reload` (行 39) 缺少 Returns
  - `DatabaseSyncFilterManager.should_exclude_database` (行 90) 缺少 Args, Returns
  - `DatabaseSyncFilterManager.filter_database_names` (行 113) 缺少 Args, Returns
  - `DatabaseSyncFilterManager.filter_capacity_payload` (行 125) 缺少 Args, Returns

## app/services/database_sync/database_sync_service.py
- 函数/方法文档不完整：
  - `DatabaseSizeCollectorService.__exit__` (行 51) 缺少 Returns
  - `DatabaseSizeCollectorService.disconnect` (行 72) 缺少 Returns

## app/services/database_sync/persistence.py
- 函数/方法文档不完整：
  - `CapacityPersistence.save_database_stats` (行 26) 缺少 Args
  - `CapacityPersistence.save_instance_stats` (行 120) 缺少 Args
  - `CapacityPersistence.update_instance_total_size` (行 189) 缺少 Args, Returns

## app/services/form_service/change_password_form_service.py
- 函数/方法文档不完整：
  - `ChangePasswordFormService.assign` (行 77) 缺少 Returns
  - `ChangePasswordFormService.after_save` (行 86) 缺少 Returns

## app/services/form_service/classification_form_service.py
- 函数/方法文档不完整：
  - `ClassificationFormService.assign` (行 79) 缺少 Returns
  - `ClassificationFormService.after_save` (行 93) 缺少 Returns

## app/services/form_service/classification_rule_form_service.py
- 函数/方法文档不完整：
  - `ClassificationRuleFormService.assign` (行 88) 缺少 Returns
  - `ClassificationRuleFormService.after_save` (行 102) 缺少 Returns

## app/services/form_service/credentials_form_service.py
- 函数/方法文档不完整：
  - `CredentialFormService.assign` (行 99) 缺少 Returns
  - `CredentialFormService.after_save` (行 116) 缺少 Returns

## app/services/form_service/instances_form_service.py
- 函数/方法文档不完整：
  - `InstanceFormService.assign` (行 77) 缺少 Returns
  - `InstanceFormService.after_save` (行 94) 缺少 Returns
  - `InstanceFormService._sync_tags` (行 200) 缺少 Returns

## app/services/form_service/resource_form_service.py
- 函数/方法文档不完整：
  - `BaseResourceService.assign` (行 128) 缺少 Returns
  - `BaseResourceService.after_save` (行 140) 缺少 Returns

## app/services/form_service/scheduler_job_form_service.py
- 函数/方法缺少 docstring：
  - `SchedulerJobFormService._build_trigger` (行 147)
- 函数/方法文档不完整：
  - `SchedulerJobFormService.assign` (行 104) 缺少 Args, Returns
  - `SchedulerJobFormService.after_save` (行 111) 缺少 Args, Returns
  - `SchedulerJobFormService.upsert` (行 125) 缺少 Args, Returns

## app/services/form_service/tags_form_service.py
- 函数/方法文档不完整：
  - `TagFormService.assign` (行 82) 缺少 Returns
  - `TagFormService.after_save` (行 97) 缺少 Returns

## app/services/form_service/users_form_service.py
- 函数/方法文档不完整：
  - `UserFormService.assign` (行 87) 缺少 Returns
  - `UserFormService.after_save` (行 102) 缺少 Returns

## app/services/partition_management_service.py
- 函数/方法文档不完整：
  - `PartitionAction.to_dict` (行 34) 缺少 Returns

## app/services/sync_session_service.py
- 函数/方法文档不完整：
  - `SyncSessionService._update_session_statistics` (行 309) 缺少 Returns

## app/static/js/common/form-validator.js
- 函数/方法文档不完整：
  - `ensureLibrary` (行 12) 缺少 @param, @returns
  - `toArray` (行 23) 缺少 @param, @returns
  - `createValidator` (行 39) 缺少 @param, @returns

## app/static/js/common/grid-wrapper.js
- 函数/方法文档不完整：
  - `GridWrapper` (行 19) 缺少 @returns

## app/static/js/common/number-format.js
- 函数/方法文档不完整：
  - `toFiniteNumber` (行 20) 缺少 @param, @returns
  - `buildDecimalPattern` (行 28) 缺少 @param, @returns
  - `formatWithPattern` (行 42) 缺少 @param, @returns
  - `formatInteger` (行 53) 缺少 @param, @returns
  - `formatDecimal` (行 65) 缺少 @param, @returns
  - `formatPlain` (行 78) 缺少 @param, @returns
  - `normalizeUnit` (行 85) 缺少 @param, @returns
  - `formatBytes` (行 96) 缺少 @param, @returns
  - `formatBytesFromMB` (行 118) 缺少 @param, @returns
  - `formatGigabytes` (行 130) 缺少 @param, @returns
  - `formatPercent` (行 146) 缺少 @param, @returns
  - `formatDurationSeconds` (行 165) 缺少 @param, @returns

## app/static/js/common/time-utils.js
- 函数/方法文档不完整：
  - `registerZhCnLocale` (行 33) 缺少 @param, @returns
  - `setupDayjs` (行 76) 缺少 @param, @returns
  - `applyTimezone` (行 114) 缺少 @param, @returns
  - `tryCustomFormats` (行 127) 缺少 @param, @returns
  - `toDayjs` (行 143) 缺少 @param, @returns
  - `formatWithPattern` (行 188) 缺少 @param, @returns
  - `formatChineseDateTimeString` (行 199) 缺少 @param, @returns
  - `diffInSeconds` (行 212) 缺少 @param, @returns
  - `isSameDay` (行 223) 缺少 @param, @returns

## app/static/js/common/toast.js
- 函数/方法文档不完整：
  - `normalizeType` (行 71) 缺少 @param, @returns
  - `resolvePosition` (行 79) 缺少 @param, @returns
  - `getContainer` (行 87) 缺少 @param, @returns
  - `createCloseButton` (行 108) 缺少 @param, @returns
  - `createIconElement` (行 117) 缺少 @param, @returns
  - `buildToastElement` (行 129) 缺少 @param, @returns
  - `trimStack` (行 184) 缺少 @param, @returns
  - `mountToastElement` (行 202) 缺少 @param, @returns
  - `showToast` (行 214) 缺少 @param, @returns

## app/static/js/core/dom.helpers.js
- 函数/方法文档不完整：
  - `toUmbrella` (行 14) 缺少 @param, @returns
  - `select` (行 39) 缺少 @param, @returns
  - `selectOne` (行 46) 缺少 @param, @returns
  - `from` (行 55) 缺少 @param, @returns
  - `ready` (行 62) 缺少 @param, @returns
  - `text` (行 76) 缺少 @param, @returns
  - `html` (行 87) 缺少 @param, @returns
  - `value` (行 98) 缺少 @param, @returns
  - `toggleDisabled` (行 118) 缺少 @param, @returns

## app/static/js/core/http-u.js
- 函数/方法文档不完整：
  - `serializeParams` (行 16) 缺少 @param, @returns
  - `ensureAjax` (行 40) 缺少 @param, @returns
  - `appendParams` (行 134) 缺少 @param, @returns
  - `parseJSON` (行 148) 缺少 @param, @returns
  - `parseResponseBody` (行 162) 缺少 @param, @returns
  - `resolveErrorMessage` (行 178) 缺少 @param, @returns
  - `buildError` (行 191) 缺少 @param, @returns
  - `request` (行 204) 缺少 @param, @returns
  - `createRequest` (行 248) 缺少 @param, @returns

## app/static/js/modules/services/capacity_stats_service.js
- 函数/方法文档不完整：
  - `append` (行 36) 缺少 @returns

## app/static/js/modules/services/scheduler_service.js
- 函数/方法文档不完整：
  - `assertJobId` (行 28) 缺少 @returns

## app/static/js/modules/stores/account_classification_store.js
- 函数/方法文档不完整：
  - `emit` (行 217) 缺少 @returns
  - `handleError` (行 233) 缺少 @returns

## app/static/js/modules/stores/credentials_store.js
- 函数/方法文档不完整：
  - `emit` (行 117) 缺少 @returns
  - `handleError` (行 127) 缺少 @returns

## app/static/js/modules/stores/instance_store.js
- 函数/方法文档不完整：
  - `normalizeIds` (行 102) 缺少 @param, @returns
  - `toNumericId` (行 118) 缺少 @param, @returns
  - `normalizeInstanceMeta` (行 129) 缺少 @param, @returns
  - `cloneInstancesMeta` (行 155) 缺少 @param, @returns
  - `cloneState` (行 164) 缺少 @param, @returns
  - `extractStats` (行 185) 缺少 @param, @returns
  - `ensureSuccess` (行 196) 缺少 @param, @returns
  - `emit` (行 285) 缺少 @returns
  - `handleError` (行 295) 缺少 @returns
  - `emitSelectionChanged` (行 309) 缺少 @returns
  - `pruneSelection` (行 358) 缺少 @returns
  - `emitLoading` (行 376) 缺少 @returns
  - `markOperation` (行 391) 缺少 @returns

## app/static/js/modules/stores/logs_store.js
- 函数/方法文档不完整：
  - `emit` (行 284) 缺少 @returns
  - `handleError` (行 293) 缺少 @returns
  - `applyListResponse` (行 303) 缺少 @returns

## app/static/js/modules/stores/partition_store.js
- 函数/方法文档不完整：
  - `emit` (行 278) 缺少 @returns
  - `emitLoading` (行 288) 缺少 @returns
  - `handleError` (行 303) 缺少 @returns

## app/static/js/modules/stores/scheduler_store.js
- 函数/方法文档不完整：
  - `cloneState` (行 143) 缺少 @param
  - `emit` (行 158) 缺少 @returns
  - `handleError` (行 168) 缺少 @returns
  - `setJobs` (行 182) 缺少 @returns

## app/static/js/modules/stores/sync_sessions_store.js
- 函数/方法文档不完整：
  - `emit` (行 204) 缺少 @returns
  - `scheduleAutoRefresh` (行 211) 缺少 @param, @returns
  - `applyListResponse` (行 235) 缺少 @returns
  - `handleRequestFailure` (行 254) 缺少 @returns
  - `debugLog` (行 266) 缺少 @returns

## app/static/js/modules/stores/tag_batch_store.js
- 函数/方法文档不完整：
  - `emit` (行 124) 缺少 @param, @returns
  - `handleError` (行 131) 缺少 @param, @returns
  - `setInstances` (行 143) 缺少 @param, @returns
  - `setTags` (行 159) 缺少 @param, @returns
  - `emitSelection` (行 175) 缺少 @param, @returns
  - `setSelection` (行 187) 缺少 @param, @returns

## app/static/js/modules/stores/tag_list_store.js
- 函数/方法文档不完整：
  - `emit` (行 88) 缺少 @param, @returns
  - `emitSelection` (行 100) 缺少 @param, @returns

## app/static/js/modules/stores/tag_management_store.js
- 函数/方法文档不完整：
  - `emit` (行 171) 缺少 @param, @returns
  - `handleError` (行 178) 缺少 @param, @returns
  - `updateStats` (行 190) 缺少 @param, @returns
  - `updateFilteredTags` (行 203) 缺少 @param, @returns
  - `emitTagsUpdated` (行 233) 缺少 @param, @returns
  - `emitSelectionChanged` (行 246) 缺少 @param, @returns
  - `applySelection` (行 258) 缺少 @param, @returns
  - `compareFn` (行 278) 缺少 @param, @returns
  - `applyPendingSelection` (行 303) 缺少 @param, @returns

## app/static/js/modules/ui/filter-card.js
- 函数/方法文档不完整：
  - `createDebounced` (行 18) 缺少 @param, @returns
  - `serializeForm` (行 35) 缺少 @param, @returns
  - `requestFormSubmit` (行 57) 缺少 @param, @returns
  - `addListener` (行 71) 缺少 @param, @returns
  - `normalizeForm` (行 82) 缺少 @param, @returns
  - `emitEvent` (行 121) 缺少 @param, @returns
  - `handleSubmit` (行 142) 缺少 @param, @returns
  - `handleClear` (行 156) 缺少 @param, @returns
  - `handleChange` (行 171) 缺少 @param, @returns
  - `handler` (行 242) 缺少 @returns

## app/static/js/modules/ui/modal.js
- 函数/方法文档不完整：
  - `toElement` (行 13) 缺少 @param, @returns
  - `ensureBootstrap` (行 32) 缺少 @param, @returns
  - `createModal` (行 43) 缺少 @param, @returns
  - `setLoading` (行 68) 缺少 @param, @returns
  - `open` (行 86) 缺少 @param, @returns
  - `close` (行 94) 缺少 @param, @returns
  - `handleShown` (行 101) 缺少 @param, @returns
  - `handleHidden` (行 108) 缺少 @param, @returns
  - `handleConfirm` (行 117) 缺少 @param, @returns
  - `handleCancel` (行 125) 缺少 @param, @returns

## app/static/js/modules/views/accounts/account-classification/index.js
- 函数/方法文档不完整：
  - `debugLog` (行 24) 缺少 @param, @returns
  - `fallbackLogger` (行 82) 缺少 @returns
  - `startPageInitialization` (行 135) 缺少 @param, @returns
  - `extractClassifications` (行 195) 缺少 @param, @returns
  - `extractRules` (行 203) 缺少 @param, @returns
  - `collectRuleIds` (行 247) 缺少 @param, @returns
  - `renderClassifications` (行 264) 缺少 @param, @returns
  - `getClassificationIcon` (行 364) 缺少 @param, @returns
  - `renderRules` (行 381) 缺少 @param, @returns
  - `renderRuleRow` (行 446) 缺少 @param, @returns
  - `getClassificationClass` (行 505) 缺少 @param, @returns
  - `setupGlobalSearchListener` (行 568) 缺少 @param, @returns
  - `handleRequestError` (行 587) 缺少 @returns

## app/static/js/modules/views/accounts/account-classification/modals/classification-modals.js
- 函数/方法文档不完整：
  - `init` (行 55) 缺少 @param
  - `triggerCreate` (行 119) 缺少 @param
  - `triggerUpdate` (行 139) 缺少 @param
  - `setupColorPreviewListeners` (行 304) 缺少 @param
  - `initFormValidators` (行 373) 缺少 @param
  - `resetCreateForm` (行 444) 缺少 @param
  - `resetEditForm` (行 458) 缺少 @param

## app/static/js/modules/views/accounts/account-classification/modals/rule-modals.js
- 函数/方法文档不完整：
  - `createController` (行 7) 缺少 @param, @returns
  - `init` (行 44) 缺少 @param, @returns
  - `syncClassificationOptions` (行 73) 缺少 @param, @returns
  - `populateClassificationSelect` (行 89) 缺少 @param, @returns
  - `openCreate` (行 106) 缺少 @param, @returns
  - `triggerCreate` (行 216) 缺少 @param, @returns
  - `resetCreateForm` (行 344) 缺少 @param, @returns
  - `resetEditForm` (行 355) 缺少 @param, @returns
  - `resetViewModal` (行 370) 缺少 @param, @returns
  - `initFormValidators` (行 402) 缺少 @param, @returns
  - `loadPermissions` (行 429) 缺少 @param, @returns
  - `debug` (行 439) 缺少 @returns

## app/static/js/modules/views/accounts/list.js
- 函数/方法文档不完整：
  - `mountAccountsListPage` (行 9) 缺少 @param
  - `initializeInstanceService` (行 60) 缺少 @param
  - `initializeInstanceStore` (行 78) 缺少 @param
  - `initializeGrid` (行 103) 缺少 @param
  - `renderTags` (行 260) 缺少 @param, @returns
  - `renderClassifications` (行 280) 缺少 @param, @returns
  - `renderDbTypeBadge` (行 300) 缺少 @param, @returns
  - `renderStatusBadge` (行 319) 缺少 @param, @returns
  - `renderActions` (行 331) 缺少 @param, @returns
  - `initializeFilterCard` (行 348) 缺少 @param, @returns
  - `handleFilterChange` (行 393) 缺少 @returns
  - `resolveFilters` (行 406) 缺少 @param, @returns
  - `collectFormValues` (行 424) 缺少 @param, @returns
  - `normalizeFilters` (行 453) 缺少 @param, @returns
  - `sanitizeText` (行 467) 缺少 @param, @returns
  - `sanitizeFlag` (行 478) 缺少 @param, @returns
  - `normalizeArrayValue` (行 488) 缺少 @param, @returns
  - `bindDatabaseTypeButtons` (行 507) 缺少 @param, @returns
  - `switchDatabaseType` (行 521) 缺少 @param, @returns
  - `buildBaseUrl` (行 534) 缺少 @param, @returns
  - `buildSearchParams` (行 542) 缺少 @param, @returns
  - `syncUrl` (行 560) 缺少 @param, @returns
  - `initializeTagFilter` (行 574) 缺少 @param, @returns
  - `parseInitialTagValues` (行 609) 缺少 @param, @returns
  - `setDefaultTimeRange` (行 622) 缺少 @param, @returns
  - `updateTotalCount` (行 641) 缺少 @param, @returns
  - `exposeGlobalActions` (行 651) 缺少 @param, @returns
  - `exportAccountsCSV` (行 662) 缺少 @param, @returns
  - `syncAllAccounts` (行 675) 缺少 @param, @returns
  - `escapeHtml` (行 710) 缺少 @param, @returns

## app/static/js/modules/views/admin/partitions/charts/partitions-chart.js
- 函数/方法文档不完整：
  - `mountAggregationsChart` (行 21) 缺少 @param, @returns
  - `buildChartQueryParams` (行 32) 缺少 @param, @returns
  - `initManager` (行 733) 缺少 @param, @returns

## app/static/js/modules/views/admin/partitions/index.js
- 函数/方法文档不完整：
  - `initializePartitionStore` (行 52) 缺少 @param
  - `bindPartitionStoreEvents` (行 93) 缺少 @param, @returns
  - `subscribeToPartitionStore` (行 107) 缺少 @param, @returns
  - `teardownPartitionStore` (行 115) 缺少 @param, @returns
  - `bindEvents` (行 130) 缺少 @param, @returns
  - `initializeModals` (行 142) 缺少 @param, @returns
  - `refreshPartitionData` (行 182) 缺少 @param, @returns
  - `updatePartitionStats` (行 194) 缺少 @param, @returns
  - `getStatusColor` (行 205) 缺少 @param, @returns
  - `handleInfoUpdated` (行 228) 缺少 @param, @returns
  - `handlePartitionLoading` (行 236) 缺少 @param, @returns
  - `handlePartitionError` (行 246) 缺少 @param, @returns
  - `handleCreateSuccess` (行 262) 缺少 @param, @returns
  - `handleCleanupSuccess` (行 270) 缺少 @param, @returns
  - `notifyStatsError` (行 278) 缺少 @param, @returns
  - `requestPartitionGridRefresh` (行 289) 缺少 @param, @returns
  - `resolvePartitionStatusLabel` (行 296) 缺少 @param, @returns

## app/static/js/modules/views/admin/partitions/modals/partitions-modals.js
- 函数/方法文档不完整：
  - `prepareCreatePartitionForm` (行 76) 缺少 @param
  - `updateMonthOptions` (行 98) 缺少 @param, @returns

## app/static/js/modules/views/admin/partitions/partition-list.js
- 函数/方法文档不完整：
  - `mount` (行 14) 缺少 @param
  - `initializeGrid` (行 36) 缺少 @param
  - `buildColumns` (行 80) 缺少 @param
  - `bindRefreshEvent` (行 193) 缺少 @param
  - `handler` (行 200) 缺少 @param, @returns
  - `refresh` (行 215) 缺少 @param

## app/static/js/modules/views/admin/scheduler/index.js
- 函数/方法文档不完整：
  - `ensureSchedulerService` (行 21) 缺少 @param, @returns
  - `ensureSchedulerStore` (行 36) 缺少 @param, @returns
  - `mountSchedulerPage` (行 60) 缺少 @param
  - `initializeSchedulerPage` (行 108) 缺少 @param, @returns
  - `initializeEventHandlers` (行 123) 缺少 @param, @returns
  - `updateCronPreview` (行 134) 缺少 @param, @returns
  - `initializeSchedulerValidators` (行 238) 缺少 @param, @returns
  - `loadJobs` (行 286) 缺少 @param, @returns
  - `displayJobs` (行 299) 缺少 @param, @returns
  - `createColumn` (行 327) 缺少 @param, @returns
  - `createJobCard` (行 390) 缺少 @param, @returns
  - `getStatusClass` (行 436) 缺少 @param, @returns
  - `getStatusText` (行 453) 缺少 @param, @returns
  - `formatTriggerInfo` (行 470) 缺少 @param, @returns
  - `getActionButtons` (行 503) 缺少 @param, @returns
  - `enableJob` (行 543) 缺少 @param, @returns
  - `disableJob` (行 566) 缺少 @param, @returns
  - `runJobNow` (行 589) 缺少 @param, @returns
  - `deleteJob` (行 612) 缺少 @param, @returns
  - `viewJobLogs` (行 645) 缺少 @param, @returns
  - `addJob` (行 660) 缺少 @param, @returns
  - `showLoadingState` (行 744) 缺少 @param, @returns
  - `hideLoadingState` (行 762) 缺少 @param, @returns
  - `formatTime` (行 780) 缺少 @param, @returns
  - `bindSchedulerStoreEvents` (行 788) 缺少 @param, @returns
  - `getSchedulerJob` (行 813) 缺少 @param, @returns
  - `normalizeElements` (行 839) 缺少 @param, @returns
  - `showElement` (行 849) 缺少 @param, @returns
  - `hideElement` (行 862) 缺少 @param, @returns
  - `clearContainer` (行 875) 缺少 @param, @returns
  - `hideAddJobModal` (行 886) 缺少 @param, @returns

## app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js
- 函数/方法文档不完整：
  - `init` (行 47) 缺少 @param
  - `populateCron` (行 145) 缺少 @param, @returns
  - `updateCronPreview` (行 182) 缺少 @param
  - `handleSubmit` (行 200) 缺少 @param
  - `toggleTriggerConfig` (行 291) 缺少 @param, @returns
  - `setFieldValue` (行 304) 缺少 @param, @returns
  - `getFieldValue` (行 314) 缺少 @param, @returns

## app/static/js/modules/views/auth/change_password.js
- 函数/方法文档不完整：
  - `initializeChangePasswordPage` (行 33) 缺少 @param, @returns
  - `initializePasswordToggles` (行 49) 缺少 @param, @returns
  - `togglePasswordVisibility` (行 72) 缺少 @param, @returns
  - `initializePasswordStrength` (行 88) 缺少 @param, @returns
  - `getPasswordStrength` (行 112) 缺少 @param, @returns
  - `updatePasswordStrength` (行 141) 缺少 @param, @returns
  - `updatePasswordRequirements` (行 184) 缺少 @param, @returns
  - `checkPasswordRequirements` (行 205) 缺少 @param, @returns
  - `initializeFormValidation` (行 219) 缺少 @param, @returns
  - `toggleSubmitLoading` (行 278) 缺少 @param, @returns

## app/static/js/modules/views/auth/list.js
- 函数/方法文档不完整：
  - `initializeUserModals` (行 63) 缺少 @param, @returns
  - `initializeGrid` (行 81) 缺少 @param, @returns
  - `bindCreateButton` (行 214) 缺少 @param, @returns
  - `initializeFilterCard` (行 227) 缺少 @param, @returns
  - `destroyFilterCard` (行 268) 缺少 @param, @returns
  - `applyUserFilters` (行 275) 缺少 @param, @returns
  - `resetUserFilters` (行 299) 缺少 @param, @returns
  - `resolveUserFilters` (行 310) 缺少 @param, @returns
  - `normalizeGridFilters` (行 331) 缺少 @param, @returns
  - `sanitizeFilterValue` (行 344) 缺少 @param, @returns
  - `sanitizePrimitiveValue` (行 354) 缺少 @param, @returns
  - `buildQueryParams` (行 371) 缺少 @param, @returns
  - `resolveFormElement` (行 386) 缺少 @param, @returns
  - `collectFormValues` (行 408) 缺少 @param, @returns
  - `escapeHtmlValue` (行 434) 缺少 @param, @returns
  - `openUserEditor` (行 449) 缺少 @param, @returns
  - `requestDeleteUser` (行 459) 缺少 @param, @returns
  - `showLoadingState` (行 493) 缺少 @param, @returns
  - `hideLoadingState` (行 506) 缺少 @param, @returns

## app/static/js/modules/views/auth/login.js
- 函数/方法文档不完整：
  - `initializePasswordToggle` (行 36) 缺少 @param, @returns
  - `togglePasswordVisibility` (行 53) 缺少 @param, @returns
  - `initializeFormValidation` (行 69) 缺少 @param, @returns
  - `initializePasswordStrengthWatcher` (行 96) 缺少 @param, @returns
  - `showLoadingState` (行 112) 缺少 @param, @returns
  - `hideLoadingState` (行 125) 缺少 @param, @returns
  - `checkPasswordStrength` (行 138) 缺少 @param, @returns
  - `resetStrengthBarClasses` (行 165) 缺少 @param, @returns
  - `updatePasswordStrength` (行 172) 缺少 @param, @returns

## app/static/js/modules/views/auth/modals/user-modals.js
- 函数/方法文档不完整：
  - `init` (行 51) 缺少 @param
  - `resetForm` (行 72) 缺少 @param
  - `openCreate` (行 89) 缺少 @param
  - `buildPayload` (行 154) 缺少 @param

## app/static/js/modules/views/capacity-stats/database_aggregations.js
- 函数/方法文档不完整：
  - `initManager` (行 62) 缺少 @param

## app/static/js/modules/views/capacity-stats/instance_aggregations.js
- 函数/方法文档不完整：
  - `initManager` (行 58) 缺少 @param

## app/static/js/modules/views/components/charts/filters.js
- 函数/方法文档不完整：
  - `readChartState` (行 92) 缺少 @param, @returns
  - `updateSelectOptions` (行 127) 缺少 @param, @returns
  - `syncSelectValue` (行 172) 缺少 @param, @returns
  - `setDisabled` (行 184) 缺少 @param, @returns

## app/static/js/modules/views/components/charts/manager.js
- 函数/方法文档不完整：
  - `formatDate` (行 81) 缺少 @param, @returns
  - `getCurrentPeriodRange` (行 88) 缺少 @param, @returns
  - `calculateDateRange` (行 129) 缺少 @param, @returns

## app/static/js/modules/views/components/charts/transformers.js
- 函数/方法文档不完整：
  - `normalizeValue` (行 73) 缺少 @param, @returns
  - `collectDateMatrix` (行 84) 缺少 @param, @returns
  - `buildDatasets` (行 119) 缺少 @param, @returns
  - `prepareTrendChartData` (行 229) 缺少 @param, @returns
  - `prepareChangeChartData` (行 262) 缺少 @param, @returns
  - `prepareChangePercentChartData` (行 301) 缺少 @param, @returns

## app/static/js/modules/views/components/permissions/permission-modal.js
- 函数/方法文档不完整：
  - `showPermissionsModal` (行 11) 缺少 @returns
  - `ensurePermissionModal` (行 45) 缺少 @param
  - `openPermissionModal` (行 63) 缺少 @param, @returns
  - `resetPermissionModal` (行 71) 缺少 @param, @returns
  - `updateModalContent` (行 96) 缺少 @param, @returns

## app/static/js/modules/views/components/permissions/permission-viewer.js
- 函数/方法文档不完整：
  - `resolveCsrfToken` (行 81) 缺少 @param

## app/static/js/modules/views/credentials/list.js
- 函数/方法文档不完整：
  - `initializeCredentialsListPage` (行 83) 缺少 @param
  - `initializeCredentialsGrid` (行 99) 缺少 @param
  - `bindModalTriggers` (行 263) 缺少 @param, @returns
  - `initializeDeleteConfirmation` (行 292) 缺少 @param, @returns
  - `handleDeleteConfirmation` (行 312) 缺少 @param, @returns
  - `deleteCredential` (行 336) 缺少 @param, @returns
  - `openCredentialEditor` (行 351) 缺少 @param, @returns
  - `showLoadingState` (行 361) 缺少 @param, @returns
  - `hideLoadingState` (行 374) 缺少 @param, @returns
  - `initializeCredentialFilterCard` (行 388) 缺少 @param, @returns
  - `destroyCredentialFilterCard` (行 447) 缺少 @param, @returns
  - `applyCredentialFilters` (行 454) 缺少 @param, @returns
  - `resolveCredentialFilters` (行 482) 缺少 @param, @returns
  - `normalizeGridFilters` (行 504) 缺少 @param, @returns
  - `sanitizeFilterValue` (行 527) 缺少 @param, @returns
  - `sanitizePrimitiveValue` (行 537) 缺少 @param, @returns
  - `buildCredentialQueryParams` (行 554) 缺少 @param, @returns
  - `resetCredentialFilters` (行 569) 缺少 @param, @returns
  - `resolveFormElement` (行 580) 缺少 @param, @returns
  - `collectFormValues` (行 602) 缺少 @param, @returns
  - `normalizeText` (行 631) 缺少 @param, @returns
  - `escapeHtmlValue` (行 642) 缺少 @param, @returns
  - `getDbBadgeMeta` (行 657) 缺少 @param, @returns
  - `bindCredentialsStoreEvents` (行 704) 缺少 @param, @returns
  - `closeDeleteModal` (行 724) 缺少 @param, @returns

## app/static/js/modules/views/credentials/modals/credential-modals.js
- 函数/方法文档不完整：
  - `init` (行 55) 缺少 @param
  - `handleCredentialTypeChange` (行 81) 缺少 @param
  - `resetForm` (行 121) 缺少 @param
  - `openCreate` (行 138) 缺少 @param
  - `buildPayload` (行 205) 缺少 @param

## app/static/js/modules/views/dashboard/overview.js
- 函数/方法文档不完整：
  - `initCharts` (行 47) 缺少 @param
  - `initLogTrendChart` (行 90) 缺少 @param

## app/static/js/modules/views/history/logs/logs.js
- 函数/方法文档不完整：
  - `mount` (行 28) 缺少 @param
  - `initializeGrid` (行 59) 缺少 @param
  - `buildColumns` (行 113) 缺少 @param
  - `initializeFilterCard` (行 234) 缺少 @param
  - `setDefaultTimeRange` (行 358) 缺少 @param
  - `initializeLogDetailModal` (行 469) 缺少 @param

## app/static/js/modules/views/history/logs/modals/log-detail-modal.js
- 函数/方法文档不完整：
  - `destroy` (行 286) 缺少 @param

## app/static/js/modules/views/history/sessions/modals/session-detail-modal.js
- 函数/方法文档不完整：
  - `clearContent` (行 262) 缺少 @param
  - `destroy` (行 271) 缺少 @param

## app/static/js/modules/views/history/sessions/sync-sessions.js
- 函数/方法文档不完整：
  - `ready` (行 43) 缺少 @param, @returns
  - `initializeService` (行 67) 缺少 @param
  - `initializeModals` (行 80) 缺少 @param, @returns
  - `initializeFilterCard` (行 104) 缺少 @param, @returns
  - `initializeSessionsGrid` (行 122) 缺少 @param, @returns
  - `buildColumns` (行 156) 缺少 @param, @returns
  - `handleServerResponse` (行 216) 缺少 @param, @returns
  - `resolveRowMeta` (行 235) 缺少 @param, @returns
  - `renderSessionId` (行 242) 缺少 @param, @returns
  - `renderSyncType` (行 255) 缺少 @param, @returns
  - `renderSyncCategory` (行 266) 缺少 @param, @returns
  - `renderStatusBadge` (行 285) 缺少 @param, @returns
  - `renderProgress` (行 297) 缺少 @param, @returns
  - `renderTimestamp` (行 323) 缺少 @param, @returns
  - `renderDuration` (行 337) 缺少 @param, @returns
  - `renderActions` (行 347) 缺少 @param, @returns
  - `bindGridEvents` (行 365) 缺少 @param, @returns
  - `setupAutoRefresh` (行 388) 缺少 @param, @returns
  - `clearAutoRefresh` (行 402) 缺少 @param, @returns
  - `applySyncFilters` (行 412) 缺少 @param, @returns
  - `resolveSyncFilters` (行 423) 缺少 @param, @returns
  - `collectFormValues` (行 447) 缺少 @param, @returns
  - `normalizeFilters` (行 475) 缺少 @param, @returns
  - `sanitizeFilterValue` (行 489) 缺少 @param, @returns
  - `sanitizePrimitiveValue` (行 501) 缺少 @param, @returns
  - `viewSessionDetail` (行 515) 缺少 @param, @returns
  - `showSessionDetail` (行 535) 缺少 @param, @returns
  - `cancelSession` (行 546) 缺少 @param, @returns
  - `notifySuccess` (行 569) 缺少 @param, @returns
  - `notifyError` (行 580) 缺少 @param, @returns
  - `escapeHtml` (行 591) 缺少 @param, @returns
  - `getProgressInfo` (行 617) 缺少 @param, @returns
  - `getStatusText` (行 646) 缺少 @param, @returns
  - `getStatusColor` (行 653) 缺少 @param, @returns
  - `getSyncTypeText` (行 661) 缺少 @param, @returns
  - `getSyncCategoryText` (行 674) 缺少 @param, @returns
  - `getDurationBadge` (行 688) 缺少 @param, @returns

## app/static/js/modules/views/instances/detail.js
- 函数/方法文档不完整：
  - `mountInstanceDetailPage` (行 13) 缺少 @param
  - `ensureInstanceService` (行 47) 缺少 @param
  - `initializeInstanceStore` (行 76) 缺少 @param
  - `teardownInstanceStore` (行 107) 缺少 @param
  - `toggleDeletedAccounts` (行 509) 缺少 @param
  - `getInstanceId` (行 542) 缺少 @param
  - `getInstanceName` (行 553) 缺少 @param
  - `loadDatabaseSizes` (行 584) 缺少 @param
  - `refreshDatabaseSizes` (行 817) 缺少 @param
  - `toggleDeletedDatabases` (行 826) 缺少 @param
  - `initializeHistoryModal` (行 865) 缺少 @param
  - `ensureHistoryModal` (行 882) 缺少 @param
  - `resetHistoryContent` (行 894) 缺少 @param

## app/static/js/modules/views/instances/list.js
- 函数/方法文档不完整：
  - `mountInstancesListPage` (行 13) 缺少 @param
  - `initializeServices` (行 81) 缺少 @param
  - `initializeInstanceStore` (行 107) 缺少 @param
  - `initializeModals` (行 133) 缺少 @param, @returns
  - `initializeGrid` (行 159) 缺少 @param, @returns
  - `buildColumns` (行 200) 缺少 @param
  - `renderDbTypeBadge` (行 371) 缺少 @param, @returns
  - `renderTags` (行 386) 缺少 @param, @returns
  - `renderStatusBadge` (行 407) 缺少 @param, @returns
  - `renderLastSync` (行 419) 缺少 @param, @returns
  - `renderActions` (行 432) 缺少 @param, @returns
  - `handleGridUpdated` (行 451) 缺少 @param, @returns
  - `resolveRowMeta` (行 458) 缺少 @param, @returns
  - `initializeFilterCard` (行 465) 缺少 @param, @returns
  - `handleFilterChange` (行 508) 缺少 @param, @returns
  - `collectFormValues` (行 542) 缺少 @param
  - `buildBaseUrl` (行 631) 缺少 @param
  - `syncUrl` (行 662) 缺少 @returns
  - `initializeTagFilter` (行 675) 缺少 @param, @returns
  - `parseInitialTagValues` (行 705) 缺少 @param, @returns
  - `bindToolbarActions` (行 718) 缺少 @param, @returns
  - `handleBatchDelete` (行 753) 缺少 @param, @returns
  - `handleBatchTest` (行 782) 缺少 @param, @returns
  - `exportInstances` (行 812) 缺少 @param, @returns
  - `subscribeToStoreEvents` (行 823) 缺少 @param, @returns
  - `updateSelectionSummary` (行 841) 缺少 @param, @returns
  - `syncSelectionCheckboxes` (行 856) 缺少 @param, @returns
  - `updateSelectAllCheckbox` (行 874) 缺少 @param, @returns
  - `collectAvailableInstanceIds` (行 901) 缺少 @param, @returns
  - `updateBatchActionState` (行 918) 缺少 @param, @returns
  - `syncStoreSelection` (行 941) 缺少 @param, @returns
  - `handleRowSelectionChange` (行 956) 缺少 @param, @returns
  - `handleSelectAllChange` (行 976) 缺少 @param, @returns
  - `handleTestConnection` (行 993) 缺少 @param, @returns
  - `toggleButtonLoading` (行 1023) 缺少 @param, @returns
  - `safeParseJSON` (行 1044) 缺少 @param, @returns
  - `formatTimestamp` (行 1056) 缺少 @param, @returns
  - `exposeGlobalActions` (行 1080) 缺少 @param, @returns
  - `escapeHtml` (行 1096) 缺少 @param, @returns

## app/static/js/modules/views/instances/modals/batch-create-modal.js
- 函数/方法文档不完整：
  - `open` (行 60) 缺少 @param
  - `submit` (行 111) 缺少 @param
  - `handleSubmit` (行 120) 缺少 @param
  - `resolveInstanceStore` (行 197) 缺少 @param
  - `resolveInstanceService` (行 209) 缺少 @param
  - `resetFileInput` (行 225) 缺少 @param
  - `attachTriggerEvents` (行 254) 缺少 @param
  - `attachFileChangeEvent` (行 269) 缺少 @param

## app/static/js/modules/views/instances/modals/instance-modals.js
- 函数/方法文档不完整：
  - `init` (行 44) 缺少 @param
  - `resetForm` (行 68) 缺少 @param
  - `openCreate` (行 85) 缺少 @param
  - `buildPayload` (行 160) 缺少 @param

## app/static/js/modules/views/instances/statistics.js
- 函数/方法文档不完整：
  - `mountInstanceStatisticsPage` (行 13) 缺少 @param
  - `ensureInstanceService` (行 50) 缺少 @param
  - `initializeInstanceStore` (行 80) 缺少 @param, @returns
  - `bindInstanceStoreEvents` (行 112) 缺少 @param, @returns
  - `subscribeToInstanceStore` (行 125) 缺少 @returns
  - `handleStatsUpdated` (行 135) 缺少 @returns
  - `teardownInstanceStore` (行 148) 缺少 @param, @returns
  - `handleVisibilityChange` (行 163) 缺少 @param, @returns
  - `createVersionChart` (行 174) 缺少 @param, @returns
  - `getVersionStats` (行 202) 缺少 @param
  - `getChartOptions` (行 304) 缺少 @param
  - `showEmptyChart` (行 343) 缺少 @returns
  - `startAutoRefresh` (行 354) 缺少 @param, @returns
  - `stopAutoRefresh` (行 366) 缺少 @param, @returns
  - `refreshStatistics` (行 376) 缺少 @param, @returns
  - `updateStatistics` (行 401) 缺少 @returns
  - `updateVersionChart` (行 422) 缺少 @returns
  - `removeExistingNotification` (行 434) 缺少 @param, @returns
  - `showDataUpdatedNotification` (行 441) 缺少 @param, @returns
  - `showErrorNotification` (行 462) 缺少 @returns
  - `manualRefresh` (行 482) 缺少 @param, @returns

## app/static/js/modules/views/tags/batch_assign.js
- 函数/方法文档不完整：
  - `mountBatchAssignPage` (行 860) 缺少 @param

## app/static/js/modules/views/tags/index.js
- 函数/方法文档不完整：
  - `initializeGrid` (行 63) 缺少 @param
  - `initializeTagModals` (行 185) 缺少 @param, @returns
  - `bindQuickActions` (行 203) 缺少 @param, @returns
  - `initializeDeleteModal` (行 216) 缺少 @param, @returns
  - `confirmDeleteTag` (行 242) 缺少 @returns
  - `handleDeleteConfirmation` (行 250) 缺少 @param, @returns
  - `initializeFilterCard` (行 280) 缺少 @param, @returns
  - `destroyFilterCard` (行 321) 缺少 @param, @returns
  - `applyTagFilters` (行 331) 缺少 @returns
  - `resetTagFilters` (行 357) 缺少 @returns
  - `normalizeGridFilters` (行 393) 缺少 @param, @returns
  - `sanitizeFilterValue` (行 406) 缺少 @param, @returns
  - `sanitizePrimitiveValue` (行 416) 缺少 @param, @returns
  - `buildQueryParams` (行 433) 缺少 @param, @returns
  - `resolveFormElement` (行 448) 缺少 @param, @returns
  - `collectFormValues` (行 470) 缺少 @param, @returns
  - `openTagEditor` (行 514) 缺少 @param, @returns
  - `showLoadingState` (行 527) 缺少 @returns
  - `hideLoadingState` (行 543) 缺少 @returns

## app/static/js/modules/views/tags/modals/tag-modals.js
- 函数/方法文档不完整：
  - `init` (行 52) 缺少 @param
  - `resetForm` (行 76) 缺少 @param
  - `updateColorPreview` (行 93) 缺少 @param
  - `openCreate` (行 107) 缺少 @param
  - `buildPayload` (行 173) 缺少 @param

## app/utils/cache_utils.py
- 函数/方法文档不完整：
  - `init_cache_manager` (行 162) 缺少 Returns

## app/utils/structlog_config.py
- 函数/方法文档不完整：
  - `StructlogConfig.shutdown` (行 186) 缺少 Returns

## scripts/check_missing_docs_smart.py
- 函数/方法文档不完整：
  - `get_python_doc_issues` (行 198) 缺少 Args, Returns
  - `main` (行 379) 缺少 Returns

## scripts/code/analyze_code.py
- 函数/方法文档不完整：
  - `count_lines` (行 12) 缺少 Args, Returns
  - `print_summary` (行 76) 缺少 Args, Returns
  - `print_top_files` (行 93) 缺少 Args, Returns
  - `export_to_json` (行 111) 缺少 Args, Returns
  - `generate_markdown_report` (行 117) 缺少 Args, Returns

## scripts/code/safe_update_code_analysis.py
- 函数/方法文档不完整：
  - `analyze_directory` (行 19) 缺少 Args, Returns
  - `get_directory_breakdown` (行 51) 缺少 Args, Returns
  - `generate_file_type_table` (行 73) 缺少 Args, Returns
  - `generate_directory_detail_table` (行 85) 缺少 Args, Returns
  - `update_report` (行 96) 缺少 Args, Returns
  - `main` (行 105) 缺少 Returns

## scripts/password/reset_admin_password.py
- 函数/方法文档不完整：
  - `generate_random_password` (行 21) 缺少 Args, Returns
  - `reset_admin_password` (行 26) 缺少 Args, Returns
  - `main` (行 65) 缺少 Returns
