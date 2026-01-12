---
title: WhaleFall 项目结构
aliases:
  - project-structure
tags:
  - architecture
  - architecture/project-structure
status: active
created: 2025-12-17
updated: 2026-01-10
owner: WhaleFall Team
scope: 仓库目录结构与代码落点
related:
  - "[[architecture/developer-entrypoint]]"
  - "[[architecture/identity-access]]"
  - "[[architecture/spec]]"
  - "[[API/api-v1-api-contract]]"
  - "[[operations/observability-ops]]"
  - "[[standards/doc/document-boundary-standards]]"
  - "[[standards/doc/documentation-standards]]"
---

# WhaleFall 项目结构

> [!info] 这份文档解决什么
> - 快速定位: 你要改什么, 应该去哪里改.
> - 本文是"代码地图", 不追求把全部文件逐一罗列.
> - 常见任务请从 [[architecture/developer-entrypoint]] 开始.

## 1. 仓库根目录(Repo)

| Path | 作用 | 备注 |
| --- | --- | --- |
| `app/` | Flask 应用代码 | 业务代码 SSOT |
| `docs/` | 文档 | SSOT 在 `docs/Obsidian/**` |
| `tests/` | 测试 | 单测在 `tests/unit/` |
| `migrations/` | 数据库迁移 | 约束见 `docs/Obsidian/standards/backend/database-migrations.md` |
| `scripts/` | 工具脚本 | CI, 本地巡检, 报告生成 |
| `sql/` | 初始化/运维 SQL | 运维辅助, 不承载业务逻辑 |
| `nginx/` | Nginx 配置 | 生产部署相关 |
| `userdata/` | 运行时数据目录 | 本地生成, 不提交 |
| `skills/` | 协作技能 | Codex workflow/skills |
| `tools/` | 工具目录 | 本地工具与辅助脚本 |
| `worktrees/` | Git worktrees | 本地生成, 不提交 |
| `app.py` | 开发启动入口 | `uv run python app.py` |
| `wsgi.py` | WSGI 入口 | gunicorn 使用 |
| `Makefile*` | 常用命令入口 | `make install`, `make dev-start`, `make typecheck` |
| `docker-compose.*.yml` | Compose 入口 | dev/prod/flask-only |

> [!note] 本地生成目录(常见)
> - `.venv/`: `uv` 创建的虚拟环境.
> - `node_modules/`: 仅在运行 `npm install` 后出现.
> - `userdata/`: scheduler SQLite, 导出文件, 日志文件等.

## 2. `app/` 目录(应用代码)

### 2.1 总览(分层与职责)

| Path | 职责 |
| --- | --- |
| `app/__init__.py` | app factory, extensions, blueprints, 全局错误处理 |
| `app/settings.py` | 配置 SSOT(解析 + 默认值 + 校验) |
| `app/api/v1/**` | `/api/v1/**` JSON API(Flask-RESTX + OpenAPI) |
| `app/routes/**` | Web UI 路由(Blueprint), 渲染 Jinja2 templates |
| `app/services/**` | 业务编排与领域逻辑 |
| `app/repositories/**` | 只读 query 组合与数据访问细节 |
| `app/models/**` | SQLAlchemy models(主库) |
| `app/schemas/**` | Pydantic payload schemas(写路径入参校验) |
| `app/tasks/**` | 后台任务入口(由 scheduler 调用) |
| `app/scheduler.py` | APScheduler 封装 + SQLite jobstore(`userdata/scheduler.db`) |
| `app/config/*.yaml` | 业务规则配置(account_filters/database_filters/scheduler_tasks) |
| `app/forms/**` | Flask-WTF 表单定义(主要用于 Web UI) |
| `app/views/**` | 表单/资源视图封装(Web UI 复用) |
| `app/templates/**` | Jinja2 模板 |
| `app/static/**` | 静态资源与前端模块(含 vendor) |
| `app/utils/**` | 可复用工具(纯函数优先), 不承载业务规则 |
| `app/core/types/**` | 类型别名, 协议, TypedDict 等 |
| `app/core/constants/**` | 常量与枚举 |
| `app/core/exceptions.py` | 统一错误类型(AppError 体系) |

### 2.2 Web UI vs API v1

- Web UI:
  - HTTP 层落点: `app/routes/**`
  - 页面落点: `app/templates/**` + `app/static/**`
  - 认证/会话: Flask-Login session cookie + CSRF
- API v1:
  - HTTP 层落点: `app/api/v1/namespaces/*.py`
  - OpenAPI: `/api/v1/openapi.json`
  - SSOT: `docs/Obsidian/API/*-api-contract.md` + [[API/api-v1-api-contract|API v1 contract index]]
  - 认证/权限: 见 [[architecture/identity-access]]

## 3. 领域落点(Where to change what)

> [!tip]
> 需要"按任务"找入口时, 优先走 [[architecture/developer-entrypoint]].

### 3.1 Instances(实例)

- Web: `app/routes/instances/*` + `app/templates/instances/*`
- API v1: `app/api/v1/namespaces/instances.py` + `app/api/v1/restx_models/instances.py`
- Service: `app/services/instances/**`
- Repo: `app/repositories/instances_repository.py`, `app/repositories/instance_statistics_repository.py`
- Models: `app/models/instance.py`, `app/models/instance_account.py`, `app/models/instance_database.py`

### 3.2 Credentials(凭据) + Connections(连接测试)

- Web: `app/routes/credentials.py` + `app/templates/credentials/*`
- API v1: `app/api/v1/namespaces/credentials.py`, `app/api/v1/namespaces/instances_connections.py`
- Service: `app/services/credentials/**`, `app/services/connection_adapters/**`, `app/services/connections/**`
- Repo: `app/repositories/credentials_repository.py`
- Model: `app/models/credential.py`

### 3.3 Accounts(账户) + Classifications(分类) + Permissions(权限)

- Web: `app/routes/accounts/*` + `app/templates/accounts/*`
- API v1: `app/api/v1/namespaces/accounts.py`, `app/api/v1/namespaces/accounts_classifications.py`
- Service:
  - 账户查询与台账: `app/services/accounts/**`, `app/services/ledgers/**`
  - 权限快照: `app/services/accounts_permissions/**`
  - 分类与规则: `app/services/account_classification/**`
  - 同步编排: `app/services/accounts_sync/**`
- Models: `app/models/account_classification.py`, `app/models/account_permission.py`, `app/models/account_change_log.py`

### 3.4 Tags(标签)

- Web: `app/routes/tags/*` + `app/templates/tags/*`
- API v1: `app/api/v1/namespaces/tags.py`
- Service: `app/services/tags/**`
- Repo: `app/repositories/tags_repository.py`
- Model: `app/models/tag.py`

### 3.5 Capacity(容量) + Aggregations(聚合)

- Web: `app/routes/capacity/*` + `app/templates/capacity/*`
- API v1: `app/api/v1/namespaces/capacity.py`
- Service: `app/services/capacity/**`, `app/services/aggregation/**`
- Repo: `app/repositories/capacity_*_repository.py`
- Models: `app/models/database_size_stat.py`, `app/models/database_size_aggregation.py`, `app/models/instance_size_stat.py`
- Tasks: `app/tasks/capacity_collection_tasks.py`, `app/tasks/capacity_aggregation_tasks.py`

### 3.6 Scheduler(任务调度) + Tasks(后台任务)

- Web: `app/routes/scheduler.py` + `app/templates/admin/scheduler/*`
- API v1: `app/api/v1/namespaces/scheduler.py`
- Scheduler: `app/scheduler.py` + `app/config/scheduler_tasks.yaml`
- Tasks: `app/tasks/**`

### 3.7 History(历史) + Logs(统一日志) + Sync sessions(同步会话)

- Web: `app/routes/history/*` + `app/templates/history/*`
- API v1: `app/api/v1/namespaces/logs.py`, `app/api/v1/namespaces/sessions.py`
- Service: `app/services/history_logs/**`, `app/services/history_sessions/**`
- Repo: `app/repositories/history_logs_repository.py`, `app/repositories/history_sessions_repository.py`
- Models: `app/models/unified_log.py`, `app/models/sync_session.py`

### 3.8 Databases(数据库台账) + Table sizes(表容量)

- Web: `app/routes/databases/*` + `app/templates/databases/*`
- API v1: `app/api/v1/namespaces/databases.py`
- Service:
  - ledger: `app/services/ledgers/database_ledger_service.py`
  - export: `app/services/files/database_ledger_export_service.py`
  - table sizes: `app/services/instances/instance_database_table_sizes_service.py`, `app/services/database_sync/table_size_coordinator.py`
- Repo: `app/repositories/ledgers/database_ledger_repository.py`
- Models: `app/models/instance_database.py`, `app/models/database_size_stat.py`, `app/models/database_table_size_stat.py`

### 3.9 Dashboard(仪表板) + Partitions(分区)

- Web:
  - dashboard: `app/routes/dashboard.py` + `app/templates/dashboard/*`
  - partitions: `app/routes/partition.py` + `app/templates/admin/partitions/*`
- API v1: `app/api/v1/namespaces/dashboard.py`, `app/api/v1/namespaces/partition.py`
- Service: `app/services/dashboard/**`, `app/services/partition/**`
- Repo: `app/repositories/dashboard_charts_repository.py`, `app/repositories/partition_repository.py`

## 4. 数据库与迁移

- 模型: `app/models/**`
- 迁移: `migrations/**`
  - 约束: 不修改历史 migration.
  - 规范: `docs/Obsidian/standards/backend/database-migrations.md`
- 初始化/运维 SQL: `sql/**`

## 5. 配置与运行

- 配置 SSOT: `app/settings.py` + `env.example`(禁止写真实密钥)
- YAML 配置: `app/config/*.yaml`
- 本地开发: [[getting-started/local-dev]]
- 常用自检: `uv run pytest -m unit`, `./scripts/ci/ruff-report.sh style`, `make typecheck`

## 6. 文档结构(SSOT)

- `docs/Obsidian/standards/**`: 标准(SSOT)
- `docs/Obsidian/reference/**`: 参考(SSOT)
- `docs/Obsidian/API/**`: API contract(SSOT)
- `docs/Obsidian/operations/**`: 运维与排障
