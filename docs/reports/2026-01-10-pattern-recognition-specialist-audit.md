# Code Pattern Audit (pattern-recognition-specialist)
> 状态: Draft
> 负责人: team
> 创建: 2026-01-10
> 更新: 2026-01-10
> 范围: `app/**`, `app/static/js/**`, `scripts/**`(仅用于模式与门禁抽样)
> 方法: 规范与约定抽样(含 `CLAUDE.md`) + 结构/命名/反模式检索(`rg`) + 大文件热点统计(`wc -l`) + 轻量重复片段扫描(Python/JS sliding window)

## 0. Executive summary

整体结论:

- 架构与代码组织呈现明显的 layer-first 取向: HTTP(routes/API) -> services -> repositories/models, 并在 docs/Obsidian 内有较完整的 SSOT 入口.
- 主要工程模式(Factory/Adapter/Coordinator/Service/Repository/Blueprint)清晰且一致, 适配多数据库的扩展路径明确.
- 发现 3 类需要关注的代码异味:
  - P0: repositories->services 的反向依赖(边界破坏信号).
  - P1: 少量 UI routes 未使用 `safe_route_call` 的一致性问题(与规范口径存在偏差).
  - P1: 大文件热点集中(尤其是 db adapters 与部分 JS views), 存在 "God module" 风险.

## 1. Pattern usage report

### 1.1 Application factory (Flask)

- 入口: `app/__init__.py:create_app`
- 特征: 统一配置注入(Settings), 扩展初始化, blueprint 注册, 全局错误封套, structlog, scheduler 组装.

### 1.2 Blueprint separation (UI vs API)

- UI: `app/routes/**`(按 domain 拆分)
- API v1: `app/api/v1/**`(Flask-RESTX, OpenAPI)
- 蓝图注册: `app/api/__init__.py:register_api_blueprints`

### 1.3 Service layer + Repository pattern

- Service 层: `app/services/**`(业务编排, write boundary, adapters 协调)
- Repository 层: `app/repositories/**`(read query 组装)
- Model 层: `app/models/**`(SQLAlchemy ORM)

### 1.4 Adapter + Factory (multi-db)

账号同步 adapters:

- Base: `app/services/accounts_sync/adapters/base_adapter.py`
- 实现: `app/services/accounts_sync/adapters/{mysql,postgresql,sqlserver,oracle}_adapter.py`
- Factory: `app/services/accounts_sync/adapters/factory.py`

容量采集 adapters:

- Base: `app/services/database_sync/adapters/base_adapter.py`
- 实现: `app/services/database_sync/adapters/{mysql,postgresql,sqlserver,oracle}_adapter.py`
- Factory: `app/services/database_sync/adapters/factory.py`

连接 adapters:

- Factory: `app/services/connection_adapters/connection_factory.py`
- 实现: `app/services/connection_adapters/adapters/*.py`

### 1.5 Coordinator/Orchestrator (flow orchestration)

- Accounts sync: `app/services/accounts_sync/coordinator.py` + `app/services/accounts_sync/accounts_sync_service.py`
- Capacity sync: `app/services/database_sync/coordinator.py` + `app/services/database_sync/database_sync_service.py`
- Table size: `app/services/database_sync/table_size_coordinator.py` + `app/services/database_sync/table_size_adapters/*`

### 1.6 Decorator-based authz + route safety

- 权限 decorators: `app/utils/decorators.py`
- 规范路由错误处理: `app/utils/route_safety.py:safe_route_call`(在多处 routes 内已采用)
- 说明入口: `CLAUDE.md` + `docs/Obsidian/standards/coding-standards.md`

## 2. Anti-patterns and code smells

### P0 - Layer boundary violation

- `app/repositories/partition_repository.py:19`
  - 现状: repository import `PartitionStatisticsService`
  - 影响: 破坏 repositories->services 的依赖方向, 提升循环依赖与职责漂移风险
  - 建议: 将 read model 查询下沉到 repository, 或将 `fetch_partition_info` 上移到 service 并让 service 调用 repo(保持 repo 纯数据访问)

### P1 - Route safety pattern inconsistency (UI routes)

抽样口径: 存在 `@*.route(...)` 但文件内未出现 `safe_route_call`.

命中(7 files):

- `app/routes/accounts/classifications.py`
- `app/routes/capacity/instances.py`
- `app/routes/databases/ledgers.py`
- `app/routes/main.py`
- `app/routes/partition.py`
- `app/routes/scheduler.py`
- `app/routes/tags/bulk.py`

备注:

- 其中部分为 "仅渲染模板/重定向/静态图标" 的简单路由, 可能属于事实上的例外.
- 但当前例外未在 standards 中显式声明, 容易导致后续新增路由在错误处理与日志口径上出现漂移.

建议:

- 要么: 将上述路由也统一包进 `safe_route_call`, 彻底消除例外.
- 要么: 在 standards 中增加明确例外规则(例如 "纯 render_template 且无 I/O" 可不包), 并提供最小模板.

### P1 - God module hotspots (static LOC proxy)

Python (top hotspots by `wc -l`):

- `app/services/accounts_sync/adapters/sqlserver_adapter.py` (1333)
- `app/services/accounts_sync/permission_manager.py` (1119)
- `app/services/aggregation/aggregation_service.py` (1007)
- `app/api/v1/namespaces/instances.py` (940)
- `app/tasks/capacity_aggregation_tasks.py` (903)
- `app/tasks/capacity_collection_tasks.py` (820)
- `app/settings.py` (696)
- `app/scheduler.py` (669)

JS (non-vendor hotspots by `wc -l`):

- `app/static/js/modules/views/instances/detail.js` (1983)
- `app/static/js/modules/views/accounts/account-classification/permissions/permission-policy-center.js` (1409)
- `app/static/js/modules/views/instances/list.js` (1302)
- `app/static/js/modules/views/tags/batch-assign.js` (1049)
- `app/static/js/modules/views/admin/scheduler/index.js` (959)

建议(原则性):

- 将 "domain logic" 从 view/controller 模块中抽出到 services/stores, view 只保留 wiring.
- 对 adapters 这种天然复杂模块, 优先按 "能力切片" 拆文件(连接/查询构造/权限解析/normalize), 而不是按函数随长.

### P2 - TODO/FIXME/HACK/XXX footprint

检索口径: `rg -n "TODO|FIXME|HACK|XXX" app scripts tests`.

- 总命中: 7
- 其中包含 1 处 vendor sourcemap 文件命中(`app/static/vendor/bootstrap/bootstrap.bundle.min.js.map`), 不属于项目自身技术债.
- 其余命中主要为脚本中的临时目录命名(`mktemp ... XXXX`)与少量 docstring 示例.

结论: 明确的 TODO/FIXME 技术债标记较少, 风格更偏 "直接修复或文档化" 而非堆 TODO.

## 3. Naming consistency analysis

命名守卫脚本:

- 执行: `./scripts/ci/refactor-naming.sh --dry-run`
- 结果: 0 处违规(脚本输出: "无需要替换的内容")

结论:

- Python/JS 的命名约束整体收敛, 并且已通过脚本形成可执行门禁.

## 4. Code duplication metrics (lightweight scan)

说明:

- 仓库未引入 `jscpd` 等重复检测工具, 本报告使用 sliding window 的轻量近似扫描作为替代.
- 该扫描更适合发现 "可抽公共骨架" 的重复, 不等价于语义重复.

### 4.1 Python duplication scan (app/*.py)

参数:

- files: 384
- lines: 57847
- window: 12 lines
- duplicate_windows_across_files: 146

高频重复片段主要集中在:

- 多数据库 adapter 的骨架一致性(例如 `table_size_adapters/{mysql,postgresql,sqlserver}_adapter.py`)
- 连接 adapters 的相似异常处理/返回结构
- export services 的相似导出流程(`app/services/files/*_export_service.py`)

建议:

- "骨架重复" 若是刻意保持一致(便于对齐与 diff), 可以接受, 但应通过 base class/mixin 提供最小公共约束(接口 + 共享校验), 避免未来漂移.
- export services 可以优先评估抽一个通用导出管线(字段映射 + writer), 以减少重复与错误口径漂移.

### 4.2 JS duplication scan (app/static/js/**/*.js, non-vendor)

参数:

- files: 99
- lines: 35833
- window: 18 lines
- duplicate_windows_across_files: 77

高频重复片段主要集中在:

- `app/static/js/modules/services/*_service.js` 的 HTTP 调用骨架高度一致
- 各 domain 的 modal 初始化骨架(`*/modals/*-modals.js`)

建议:

- 提供一个统一的 base service(fetch wrapper, error envelope, default headers), 各 service 仅声明 endpoint 与 payload mapping.
- 提供一个统一的 modal helper(打开/关闭/校验/回调约定), 以减少重复与 UI 口径漂移.

## 5. Recommended actions (prioritized)

1. P0: 修复 `app/repositories/partition_repository.py` 的 repositories->services 依赖反转.
2. P1: 明确 `safe_route_call` 的适用边界, 并消除 routes 层的 "隐式例外".
3. P1: 针对 top hotspots, 按 domain/能力切片拆分大文件(优先 adapters 与超大 JS views).
4. P2: 对高重复的 JS services/modals 抽公共基建, 同时保持命名守卫脚本可持续生效.
