# Architecture Audit (architecture-strategist)
> 状态: Draft
> 负责人: team
> 创建: 2026-01-10
> 更新: 2026-01-10
> 范围: `app/**`, `docs/Obsidian/architecture/**`, 以及仓库入口文件(`app.py`, `wsgi.py`, `pyproject.toml`)
> 方法: 文档与入口抽样阅读 + 分层依赖边界静态扫描(`rg`) + 关键模块 import 走向核对

## 1. Architecture overview

WhaleFall 是一个 Flask 单体应用, 同时提供 Web UI(SSR: Jinja2 + Bootstrap + Grid.js)与版本化 JSON API(`app/api/v1/**`, Flask-RESTX + OpenAPI). 系统围绕 "实例/凭据/账户权限/容量/调度/日志" 等 DBA 场景组织领域能力, 并通过 adapters 连接外部数据库完成同步与采集.

架构与分层的 SSOT 入口主要在:

- `docs/Obsidian/architecture/spec.md`(as-built 能力图, C4, 关键流程与运行拓扑)
- `docs/Obsidian/architecture/module-dependency-graph.md`(layer-first 依赖方向, import 级别边界)
- `docs/Obsidian/architecture/developer-entrypoint.md`(常见改动的落点导航与自检)
- `docs/Obsidian/API/*-api-contract.md`(API contract SSOT)

## 2. Component map (as-built)

### 2.1 Interface layer

- Web UI: `app/routes/**` + `app/templates/**` + `app/static/**`
- API v1: `app/api/v1/**`(blueprint 由 `app/api/__init__.py:register_api_blueprints` 注册)

### 2.2 Domain layer

- Services: `app/services/**`(业务编排, write operation 边界, adapters 协调)
- Tasks: `app/tasks/**`(调度入口, 业务逻辑下沉到 services)
- Schemas: `app/schemas/**`(schema/DTO, 供 API v1 与 services 共享)
- Forms/Views: `app/forms/**`, `app/views/**`(UI 层的输入与渲染辅助)

### 2.3 Data layer

- Repositories: `app/repositories/**`(read query 组合与访问细节)
- Models: `app/models/**`(SQLAlchemy 持久化模型)

### 2.4 Foundations (base)

- Settings: `app/settings.py`(环境变量解析, 默认值, 校验, 统一注入 `app.config`)
- Utils/Types/Constants/Errors: `app/utils/**`, `app/types/**`, `app/constants/**`, `app/errors/**`

### 2.5 Runtime/infra

- App factory: `app/__init__.py:create_app`
- Scheduler: `app/scheduler.py`(APScheduler + SQLite jobstore + 文件锁单实例)
- Migrations: `migrations/**`
- Ops: `nginx/**`, `docker-compose*.yml`, `Dockerfile.prod`
- Tooling: `scripts/**`, `Makefile*`, `pyproject.toml`, `package.json`

## 3. Compliance check (layer-first)

本节以 `docs/Obsidian/architecture/module-dependency-graph.md` 为口径, 对核心依赖边界做静态抽样核对.

### 3.1 Dependency boundary scan (static)

扫描命令(同 `module-dependency-graph.md` 的建议口径):

```bash
rg -n "from app\\.routes|import app\\.routes|from app\\.api|import app\\.api" app/services
rg -n "from app\\.services|import app\\.services|from app\\.routes|import app\\.routes|from app\\.api|import app\\.api" app/repositories
rg -n "from app\\.services|from app\\.routes|from app\\.api|from app\\.repositories" app/utils
```

结果摘要:

- `app/services/**` 反向依赖 `app/routes`/`app/api`: 0 处命中
- `app/utils/**` 反向依赖 services/routes/api/repositories: 0 处命中
- `app/repositories/**` 依赖 services: 1 处命中
  - `app/repositories/partition_repository.py` import `app.services.statistics.partition_statistics_service.PartitionStatisticsService`

结论:

- 当前整体分层依赖方向基本符合 layer-first 约束.
- 但 repositories->services 的 1 处反向依赖属于明确的边界破坏信号, 建议优先修复, 避免后续出现循环依赖与职责漂移.

### 3.2 App factory composition

`app/__init__.py:create_app` 采用显式的 composition 顺序, 将跨切面能力集中在 app factory 内完成注册:

- Settings -> `app.config`(单入口配置注入)
- ProxyFix(可信代理头解析)
- Security(session/cookie, CSRF, JWT/Login manager 等)
- Extensions(SQLAlchemy, Migrate, Cache, CORS 等)
- Blueprints(routes + API v1)
- Logging(structlog, 全局错误封套)
- Scheduler(可选启用, 通过文件锁保持单实例)

优点:

- 入口清晰, 可测性较好(允许注入 `settings` 并关闭 scheduler 初始化).
- 跨切面能力集中管理, 避免散落到业务代码.

关注点:

- `create_app` 在 scheduler 初始化异常时会继续启动应用(记录异常日志). 这是一种可用性优先的取舍, 但会带来 "任务未运行但服务可用" 的运行态差异, 需要运维侧有可观测性与告警口径配套.
- 全局 `@app.errorhandler(Exception)` 统一返回 JSON envelope, 会弱化 UI vs API 的边界差异. 若 UI 期望 HTML 错误页或 flash, 需要明确当前产品取舍, 或按 blueprint/Accept header 做分流.

### 3.3 Contract-first alignment

项目已在文档层面建立了 "contract-first" 的入口与约束:

- `docs/Obsidian/API/*-api-contract.md` 作为 API contract SSOT
- `docs/Obsidian/architecture/developer-entrypoint.md` 要求 "先更新 contract, 再写代码"
- 代码落点清晰: API HTTP 层 `app/api/v1/**`, 业务层 `app/services/**`, 数据层 `app/repositories/**`/`app/models/**`

建议持续保持:

- 任何 API 新增/变更都同时更新 contract 与对应 schema/resource, 并确保 `BaseResource.safe_call` 等封套一致性.

## 4. Risk analysis

### 4.1 Layer boundary erosion (repo imports service)

- 现状: `PartitionRepository` 通过 `PartitionStatisticsService` 获取分区信息.
- 风险: repositories 职责从 "数据访问" 漂移到 "业务计算/编排" 或 "服务复用", 容易引入:
  - 循环依赖(services->repositories 已是常态, 反向再引入会形成环)
  - 事务边界与错误语义不清晰(服务层口径被 repository 间接继承)
  - 测试困难(Repository 测试被迫依赖 Service 及其依赖)

### 4.2 Scheduler single-instance assumptions

- 现状: `app/scheduler.py` 通过 `userdata/scheduler.lock` 文件锁保证单进程运行, 并使用 SQLite jobstore.
- 风险: 多进程/多实例部署下, 需要明确 scheduler 的运行拓扑与支持范围(单机多 worker vs 多机). 如果未来扩展为多机, 文件锁与本地 SQLite jobstore 都需要重新评估.

### 4.3 Dual auth surface (Login + JWT)

- 现状: README 声明使用 Flask-Login 与 Flask-JWT-Extended.
- 风险: UI session 与 API token 的鉴权/授权口径可能出现分叉(例如 RBAC 判定点不一致, 或权限模型未统一封装), 建议以 "单一授权服务/策略层" 统一出口, 并在文档中明确.

## 5. Recommendations (prioritized)

### P0 (should fix soon)

1. 修复 repositories->services 反向依赖
   - 方向 A: 将 `PartitionStatisticsService.get_partition_info` 的数据访问部分下沉到 repository, service 仅做编排与对外返回组装.
   - 方向 B: 若 `get_partition_info` 本质是 read model 查询, 直接迁移为 `PartitionRepository.fetch_partition_info` 的纯查询实现, 删除对 service 的依赖.

### P1 (guardrails)

2. 增加分层依赖门禁(轻量即可)
   - 在 `scripts/ci/` 增加或复用现有脚本, 将本报告使用的 `rg` 扫描固化为 CI 失败条件, 防止边界回退.
   - 为 "允许的例外" 建立显式白名单文件, 避免口头约定导致漂移.

### P2 (clarify runtime semantics)

3. 明确 scheduler 失败语义与可观测口径
   - 补充 "scheduler 启动状态" 的健康检查/管理页展示/日志字段约定, 并在运维文档中定义告警条件.

4. 明确 UI vs API 的错误处理策略
   - 若统一 JSON envelope 是产品取舍, 建议在 docs/Obsidian/architecture 或 standards 中写明.
   - 若需要差异化, 建议按 blueprint/Accept header 分流错误处理器, 保持边界清晰.

## 6. Evidence (key locations)

- Layer-first 依赖边界 SSOT: `docs/Obsidian/architecture/module-dependency-graph.md`
- App factory: `app/__init__.py:create_app`
- API v1 blueprint 注册: `app/api/__init__.py:register_api_blueprints`
- 发现的边界破坏点: `app/repositories/partition_repository.py`
- Scheduler 单实例锁: `app/scheduler.py:_acquire_scheduler_lock`

