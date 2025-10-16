# 重构文档涉及代码位置索引

本索引将每份重构/统一文档映射到仓库中的具体代码位置，便于后续重构定位与批量治理。路径均为相对仓库根目录。

## 错误处理与日志
- `error_handling_unification.md`
  - `app/utils/structlog_config.py`
  - `app/utils/api_response.py`
  - `app/__init__.py`
  - `app/routes/*.py`
  - `app/services/*.py`
  - `app/tasks/*.py`
  - （清理）`app/utils/logging_config.py`, `app/utils/error_handler.py`

- `error_logging_unification.md`
  - `app/utils/structlog_config.py`
  - `app/utils/logging_config.py`（废弃迁移）
  - `app/utils/error_handler.py`（废弃迁移）
  - `app/models/unified_log.py`
  - `app/routes/*.py`, `app/services/*.py`

- `timezone_and_loglevel_unification.md`
  - `app/utils/time_utils.py`
  - `app/utils/structlog_config.py`
  - `app/models/*`（时间字段统一口径）
  - `app/tasks/*.py`, `app/services/*.py`

## 响应、验证与权限
- `api_response_unification.md`
  - `app/utils/api_response.py`
  - `app/routes/*.py`

- `request_validation_unification.md`
  - `app/utils/validation.py`
  - `app/utils/data_validator.py`
  - `app/utils/decorators.py`（`validate_json`）
  - `app/routes/*.py`

- `auth_permission_unification.md`
  - `app/utils/decorators.py`
  - `app/utils/rate_limiter.py`
  - `app/routes/*.py`
  - `app/templates/errors/*.html`（页面路由反馈）

- `routes_restful_unification.md`
  - `app/routes/*.py`
  - `app/routes/__init__.py`

## 安全与跨域
- `csrf_frontend_unification.md`
  - 后端：`app/__init__.py`（CSRFProtect/CORS），`app/routes/auth.py`（令牌发放），`app/utils/security_csrf.py`（统一 CSRF 装饰器）
  - 前端：`app/static/js/**`（Axios 拦截器与写操作统一注入）

- `cors_security_headers_unification.md`
  - `app/__init__.py`（CORS 配置与安全响应头）
  - `app/routes/*.py`
  - （如使用反向代理）`nginx/conf.d/*`（跨域与安全头对齐）

## 缓存与限流
- `cache_rate_limit_unification.md`
  - `app/utils/cache_manager.py`
  - `app/utils/rate_limiter.py`
  - `app/routes/*.py`

## 数据库与查询
- `db_models_migrations_refactor.md`
  - `app/models/*.py`
  - `migrations/versions/*.py`
  - `migrations/env.py`

- `db_transaction_query_unification.md`
  - `app/utils/db_context.py`
  - `app/routes/*.py`
  - `app/services/*.py`

- `db_connections_accounts_refactor.md`
  - `app/routes/connections.py`
  - `app/models/*.py`
  - `app/services/*.py`
  - `app/config.py`（连接池与凭据配置）

## 搜索、分页与统计
- `search_pagination_refactor.md`
  - `app/routes/instances.py`, `app/routes/credentials.py`, `app/routes/logs.py`, `app/routes/sync_sessions.py`
  - `app/utils/api_response.py`（分页响应结构，如适用）

- `pagination_audit.md`
  - `app/routes/*.py`（分页契约核查）

- `aggregation_stats_refactor.md`
  - `app/routes/aggregations.py`
  - `app/services/*.py`（统计聚合层）
  - `app/utils/cache_manager.py`（统计缓存）

- `charts_dashboard_refactor.md`
  - `app/routes/dashboard.py`
  - `app/templates/dashboard/*`
  - `app/static/js/**`（前端图表库与数据契约）

## 调度与同步
- `scheduler_reliability_refactor.md`
  - `app/scheduler.py`
  - `app/tasks/*.py`
  - `env.*` 与 `app/config.py`（APScheduler 持久化与连接配置）

- `capacity_sync_refactor.md`
  - `app/tasks/legacy_tasks.py`
  - `app/services/sync_adapters/*`
  - `app/models/*.py`（容量/配额数据模型）

## 配置、命名与技术债
- `config_env_refactor.md`
  - `app/config.py`
  - `env.development`, `env.production`

- `naming_context_unification.md`
  - `app/utils/structlog_config.py`（日志上下文字段）
  - `app/models/*.py`（字段命名统一）
  - `app/routes/*.py`（参数命名统一）

- `technical_debt_cleanup.md`
  - 全局性：与上述所有模块相关

—— 索引会随文档更新持续补充；建议在每个重构 PR 说明中引用本索引并列出本次改动覆盖的具体文件。