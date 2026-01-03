# Instance Database Table Sizes(on-demand) Implementation Plan

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-02
> 更新: 2026-01-02
> 范围: instances 详情页(数据库容量 Tab), API v1 instances, 表容量采集与落库
> 关联: docs/standards/backend/api-response-envelope.md, docs/standards/backend/configuration-and-secrets.md, docs/standards/backend/database-migrations.md
>
> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在实例详情页的"数据库容量信息"列表中, 为每个 database 增加"表容量"按钮. 点击后打开模态框, 展示该 database 下各表的容量. 仅在用户点击"刷新"时采集远端数据, 本地仅保存最新快照(不保留历史).

**Architecture:** 新增本地表 `database_table_size_stats` 用于保存每个(instance_id, database_name, schema_name, table_name)的最新容量快照. GET 接口只读取快照, POST 刷新接口负责连接远端实例采集表容量并 upsert 快照, 同时清理已不存在的表记录. 前端复用 instances/detail 的 Grid.js 与 `UI.createModal`, 在数据库列表新增操作列与模态框.

**Tech Stack:** Flask, Flask-RESTX, SQLAlchemy, Alembic, Grid.js, Bootstrap modal

---

## Background

现状:

- instances 详情页已有"数据库容量信息" Tab, 通过 `GET /api/v1/instances/<id>/databases/sizes` 展示 database 容量.
- 用户需要进一步下钻到单个 database 的表级别容量, 且采集必须是手动触发.

问题:

- 缺少表级别容量的读模型与 UI 展示.
- 若直接每次打开模态框都实时采集, 会带来不可控的耗时与远端压力.

---

## Goals / Non-goals

Goals:

- 为每个 database 提供"查看表容量"入口(实例详情页, 数据库列表新增操作列).
- 模态框展示: table 名称 + 容量(size), 支持手动刷新.
- 本地只保存最新快照, 不保留历史记录.
- 尽可能复用既有模块: API v1(envelope + safe_call), connection factory, UI modal, Grid.js.

Non-goals:

- 不做定时任务采集(不接入 scheduler, 不自动刷新).
- 不做跨数据库的全量表容量聚合报表(仅实例详情页下钻).
- 不做容量趋势图(因为无历史).

---

## Design Options

Option A(Recommended): "快照读取 + 显式刷新"

- 打开模态框: 调用 GET 读取本地快照并展示.
- 点击刷新: 调用 POST 采集远端表容量并 upsert 快照, 返回最新列表后刷新 UI.
- Pros: UX 简洁, 与当前 database sizes 的 read model 类似, 可复用大量模块.
- Cons: 表数量很大时, 单次 refresh 可能较慢或触发请求超时.

Option B: "异步会话 + 轮询"

- 刷新触发异步任务, 返回 session_id, 前端轮询任务结果或跳转 sessions 页面.
- Pros: 解决超时与长任务问题.
- Cons: 复杂度高, 需要新增会话模型与 UI 交互.

结论: 先落地 Option A, 若后续出现超时或性能瓶颈, 再升级为 Option B.

---

## Data Model

新增表: `database_table_size_stats` (仅保存最新快照, 无历史分区).

建议字段:

- `id`: BigInteger PK
- `instance_id`: Integer FK -> `instances.id`, index
- `database_name`: String(255), index
- `schema_name`: String(255), not null
- `table_name`: String(255), not null
- `size_mb`: BigInteger, not null (total size, MB)
- `data_size_mb`: BigInteger, nullable (MB)
- `index_size_mb`: BigInteger, nullable (MB)
- `row_count`: BigInteger, nullable (optional, best-effort)
- `collected_at`: DateTime(tz), not null (snapshot time)
- `created_at` / `updated_at`: DateTime(tz), not null

约束与索引:

- Unique: `(instance_id, database_name, schema_name, table_name)` (保证 upsert 的 key 稳定)
- Index: `(instance_id, database_name)` (列表查询)
- Index: `(instance_id, database_name, size_mb desc)` (按容量排序)

清理策略:

- 每次 refresh 后, 删除同一 `(instance_id, database_name)` 下不在本次结果中的记录.
- 这样快照始终反映"当前表集合", 不会残留已删除表.

---

## Backend APIs

### 1) Read snapshot

Route:

- `GET /api/v1/instances/<int:instance_id>/databases/<string:database_name>/tables/sizes`

Query params:

- `schema_name`: optional, like filter
- `table_name`: optional, like filter
- `limit`: default 200, max 2000
- `offset`: default 0

Response `data`:

```json
{
  "total": 2,
  "limit": 200,
  "offset": 0,
  "collected_at": "2026-01-02T10:00:00+08:00",
  "tables": [
    {
      "schema_name": "public",
      "table_name": "users",
      "size_mb": 12,
      "data_size_mb": 9,
      "index_size_mb": 3,
      "row_count": 1000,
      "collected_at": "2026-01-02T10:00:00+08:00"
    }
  ]
}
```

Notes:

- 仅返回本地快照, 不连接远端.
- `collected_at` 建议返回为本次列表内的 max(collected_at), 便于 UI 展示"最后刷新时间".

### 2) Refresh snapshot(on-demand collection)

Route:

- `POST /api/v1/instances/<int:instance_id>/databases/<string:database_name>/tables/sizes/actions/refresh`

Request body:

- empty body is ok.

Response `data`:

- 同 GET, 额外建议返回:
  - `saved_count`: upsert 数量
  - `deleted_count`: 清理数量
  - `elapsed_ms`: 采集耗时

Error cases(expected):

- 404: instance 不存在
- 409: 无法连接远端, 或远端拒绝访问, 或 database 不存在
- 504/500: 超时或未知异常(由统一错误封套输出)

Envelope:

- MUST: 使用 `BaseResource.safe_call()` + `self.success()` 输出统一封套.
- MUST NOT: 手写 `{success: ..., message: ...}`.

---

## Collection Logic

核心目标: 从远端实例采集指定 database 的 table 级别容量.

建议模块拆分(尽量复用 capacity_sync 的结构):

- `app/services/database_sync/table_size_adapters/*`: 按 db_type 实现 table size SQL.
- `app/services/database_sync/table_size_coordinator.py`: 组织连接, 采集, persistence, cleanup.

连接策略:

- MySQL: 复用实例连接, 从 `information_schema.TABLES` 按 `TABLE_SCHEMA = :database_name` 读取.
- SQL Server: 复用实例连接, 在指定 database 上下文执行(建议使用 `DB_NAME()` + three-part name 或 `USE [db]` 的安全版本).
- PostgreSQL: 需要连接到目标 database 才能读取 relation sizes. 建议创建临时连接(override dbname), 用完即断开.
- Oracle: 延续现有容量同步逻辑: "database_name" 对应 tablespace, inventory/capacity 都基于 `dba_data_files` 的 tablespace 聚合. table sizes 以 `database_name = tablespace_name`, 直接使用 `dba_segments` 过滤 `segment_type IN ('TABLE', 'TABLE PARTITION', 'TABLE SUBPARTITION')`, 按 `(owner, segment_name)` 聚合 `bytes` 计算 size, 映射 `schema_name = owner`, `table_name = segment_name`. 不做降级方案, 依赖 Oracle 账号具备 `DBA_SEGMENTS` 读取权限(现网已具备).

安全与防御:

- 本期不新增独立 timeout/limit 配置, 不引入 table 数量超限处理(包含: UI 过滤采集或 top N + truncated).
- 超时/长耗时风险作为已知约束, 由用户显式触发; 若成为问题, 再升级 Option B(异步会话 + 轮询).

---

## Frontend(UI)

入口位置:

- 页面: `app/templates/instances/detail.html` 的数据库容量 Grid.
- 变更: 在数据库列表列定义 `buildDatabaseSizesGridColumns()` 增加"操作"列.

操作列按钮:

- 文案: "表容量"
- 属性:
  - `data-action="open-table-sizes"`
  - `data-database-name="..."` (需要 escape + encode)

模态框:

- Template: 在 `app/templates/instances/detail.html` 末尾新增 modal, 复用 `components/ui/modal.html`.
- Header: 显示 database 名称 + 最后刷新时间.
- Body: 一个 Grid.js 列表, 展示 tables.
- Footer:
  - "刷新"按钮(确认按钮, `data-modal-confirm`)
  - "关闭"按钮(取消按钮, `data-modal-cancel`)

JS 交互:

- Service: 扩展 `app/static/js/modules/services/instance_management_service.js`
  - `fetchDatabaseTableSizes(instanceId, databaseName, params)`
  - `refreshDatabaseTableSizes(instanceId, databaseName)`
- View:
  - 推荐新增文件 `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js`
  - 在 `app/static/js/modules/views/instances/detail.js` 初始化该 modal controller, 并在 `bindTemplateActions()` 增加 `open-table-sizes` 的 case.

UI 行为:

- 打开模态框:
  - 先渲染 loading state
  - 调用 GET 读取快照并填充 Grid
- 点击刷新:
  - modal confirm 进入 loading
  - 调用 POST refresh
  - 成功后刷新 Grid, 更新 "collected_at"
  - 失败 toast error, 保持原快照不清空

---

## Permissions

不新增权限, 权限策略复用现有 instances "同步容量" 的口径:

- GET: 维持现有 `api_permission_required("view")`.
- POST refresh: 复用现有 "同步容量" 权限校验 + `require_csrf`.
- 前端: 可先不做按钮级别权限控制(与现有 "同步容量" 一致), 交由 API 返回 403.

---

## Testing

后端单测:

- contract test: `tests/unit/routes/test_api_v1_instances_contract.py`
  - 新增 `test_api_v1_instances_database_table_sizes_snapshot_contract`
  - 新增 `test_api_v1_instances_database_table_sizes_refresh_contract`(mock adapter)
- repository/service test:
  - 验证分页, filter, order.
  - refresh: upsert + cleanup 行为(建议用 sqlite in-memory + session).

前端测试:

- 当前仓库无 JS 单测体系, 只做手工回归 + eslint.

手工回归路径:

- instances 详情页 -> 数据库容量信息 -> 点击某一行"表容量" -> 查看快照 -> 点击刷新 -> 列表更新.

---

## Rollout / Config

- 本功能不新增配置项/开关.

---

## Implementation Tasks(TDD)

### Task 1: Add DB migration + model

**Files:**
- Create: `app/models/database_table_size_stat.py`
- Create: `migrations/versions/<timestamp>_add_database_table_size_stats.py`

**Step 1: Create model file**

- Define `DatabaseTableSizeStat` with constraints/indexes.

**Step 2: Generate migration**

Run: `flask db revision -m "add database_table_size_stats" --autogenerate`

Expected: new revision created, includes create_table + indexes + unique constraint.

**Step 3: Smoke test migration**

Run: `flask db upgrade`

Expected: success.

### Task 2: Add types for query/result DTO

**Files:**
- Create: `app/types/instance_database_table_sizes.py`

**Step 1: Add dataclasses**

- `InstanceDatabaseTableSizesQuery`
- `InstanceDatabaseTableSizeEntry`
- `InstanceDatabaseTableSizesResult`

### Task 3: Add repository(read model)

**Files:**
- Create: `app/repositories/instance_database_table_sizes_repository.py`

**Step 1: Implement list query**

- Filter by `instance_id` + `database_name`.
- Support optional `schema_name`/`table_name` fuzzy match.
- Order by `size_mb desc`, then name.
- Return `total/limit/offset/collected_at/tables`.

### Task 4: Add service layer

**Files:**
- Create: `app/services/instances/instance_database_table_sizes_service.py`

**Step 1: Wire repository**

- `fetch_snapshot(options)`.

### Task 5: Add table size adapters + coordinator

**Files:**
- Create: `app/services/database_sync/table_size_adapters/base_adapter.py`
- Create: `app/services/database_sync/table_size_adapters/mysql_adapter.py`
- Create: `app/services/database_sync/table_size_adapters/postgresql_adapter.py`
- Create: `app/services/database_sync/table_size_adapters/sqlserver_adapter.py`
- Create: `app/services/database_sync/table_size_adapters/oracle_adapter.py`
- Create: `app/services/database_sync/table_size_coordinator.py`

**Step 1: Define adapter interface**

- `fetch_table_sizes(instance, connection, database_name) -> list[dict]`.

**Step 2: Implement MySQL query**

- `information_schema.TABLES` aggregate.

**Step 3: Implement PostgreSQL query**

- connect to target db and use `pg_total_relation_size`.

**Step 4: Implement SQL Server query**

- use sys tables to compute reserved pages.

**Step 5: Implement persistence**

- Upsert rows by unique key.
- Cleanup removed tables.

### Task 6: Add API v1 endpoints

**Files:**
- Modify: `app/api/v1/namespaces/instances.py`
- Create: `app/routes/instances/restx_models/instance_database_table_sizes.py` (or extend existing models file)

**Step 1: Add GET resource**

- `/api/v1/instances/<id>/databases/<database_name>/tables/sizes`

**Step 2: Add POST refresh resource**

- `/api/v1/instances/<id>/databases/<database_name>/tables/sizes/actions/refresh`

**Step 3: Add contract tests**

Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_contract.py -v`

Expected: PASS.

### Task 7: Add frontend service methods

**Files:**
- Modify: `app/static/js/modules/services/instance_management_service.js`

**Step 1: Add GET/POST wrappers**

- `fetchDatabaseTableSizes`
- `refreshDatabaseTableSizes`

### Task 8: Add modal markup and JS controller

**Files:**
- Modify: `app/templates/instances/detail.html`
- Create: `app/static/js/modules/views/instances/modals/database-table-sizes-modal.js`
- Modify: `app/static/js/modules/views/instances/detail.js`

**Step 1: Add modal template**

- Add `#tableSizesModal` with body container and footer buttons.

**Step 2: Wire JS**

- Add action button in database grid columns.
- Add click handler to open modal with payload `{ database_name }`.
- Implement modal onOpen: call GET and render grid.
- Implement modal onConfirm(refresh): call POST and reload grid.

### Task 9: Add CSS polish

**Files:**
- Modify: `app/static/css/pages/instances/detail.css`

**Step 1: Add modal layout helpers**

- Make table list scrollable, keep header sticky(optional).

### Task 10: Verification gates

Run:

- `make format`
- `make typecheck`
- `uv run pytest -m unit`
- `./scripts/ci/eslint-report.sh quick` (if JS changed)
