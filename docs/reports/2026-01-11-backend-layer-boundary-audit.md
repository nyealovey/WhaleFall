# Backend Layer Boundary Audit (2026-01-11)
> 状态: Draft
> 负责人: team
> 创建: 2026-01-11
> 更新: 2026-01-11
> 范围: `app/**`(routes/api/tasks/services/repositories/models/forms/views/utils/types/constants) + 后端分层标准(`docs/Obsidian/standards/backend/layer/**`)
> 方法: 以 layer standards 为口径 + 静态扫描(`rg`) + 关键文件抽样阅读 + 现有 CI guards 执行核对

## 0. 结论摘要

结论: 当前代码存在明确的分层边界跨越问题, 且主要集中在 4 个区域.

- P0: `app/services/**` 仍存在大量绕过 Repository 的数据访问与查询组装(当前命中 `61` 次 `.query`, `21` 次 `db.session.query/execute`), 但 `InstanceWriteService`/`SyncSessionService` 已完成一次下沉整改.
- P0: `app/tasks/**` 已消除 `Model.query` 与 `db.session.query/execute` 直用(命中 0), 且 `capacity_*_tasks.py` 已拆分为薄入口 + runner service(调度入口显著变薄).
- P0: `app/forms/**` 已消除对 models/services/repositories 的直接依赖与查库(命中 0). 原 `app/forms/handlers/**` 已迁移为 `app/views/form_handlers/**`, 由 Views 显式绑定 `service_class`.
- P1: `app/utils/**` 出现 DB 事务/写入(例如 `database_batch_manager.py`), 与 utils-layer-standards 存在边界冲突. 其中事务边界与 worker 入口已确认迁移到 `app/infra/**`(见 5.1).

补充: 写边界相关 CI guard 当前通过, 说明 "commit 位置" 受控, 但不代表 "分层边界" 正常.

- `./scripts/ci/db-session-route-write-guard.sh`: 通过
- `./scripts/ci/db-session-commit-services-drift-guard.sh`: 通过
- `./scripts/ci/db-session-write-boundary-guard.sh`: 通过

进度跟踪: 见 `docs/reports/2026-01-11-backend-layer-boundary-audit-progress.md`.

## 1. 口径与依赖方向(SSOT)

本报告以以下 standards 为口径:

- 后端分层总览: `../Obsidian/standards/backend/layer/README.md`
- 10 个层标准:
  - Routes: `../Obsidian/standards/backend/layer/routes-layer-standards.md`
  - API v1: `../Obsidian/standards/backend/layer/api-layer-standards.md`
  - Tasks: `../Obsidian/standards/backend/layer/tasks-layer-standards.md`
  - Services: `../Obsidian/standards/backend/layer/services-layer-standards.md`
  - Repository: `../Obsidian/standards/backend/layer/repository-layer-standards.md`
  - Models: `../Obsidian/standards/backend/layer/models-layer-standards.md`
  - Forms/Views: `../Obsidian/standards/backend/layer/forms-views-layer-standards.md`
  - Utils: `../Obsidian/standards/backend/layer/utils-layer-standards.md`
  - Constants: `../Obsidian/standards/backend/layer/constants-layer-standards.md`
  - Types: `../Obsidian/standards/backend/layer/types-layer-standards.md`
- 写操作事务边界: `../Obsidian/standards/backend/write-operation-boundary.md`

依赖方向(概览)以 `layer/README.md` 的 mermaid 图为准, 核心约束可简化为:

- Routes/API/Tasks: 只做入口与编排, 调用 Services, 不直接查库.
- Services: 业务编排 + 事务边界策略, 数据访问必须通过 Repositories.
- Repositories: 负责 ORM Query 组装与数据访问细节, 不做业务编排, 不 commit.
- Models: 负责 ORM 映射与最小方法, 避免堆叠业务与复杂查询.
- Forms/Views/Utils/Types/Constants: 各自保持纯度, 不反向依赖业务层, 不触碰数据库(除明确允许的事务边界入口例外).

## 2. 范围与方法

### 2.1 扫描范围

- `app/routes/**`
- `app/api/v1/**`
- `app/tasks/**`
- `app/services/**`
- `app/repositories/**`
- `app/models/**`
- `app/forms/**`
- `app/views/**`
- `app/utils/**`
- `app/constants/**`
- `app/types/**`

### 2.2 扫描方法与命令(摘要)

- 分层边界关键扫描:

```bash
rg -n "\\bfrom app\\.(models|repositories)\\b|\\bimport app\\.(models|repositories)\\b|Model\\.query|db\\.session" app/routes
rg -n "\\bfrom app\\.(models|routes)\\b|db\\.session|\\.query\\b" app/api/v1
rg -n "db\\.session\\.(commit|rollback)\\(|\\.query\\b" app/tasks
rg -n "db\\.session\\.(commit|rollback)\\(|db\\.session\\.(query|execute)\\b|\\.query\\b" app/services
rg -n "db\\.session\\.commit\\(" app/repositories
rg -n "from app\\.(services|repositories)\\." app/models
rg -n "from app\\.(models|services|repositories)|db\\.session|\\.query\\b" app/forms app/views
rg -n "from app\\.(models|services|repositories|routes|api)|db\\.session" app/utils
```

- 写边界 guard(现状核对):

```bash
./scripts/ci/db-session-route-write-guard.sh
./scripts/ci/db-session-commit-services-drift-guard.sh
./scripts/ci/db-session-write-boundary-guard.sh
```

## 3. 分层对照结果(按 10 层)

### 3.1 Routes (`app/routes/**`)

结论: 基本满足 "不直接查库", 但 `safe_route_call` 覆盖不完整(与 routes-layer-standards 的 MUST 冲突).

- DB 访问: 未发现 `Model.query`/`db.session` 直接使用(扫描命中为 0).
- `safe_route_call` 覆盖: 路由总数约 `26`(按 `@*.route(` 粗略统计), `safe_route_call` 命中 `13`.
- 典型未使用 `safe_route_call` 的文件/路由:
  - `app/routes/main.py:15`(多处 route 均未包裹)
  - `app/routes/tags/bulk.py:16`
  - `app/routes/scheduler.py:14`
  - `app/routes/partition.py:14`
  - `app/routes/databases/ledgers.py:45`
  - `app/routes/capacity/instances.py:17`

### 3.2 API v1 (`app/api/v1/**`)

结论: 未发现直接 `.query`/`db.session`, 但存在 API 依赖 models 的边界漂移.

- 已整改: API v1 namespaces 不再 import `app.models.*`(扫描命中 0).
- 风险(历史原因): API 层持有 ORM 实体会诱发端点层承担更多数据逻辑, 并使 contract/DTO 边界模糊.

### 3.3 Tasks (`app/tasks/**`)

结论: 已完成 "禁止 query/execute" 的边界整改(Tasks 层命中为 0), 且 capacity 相关任务已拆分为薄入口 + runner.

- 直接查库(按门禁口径扫描): 0 命中
- 文件规模(抽样):
  - `app/tasks/capacity_collection_tasks.py` 约 150 行(调度入口)
  - `app/tasks/capacity_aggregation_tasks.py` 约 215 行(调度入口)
  - `app/tasks/accounts_sync_tasks.py` 约 281 行(仍偏厚)
- app context: 多数任务含 `with app.app_context():`(符合 tasks-layer-standards 的强约束).

### 3.4 Services (`app/services/**`)

结论: 边界漂移最严重区域. Services 大量绕过 Repository, 直接使用 `Model.query`/`db.session`.

- `.query` 命中: `61`(粗略统计).
- 典型高频文件(按命中数排序, 仅列 top):
  - `app/services/instances/batch_service.py`(11)
  - `app/services/aggregation/aggregation_tasks_read_service.py`(7)
  - `app/services/accounts/account_classifications_write_service.py`(7)
  - `app/services/aggregation/instance_aggregation_runner.py`(4)
  - `app/services/aggregation/database_aggregation_runner.py`(4)
- 典型越界样例:
  - `app/services/instances/batch_service.py`(批量操作内含多处 `*.query`)
  - `app/services/tags/tags_bulk_actions_service.py`(`Instance.query`/`Tag.query`)
- 事务回滚漂移(违反 write-operation-boundary 的 "services 内不得 rollback 整个请求事务"):
  - `app/services/dashboard/dashboard_overview_service.py:31`
  - `app/services/statistics/log_statistics_service.py:44`
  - `app/services/tags/tag_write_service.py:78`
- `db.session.commit` 漂移: 未发现(现有 CI guard 也验证为 0).

### 3.5 Repositories (`app/repositories/**`)

结论: commit 边界符合, 未发现明显反向依赖 services/routes/api.

- `db.session.commit`: 0 处命中.
- 反向依赖扫描: 未发现 `from app.services`/`from app.routes`/`from app.api`.

### 3.6 Models (`app/models/**`)

结论: 存在少量 "查询工具方法" 聚集在 model 上的倾向, 会加速上层绕过 Repository.

- `.query`/`db.session` 命中(抽样):
  - `app/models/tag.py:124` (`Tag.query...`)
  - `app/models/sync_session.py:182` (`SyncSession.query...`)
  - `app/models/unified_log.py:162` (含 `db.session.query(...)`)

### 3.7 Forms/Views (`app/forms/**`, `app/views/**`)

结论: Forms 层已按 standards 完成去 DB/去跨层依赖整改, Views 通过显式 `service_class` 绑定表单 handler.

- Forms: `app/forms/**` 不再 import `app.models/app.services/app.repositories`, 也不再出现 `Model.query/db.session`
- Views: 新增 `app/views/form_handlers/**` 承载表单 load/upsert/context 编排, 并由 `app/views/*_forms.py` 显式绑定 `service_class`
- Forms definitions: `scheduler_job` 等定义不再依赖 service 类型, 仅保留字段定义与模板配置

### 3.8 Utils (`app/utils/**`)

结论: 出现 DB 事务与写入, 与 utils-layer-standards 存在边界冲突, 同时与写边界标准存在口径不一致.

- `db.session` 命中:
- `app/infra/route_safety.py:146` (commit)
- `app/infra/logging/queue_worker.py:184` (commit)
  - `app/utils/database_batch_manager.py:151` (begin/begin_nested/rollback)

### 3.9 Constants (`app/constants/**`)

结论: 基本符合. 未发现跨层依赖(仅内部 constants 互相依赖).

### 3.10 Types (`app/types/**`)

结论: 已按方案 B 清除 `app/types/**` 对 `app.models.*` 的引用(包括 `TYPE_CHECKING`), 改为 `Protocol`/弱类型表达最小接口.

- 已落地变更(2026-01-11):
  - `app/types/credentials.py`
  - `app/types/tags.py`

## 4. 发现清单(按严重度)

### P0

- Services 数据访问绕过 Repository:
  - 现象: `Model.query`/`db.session.query/execute/add/delete` 出现在 `app/services/**`.
  - 风险: 查询与数据访问细节无法复用, 事务语义分散, 容易形成循环依赖与测试困难.
- Tasks 入口过厚(已修复 query/execute 直用, 仍需变薄):
  - 现象: `capacity_*_tasks.py` 已拆分为薄入口 + runner service, 但仍存在个别任务(例如 `accounts_sync_tasks.py`)文件规模偏大.
  - 风险: 业务逻辑沉积在调度入口, 导致复用困难与回归风险上升.
- Forms 层越界(已修复):
  - 现象: 过去 `app/forms/**` 直接依赖 models/services/repositories 并出现 `Model.query`.
  - 风险: UI 表单层成为隐形业务层, 难以做一致的事务与错误口径, 也难以测试.

### P1

- API v1 依赖 models(已修复):
  - 现象: 过去 `app/api/v1/**` import `app.models.*`.
  - 风险: 端点层更容易持有 ORM 实体并逐步承担数据逻辑.
- Utils DB 访问与事务:
  - 现象: `app/utils/**` 出现 `db.session.*`.
  - 风险: 工具层反向绑定 infra 能力, 容易与业务层耦合并引入循环导入.

### P2

- Models 内含查询工具方法:
  - 现象: `app/models/**` 出现 `Model.query`/`db.session.query`.
  - 风险: 上层倾向直接调用 model 静态方法, 绕过 repository.
- Types 在 `TYPE_CHECKING` 下引用 models:
  - 现象: 过去 `app/types/*.py` 在 `TYPE_CHECKING` 分支引用 `app.models.*`.
  - 风险: 标准口径不一致, 导致评审争议与门禁难以统一.
  - 状态: 已按方案 B 修复(见 5.3).

## 5. 标准冲突与决策点(已确认)

说明: 本节用于记录 standards 文案冲突与收敛决策. 以下口径已于 2026-01-11 完成确认, 并已回写到 SSOT standards(见各小节 "已落地变更").

### 5.1 Utils 层标准 vs 写边界标准(已确认)

- 背景: `utils-layer-standards` 禁止 utils 触 DB, 但 `write-operation-boundary` 需要存在事务边界入口与 worker 入口.
- 确认决策: 方案 A. 将事务边界/worker 类文件移出 utils, 放入 `app/infra/**`, 保持 utils 纯净.
- 已落地变更(2026-01-11):
  - `app/infra/route_safety.py`
  - `app/infra/logging/queue_worker.py`

### 5.2 Tasks 层 "禁止 db.session" vs 写边界允许 tasks commit(已确认)

- 背景: `tasks-layer-standards` 需要与 `write-operation-boundary` 对齐, 同时保持 Tasks 层 "薄入口" 与 "不直接查库" 的边界.
- 确认决策: tasks-layer-standards 收敛口径为 "允许 commit/rollback, 但禁止 query/execute 与业务逻辑堆叠".
- 已落地变更(2026-01-11):
  - `docs/Obsidian/standards/backend/layer/tasks-layer-standards.md`

### 5.3 Types MUST NOT 依赖 models vs `TYPE_CHECKING` 引用(已确认)

- 观察: `types-layer-standards` 写了 MUST NOT 依赖 models, 但此前 `app/types/*.py` 存在 `TYPE_CHECKING` 下的 model 引用.
- 确认决策: 方案 B. 不允许 `TYPE_CHECKING` 引用 models, 统一改为 `Protocol`/弱类型, 并补充示例.
- 已落地变更(2026-01-11):
  - `docs/Obsidian/standards/backend/layer/types-layer-standards.md`
  - `app/types/credentials.py`
  - `app/types/tags.py`
- 团队确认结果: 已确认

## 6. 整改路线图(建议)

建议按 P0 优先级拆分为多 PR 推进, 每个 PR 只收口一个域/一个层, 以降低回归风险:

1. Forms/Views 收口: 已完成
   - `app/forms/**` 已不再 import `app.models/app.services/app.repositories`, 且不再出现 `.query/db.session`
   - 原 `app/forms/handlers/**` 已迁移为 `app/views/form_handlers/**`
2. Tasks 收口: 已完成
   - 已完成: tasks 内 `.query/db.session.query/execute` 下沉为 Service/Repository 调用
3. Services 逐域迁移到 Repository: 部分完成
   - 已完成: `InstanceWriteService`/`SyncSessionService` 删除 `.query/db.session.query`, 下沉到 repositories
   - 待完成: 其他高频 service(例如 `instances/batch_service.py`) 的逐域下沉
4. API v1 去 models 依赖: 已完成
   - 端点层只持有 DTO/primitive, ORM 相关在 service 内部消化.
5. 标准冲突收敛 + guard 门禁化: 已完成
   - 明确 Tasks/Utils/Types 的例外口径, 并将规则固化为 scripts/ci guards.

## 7. 证据与数据来源(关键摘要)

- `.query` 命中数:
  - `app/services/**`: 61
  - `app/tasks/**`: 0
  - `app/forms/**`: 0
  - `app/models/**`: 14
- tasks 文件行数:
  - `app/tasks/capacity_aggregation_tasks.py`: 903
  - `app/tasks/capacity_collection_tasks.py`: 820
  - `app/tasks/accounts_sync_tasks.py`: 281
- infra/utils `db.session` 命中:
  - `app/utils/database_batch_manager.py`: 8
  - `app/infra/route_safety.py`: 4
  - `app/infra/logging/queue_worker.py`: 3
