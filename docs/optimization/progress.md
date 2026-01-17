# Repo Simplicity Optimization Progress

> 目标：对仓库做 code-simplicity-reviewer 式极简化（严格 YAGNI），逐“功能模块”交付模块文档与勾选追踪。

## Hard Constraints（硬约束）

- 严格 YAGNI；禁止无依据兜底/防御性分支/吞异常继续
- 不改变对外行为/接口/迁移历史
- 每完成一个模块：必须执行并在此处记录 `make format && make typecheck && uv run pytest -m unit`
- 每个模块文档：必须包含 `file:line` 与“可删 LOC 估算”

## Latest Verification（最近一次验证）

- Date: 2026-01-17T19:57:30+0800
- Result: PASS (`make format && make typecheck && uv run pytest -m unit`)

## Modules（按依赖→耦合排序；同层级 CRUD→同步/自动化）

### 基础层（被依赖最多）

- [x] app/core/constants（系统常量）
- [x] app/core/types（类型定义）
- [x] app/core/exceptions（统一异常）
- [x] app/utils/logging + app/utils/structlog_config.py（结构化日志）
- [x] app/utils/http（decorators/request_payload/response_utils/proxy_fix_middleware/pagination）
- [x] app/utils/db（safe_query_builder/sqlserver_connection_utils/database_type_utils/query_filter_utils/cache_utils）
- [x] app/utils/security（rate_limiter/redirect_safety/password_crypto_utils/sensitive_data/spreadsheet_formula_safety）
- [x] app/utils/misc（time_utils/version_parser/payload_converters/status_type_utils/user_role_utils/theme_color_utils）
- [x] app/settings.py（配置读取/默认值/校验）
- [x] app/config/*.yaml（过滤器/调度任务配置）
- [x] app/infra（logging/route_safety/error_mapping/...）
- [x] app/schemas（base/validation/contracts）
- [x] app/models（ORM）
- [x] app/repositories（数据访问）
- [x] app/api/v1（API 封套/错误口径/契约边界）

### 业务层（CRUD 为主）

- [x] services/auth + routes/auth + templates/auth（认证）
- [x] services/users + routes/users + templates/users（用户）
- [x] services/credentials + routes/credentials + templates/credentials（凭证）
- [x] services/tags + routes/tags + templates/tags（标签）
- [x] services/instances + routes/instances + templates/instances（实例）
- [x] services/accounts + routes/accounts + templates/accounts（账户）
- [x] services/ledgers + repositories/ledgers + templates/(TBD)（台账）
- [x] services/history_logs + services/history_sessions + routes/history + templates/history（历史）
- [x] services/dashboard + services/statistics + services/aggregation + routes/(TBD) + templates/dashboard（仪表盘/统计）

### 基础服务（被多业务复用）

- [x] services/common（通用服务）
- [x] services/connection_adapters + services/connections（连接/适配器）
- [x] services/cache + services/cache_service（缓存）
- [x] services/partition（分区）
- [x] services/files（文件）
- [x] services/health（健康检查）
- [x] services/logging（日志）

### 同步/自动化（高耦合/复杂流程）

- [x] scheduler（app/scheduler.py + services/scheduler + core/constants/scheduler_jobs.py）
- [x] accounts_sync（services/accounts_sync + tasks/accounts_sync_tasks.py）
- [x] database_sync（services/database_sync）
- [x] capacity-sync（services/capacity + tasks/capacity_*）
- [x] account_classification（services/account_classification + utils/account_classification_dsl_v4.py）

## Verification Log（每模块一条）

<!--
格式（示例）：
- 2026-01-17 app/core: PASS (make format/typecheck/pytest -m unit)
-->

- 2026-01-17 app/core/constants: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/settings.py: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/core/types: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/core/exceptions: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/utils/logging: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/utils/http: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/utils/db: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/utils/security: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/utils/misc: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/config/*.yaml: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/infra: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/schemas: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/models: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/repositories: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 app/api/v1: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/auth: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/users: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/credentials: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/tags: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/instances: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/accounts: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/ledgers: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/history_logs + services/history_sessions: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/dashboard + services/statistics + services/aggregation: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/common: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/connection_adapters + services/connections: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/cache + services/cache_service: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/partition: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/files: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/health: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 services/logging: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 scheduler: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 accounts_sync: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 database_sync: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 capacity-sync: PASS (make format/typecheck/pytest -m unit)
- 2026-01-17 account_classification: PASS (make format/typecheck/pytest -m unit)
