# Python `or` Fallback Scan (AST)

- Generated: 2026-01-16 07:23:32 UTC
- Paths: app
- Exclude: tests/**

## Summary

- Python files scanned: 435
- AST parse failures: 0
- `or` chains (BoolOp(Or)): 647
- Chains with `""/0/False/[]/{}` candidates: 378

## Directory Distribution

| Directory | `or` chains | candidate chains |
|---|---:|---:|
| `app/services/**` | 360 | 204 |
| `app/repositories/**` | 85 | 78 |
| `app/api/**` | 101 | 50 |
| `app/utils/**` | 30 | 21 |
| `app/routes/**` | 15 | 11 |
| `app/infra/**` | 6 | 4 |
| `app/views/**` | 22 | 3 |
| `app/schemas/**` | 13 | 2 |
| `app/core/**` | 6 | 2 |
| `app/models/**` | 4 | 2 |
| `app/tasks/**` | 2 | 1 |
| `app/settings.py/**` | 2 | 0 |
| `app/__init__.py/**` | 1 | 0 |

## Top Files (by candidate chains, then total)

| File | `or` chains | candidate chains |
|---|---:|---:|
| `app/services/history_sessions/history_sessions_read_service.py` | 22 | 21 |
| `app/services/accounts_sync/adapters/sqlserver_adapter.py` | 14 | 14 |
| `app/utils/query_filter_utils.py` | 14 | 14 |
| `app/services/tags/tag_options_service.py` | 15 | 13 |
| `app/api/v1/namespaces/instances.py` | 13 | 10 |
| `app/services/partition/partition_read_service.py` | 10 | 9 |
| `app/repositories/users_repository.py` | 9 | 9 |
| `app/api/v1/namespaces/capacity.py` | 20 | 8 |
| `app/api/v1/namespaces/databases.py` | 16 | 8 |
| `app/repositories/tags_repository.py` | 8 | 8 |
| `app/services/aggregation/aggregation_service.py` | 13 | 7 |
| `app/services/statistics/database_statistics_service.py` | 9 | 7 |
| `app/repositories/account_statistics_repository.py` | 8 | 7 |
| `app/services/accounts_sync/adapters/mysql_adapter.py` | 8 | 7 |
| `app/services/accounts_sync/permission_manager.py` | 9 | 6 |
| `app/api/v1/namespaces/credentials.py` | 8 | 6 |
| `app/services/capacity/instance_aggregations_read_service.py` | 8 | 6 |
| `app/services/database_sync/table_size_coordinator.py` | 7 | 6 |
| `app/repositories/instances_repository.py` | 6 | 6 |
| `app/services/accounts_sync/adapters/oracle_adapter.py` | 7 | 5 |
| `app/repositories/capacity_instances_repository.py` | 6 | 5 |
| `app/services/capacity/database_aggregations_read_service.py` | 6 | 5 |
| `app/services/common/filter_options_service.py` | 6 | 5 |
| `app/repositories/instance_accounts_repository.py` | 5 | 5 |
| `app/services/database_sync/table_size_adapters/oracle_adapter.py` | 5 | 5 |
| `app/services/aggregation/capacity_aggregation_task_runner.py` | 8 | 4 |
| `app/api/v1/namespaces/accounts.py` | 7 | 4 |
| `app/services/capacity/capacity_databases_page_service.py` | 7 | 4 |
| `app/infra/route_safety.py` | 6 | 4 |
| `app/services/files/instances_export_service.py` | 6 | 4 |

## Pattern Counts

| Pattern | Hits |
|---|---:|
| `... or ""` | 158 |
| `... or 0` | 127 |
| `... or {}` | 54 |
| `... or []` | 33 |
| `... or False` | 6 |

