# app/services 目录死代码分析报告
生成时间：2025-10-28 09:12:58


## cache_manager.py
发现 6 个可能未使用的项

- **get_database_permissions_cache** (method) - 引用次数: 1
- **set_database_permissions_cache** (method) - 引用次数: 1
- **get_all_database_permissions_cache** (method) - 引用次数: 1
- **get_account_permissions_cache** (method) - 引用次数: 1
- **set_account_permissions_cache** (method) - 引用次数: 1
- **invalidate_rule_evaluation_cache** (method) - 引用次数: 1

## account_classification_service.py
✅ 未发现明显的死代码

## account_statistics_service.py
✅ 未发现明显的死代码

## database_size_aggregation_service.py
发现 4 个可能未使用的项

- **calculate_today_aggregations** (method) - 引用次数: 1
- **calculate_today_instance_aggregations** (method) - 引用次数: 1
- **get_instance_aggregations** (method) - 引用次数: 1
- **get_trends_analysis** (method) - 引用次数: 1

## database_type_service.py
发现 6 个可能未使用的项

- **get_type_by_id** (method) - 引用次数: 1
- **create_type** (method) - 引用次数: 1
- **update_type** (method) - 引用次数: 1
- **delete_type** (method) - 引用次数: 1
- **toggle_status** (method) - 引用次数: 1
- **init_default_types** (method) - 引用次数: 1

## partition_management_service.py
✅ 未发现明显的死代码

## scheduler_health_service.py
✅ 未发现明显的死代码

## sync_session_service.py
发现 1 个可能未使用的项

- **recover_stuck_instances** (method) - 引用次数: 1

## account_sync_adapters/base_sync_adapter.py
✅ 未发现明显的死代码

## account_sync_adapters/mysql_sync_adapter.py
✅ 未发现明显的死代码

## account_sync_adapters/postgresql_sync_adapter.py
✅ 未发现明显的死代码

## account_sync_adapters/sqlserver_sync_adapter.py
✅ 未发现明显的死代码

## account_sync_adapters/oracle_sync_adapter.py
✅ 未发现明显的死代码

## account_sync_adapters/account_sync_service.py
✅ 未发现明显的死代码

## account_sync_adapters/account_data_manager.py
发现 1 个可能未使用的项

- **get_supported_db_types** (method) - 引用次数: 1

## capacity_sync_adapters/capacity_sync_service.py
发现 1 个可能未使用的项

- **collect_all_instances_database_sizes** (function) - 引用次数: 1

## connection_adapters/connection_factory.py
✅ 未发现明显的死代码

## connection_adapters/connection_test_service.py
✅ 未发现明显的死代码

## account_sync_filters/database_filter_manager.py
发现 6 个可能未使用的项

- **get_sql_filter_conditions** (method) - 引用次数: 1
- **get_safe_sql_filter_conditions** (method) - 引用次数: 1
- **should_include_account** (method) - 引用次数: 1
- **update_filter_rules** (method) - 引用次数: 1
- **save_filter_rules_to_file** (method) - 引用次数: 1
- **get_filter_statistics** (method) - 引用次数: 1
