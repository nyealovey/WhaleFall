# 命名重构执行记录

> 用于跟踪 1.2.0 命名重构过程中每一次修改，确保所有引用同步更新。

## 记录格式

| 序号 | 时间 | 变更描述 | 受影响文件 | 检查/备注 |
| --- | --- | --- | --- | --- |

| 1 | 2025-10-31 15:50:03 | 重命名 `app/services/cache_manager.py` → `cache_service.py`，类改为 `CacheService`，初始化入口调整为 `init_cache_service` | app/services/cache_service.py | 引用已替换 (app/__init__.py, services.*, routes/cache.py, routes/health.py) |

| 2 | 2025-10-31 15:57:39 | 上移 `account_sync_service.py` 到 services 根目录并更新引用 | app/services/account_sync_service.py 等 | routes/account.py, routes/account_sync.py, tasks/account_sync_tasks.py |

| 3 | 2025-10-31 15:59:13 | 上移 `capacity_sync_service.py` 并调整引用 | app/services/capacity_sync_service.py 等 | tasks/database_size_collection_tasks.py, routes/storage_sync.py |

| 4 | 2025-10-31 16:02:46 | 重命名聚合 Runner 文件以明确职责 | app/services/aggregation/database_aggregation_runner.py, app/services/aggregation/instance_aggregation_runner.py | aggregation_service.py 引用已更新 |

| 5 | 2025-10-31 16:05:58 | 重命名 `app/utils/cache_manager.py` → `cache_utils.py` 并更新引用 | app/utils/cache_utils.py | app/__init__.py, routes/dashboard.py |

| 6 | 2025-10-31 16:09:06 | 重命名 `app/routes/instances_detail.py` → `instance_detail.py` 并更新 `instances.py` 引用 | app/routes/instance_detail.py | app/routes/instance.py |

| 7 | 2025-10-31 16:10:29 | 重命名 `app/routes/instances_stats.py` → `instance_statistics.py` 并更新 `instances.py` 引用 | app/routes/instance_statistics.py | app/routes/instance.py |

| 8 | 2025-10-31 16:21:38 | 重命名 `app/utils/filter_data.py` → `query_filter_utils.py` 并更新引用 | app/utils/query_filter_utils.py 等 | routes (account/logs/instance_stats/instances/databases/credentials/tags), constants/filter_options.py |

| 9 | 2025-10-31 16:23:51 | 将 `password_manager.py` 重命名为 `password_crypto_utils.py` 并更新凭据模型引用 | app/utils/password_crypto_utils.py | app/models/credential.py |

| 10 | 2025-10-31 16:26:33 | 重命名 `sqlserver_connection_diagnostics.py` → `sqlserver_connection_utils.py` 并更新连接工厂引用 | app/utils/sqlserver_connection_utils.py | app/services/connection_adapters/connection_factory.py |

| 11 | 2025-10-31 16:49:34 | 重命名数据库统计路由 `database_stats` → `databases` 并更新所有前端/文档引用 | app/routes/databases.py 等 | app/__init__.py, routes/instance_detail.py, 前端 JS, docs 等 |

| 12 | 2025-10-31 16:54:52 | 重命名 `app/routes/instances.py` → `instance.py` 并更新引用 | app/routes/instance.py 等 | app/__init__.py, routes/instance_detail.py, routes/instance_statistics.py |

| 13 | 2025-10-31 17:07:35 | 重命名 `app/routes/storage_sync.py` → `storage.py`，更新 Blueprint 前缀与前端调用路径 | app/routes/storage.py 等 | app/__init__.py, static/js pages/instances, docs/api 等 |

| 14 | 2025-10-31 17:16:16 | 将实例蓝图统一为 `instance_bp`，同步所有 `url_for` 与文档引用 | app/routes/instance.py, app/routes/account_sync.py 等 | app/templates/instances/*, app/templates/auth/profile.html, docs/api, docs/architecture |
