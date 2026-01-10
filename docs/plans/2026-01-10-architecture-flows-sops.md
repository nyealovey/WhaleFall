# Architecture Flows SOP Notes Implementation Plan (Capability-first)

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 把 `docs/Obsidian/architecture/flows/` 从"索引"补齐为 7 份可执行 SOP(含流程图/入口代码/常见排障与自查命令), 聚焦产品核心能力: 登录 + 会话 + 3 个定时任务(账户同步/容量同步/聚合统计) + 标签 bulk + 自动分类.

**Architecture (Approach A):** 每份 SOP 按"业务能力"拆分, 同一份文档同时覆盖:
- 定时触发: scheduler job
- 手动触发: API action endpoint(或 UI 行为触发)

每份文档统一结构:
- 适用场景/范围
- 触发入口(定时/手动)
- Mermaid 流程图(一张主流程 + 需要时补关键分支)
- 代码入口(路由/服务/task/coordinator/model)
- 可复制复现(curl/最小输入)
- 常见 message_code + 触发点
- 自查命令(rg/SQL)
- 相关 standards/reference/API contract

**Tech Stack:** Obsidian Markdown(YAML frontmatter + wikilinks + callouts) + Mermaid + `rg` + `curl` + SQL.

---

## Task 1: Create flow note `login.md`

**Files:**
- Create: `docs/Obsidian/architecture/flows/login.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: frontmatter + SOP 骨架**

**Step 2: Mermaid(2 张)**

- Web 登录(页面): `/auth/login` -> `LoginService` -> session cookie
- API 登录: `GET /api/v1/auth/csrf-token` -> `POST /api/v1/auth/login` -> cookie + JWT

**Step 3: 代码入口 + rg**

至少包含:
- `app/routes/auth.py`
- `app/services/auth/login_service.py`
- `app/api/v1/namespaces/auth.py`
- `app/utils/decorators.py`(`require_csrf`)
- `app/api/v1/resources/decorators.py`(`api_login_required`)

**Step 4: 可复制复现**

复用 `[[reference/examples/api-v1-cookbook]]` 的最小 curl, 只保留关键步骤并链接回 cookbook.

**Step 5: 常见 message_code**

至少列:
- `CSRF_MISSING`, `CSRF_INVALID`
- `AUTHENTICATION_REQUIRED`
- `INVALID_CREDENTIALS`, `ACCOUNT_DISABLED`, `RATE_LIMIT_EXCEEDED`

---

## Task 2: Create flow note `sync-session.md` (batch async session as a product feature)

**Files:**
- Create: `docs/Obsidian/architecture/flows/sync-session.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: frontmatter + SOP 骨架**

scope 要明确: `SyncSession/SyncInstanceRecord` 是批量异步能力的统一观测面, 是 accounts/capacity/aggregation 等流程的共同依赖.

**Step 2: Mermaid(2 张)**

- 统一会话生命周期: create -> add records -> start/complete/fail -> terminal -> 查询/取消
- "后台线程触发"通用模式: request -> prepare(session_id) -> response -> launch thread -> update records

**Step 3: 入口代码与 contract**

至少包含:
- contract: `docs/Obsidian/API/sessions-api-contract.md`
- models: `app/models/sync_session.py`, `app/models/sync_instance_record.py`
- service: `app/services/sync_session_service.py`
- API: `app/api/v1/namespaces/sessions.py`
- Web UI:
  - route: `app/routes/history/sessions.py` (`/history/sessions`)
  - template: `app/templates/history/sessions/sync-sessions.html`
  - JS: `app/static/js/modules/views/history/sessions/sync-sessions.js` + modal/detail scripts
  - async feedback helper(关联 resultUrl 与 toast 口径): `app/static/js/modules/ui/async-action-feedback.js`
- cleanup: `app/tasks/log_cleanup_tasks.py`

**Step 4: 自查 SQL**

至少包含:
- 按 `session_id` 查失败实例记录
- 最近 24h failed session 列表(按 `sync_category` 分组)

**Step 5: 常见 message_code**

至少列:
- `SYNC_DATA_ERROR`, `SNAPSHOT_MISSING`, `PERMISSION_FACTS_MISSING`

---

## Task 3: Create flow note `accounts-sync.md` (scheduled + manual)

**Files:**
- Create: `docs/Obsidian/architecture/flows/accounts-sync.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: 定义范围与触发入口**

- 定时任务: scheduler job `sync_accounts` -> `app/tasks/accounts_sync_tasks.py:sync_accounts`
- 手动触发:
  - `POST /api/v1/instances/actions/sync-accounts`(后台全量, 返回 `session_id`)
  - `POST /api/v1/instances/{instance_id}/actions/sync-accounts`(单实例, 同步返回 result)

**Step 2: Mermaid(1-2 张)**

- 主流程: trigger -> create session -> per instance coordinator -> inventory -> permission snapshot -> write models -> update record -> complete/fail

**Step 3: 代码入口清单**

至少包含:
- contract: `docs/Obsidian/API/instances-api-contract.md`
- API: `app/api/v1/namespaces/instances_accounts_sync.py`
- task: `app/tasks/accounts_sync_tasks.py`
- actions service: `app/services/accounts_sync/accounts_sync_actions_service.py`
- coordinator: `app/services/accounts_sync/coordinator.py`
- permission manager: `app/services/accounts_sync/permission_manager.py`
- models(按实际落库): `app/models/instance_account.py`, `app/models/account_permission.py`, `app/models/account_change_log.py`
- Web UI(手动触发入口):
  - template: `app/templates/instances/detail.html` (`data-action="sync-accounts"`)
  - JS: `app/static/js/modules/views/instances/detail.js`
  - JS service: `app/static/js/modules/services/instance_management_service.js`

**Step 4: 常见 message_code + 触发点**

至少列:
- `DATABASE_CONNECTION_ERROR`(连接失败, 视具体抛出点)
- `SYNC_DATA_ERROR`(数据回填缺失等)
- `SNAPSHOT_MISSING`(下游读取 v4 snapshot 时)

**Step 5: 自查命令**

- `rg` 定位 action/task 入口与阶段日志
- SQL: 按 `session_id` 查失败实例, 按 `instance_id` 查最近的权限/账户变更

---

## Task 4: Create flow note `capacity-sync.md` (scheduled + manual)

**Files:**
- Create: `docs/Obsidian/architecture/flows/capacity-sync.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: 定义范围与触发入口**

- 定时任务: scheduler job `collect_database_sizes` -> `app/tasks/capacity_collection_tasks.py:collect_database_sizes`
- 手动触发: `POST /api/v1/instances/{instance_id}/actions/sync-capacity`

**Step 2: Mermaid**

- 主流程: inventory -> collect -> save stats -> update instance totals -> trigger daily aggregation(best effort) -> session record update

**Step 3: 代码入口**

至少包含:
- contract: `docs/Obsidian/API/instances-api-contract.md`
- API: `app/api/v1/namespaces/instances.py`(sync-capacity action)
- task: `app/tasks/capacity_collection_tasks.py`
- service(action): `app/services/capacity/instance_capacity_sync_actions_service.py`
- coordinator/adapters: `app/services/database_sync/**`
- models:
  - `app/models/database_size_stat.py`
  - `app/models/instance_size_stat.py`
  - (optional) `app/models/database_table_size_stat.py`
- Web UI(手动触发入口):
  - template: `app/templates/instances/detail.html` (`data-action="sync-capacity"`)
  - JS: `app/static/js/modules/views/instances/detail.js`
  - JS service: `app/static/js/modules/services/instance_management_service.js`

**Step 4: 常见 message_code**

至少列:
- `DATABASE_CONNECTION_ERROR`, `SYNC_DATA_ERROR`

**Step 5: 自查 SQL**

- 某实例最近 N 天 `database_size_stats`/`instance_size_stats`
- `database_table_size_stats` 快照自查(如该能力已启用)

---

## Task 5: Create flow note `aggregation-stats.md` (scheduled + manual)

**Files:**
- Create: `docs/Obsidian/architecture/flows/aggregation-stats.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: 定义范围与触发入口**

- 定时任务: scheduler job `calculate_database_size_aggregations` -> `app/tasks/capacity_aggregation_tasks.py:calculate_database_size_aggregations`
- 手动触发(action):
  - `POST /api/v1/capacity/aggregations/current`(admin, 聚合当前周期)
- 查询聚合数据(read):
  - `GET /api/v1/capacity/databases` / `/summary`
  - `GET /api/v1/capacity/instances` / `/summary`

**Step 2: Mermaid**

- 主流程: select periods -> create session -> per instance aggregate -> write aggregation tables -> finalize session

**Step 3: 代码入口**

至少包含:
- contract: `docs/Obsidian/API/capacity-api-contract.md`
- API: `app/api/v1/namespaces/capacity.py`
- task: `app/tasks/capacity_aggregation_tasks.py`
- service: `app/services/aggregation/aggregation_service.py`
- partition retention:
  - `app/tasks/partition_management_tasks.py`
  - `app/services/partition_management_service.py`
- models:
  - `app/models/database_size_aggregation.py`
  - `app/models/instance_size_aggregation.py`
- Web UI(查询与手动触发入口):
  - routes:
    - `app/routes/capacity/instances.py` (`/capacity/instances`)
    - `app/routes/capacity/databases.py` (`/capacity/databases`)
  - templates:
    - `app/templates/capacity/instances.html` (`#calculateAggregations`)
    - `app/templates/capacity/databases.html` (`#calculateAggregations`)
  - JS charts controller:
    - `app/static/js/modules/views/components/charts/manager.js` (bind `#calculateAggregations`)
    - `app/static/js/modules/views/components/charts/data-source.js` (calls calculateCurrent)
  - JS service:
    - `app/static/js/modules/services/capacity_stats_service.js`

**Step 4: 常见 message_code**

至少列:
- `VALIDATION_ERROR`(参数/period)
- `TASK_EXECUTION_FAILED`/`INTERNAL_ERROR`(未捕获异常)

**Step 5: 自查 SQL**

- 某周期聚合是否已存在/是否跳过
- 按 instance_id/period_type 查询聚合结果条数与时间范围

---

## Task 6: Create flow note `tags-bulk.md`

**Files:**
- Create: `docs/Obsidian/architecture/flows/tags-bulk.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: 范围与入口**

覆盖(以当前 UI 行为为主):
- 批量分配: `POST /api/v1/tags/bulk/actions/assign`
- 批量移除(清空实例所有标签): `POST /api/v1/tags/bulk/actions/remove-all`

可选补充(非 UI 主路径, 仅作为对后端能力的备注/附录):
- 批量移除(指定 tag_ids): `POST /api/v1/tags/bulk/actions/remove`

**Step 2: Mermaid**

- flowchart: validate payload -> load instances/tags -> upsert relation -> return counts

**Step 3: 代码入口**

至少包含:
- contract: `docs/Obsidian/API/tags-api-contract.md`
- API: `app/api/v1/namespaces/tags.py`
- service: `app/services/tags/tags_bulk_actions_service.py`
- models: `app/models/tag.py`(`instance_tags` join table), `app/models/instance.py`
- Web UI(批量操作入口):
  - route: `app/routes/tags/bulk.py` (`/tags/bulk/assign`)
  - template: `app/templates/tags/bulk/assign.html`
  - JS: `app/static/js/modules/views/tags/batch-assign.js`
  - JS service: `app/static/js/modules/services/tag_management_service.js`
  - note: 当前 UI 的 "移除" 走 `remove-all`(不支持指定 tag_ids 移除)

**Step 4: 常见 message_code**

至少列:
- `REQUEST_DATA_EMPTY`, `VALIDATION_ERROR`

**Step 5: 自查 SQL**

- 按 instance_id 查询 instance_tags 关联数量
- 按 tag_id 查询被引用实例数

---

## Task 7: Create flow note `auto-classify.md`

**Files:**
- Create: `docs/Obsidian/architecture/flows/auto-classify.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: 范围与入口**

- 自动分类 action: `POST /api/v1/accounts/classifications/actions/auto-classify`(update + CSRF)
- 可选参数: `instance_id?`(只跑单实例或全量)

**Step 2: Mermaid**

- 主流程: validate -> load rules -> ensure permission facts -> evaluate -> write assignments -> return metrics

**Step 3: 代码入口**

至少包含:
- contract: `docs/Obsidian/API/accounts-api-contract.md`
- API: `app/api/v1/namespaces/accounts_classifications.py`
- service: `app/services/account_classification/auto_classify_service.py`
- orchestrator(如被调用): `app/services/account_classification/orchestrator.py`
- Web UI(触发入口):
  - route: `app/routes/accounts/classifications.py` (`/accounts/classifications/`)
  - template: `app/templates/accounts/account-classification/index.html` (`data-action="auto-classify-all"`)
  - JS: `app/static/js/modules/views/accounts/account-classification/index.js`
  - JS service: `app/static/js/modules/services/account_classification_service.js`

**Step 4: 常见 message_code**

至少列:
- `PERMISSION_FACTS_MISSING`
- `VALIDATION_ERROR`(payload)

---

## Task 8: Update flow index + cross-links

**Files:**
- Modify: `docs/Obsidian/architecture/flows/README.md:1`
- Modify: `docs/Obsidian/architecture/spec.md:1` (仅在需要时补充 links, 不重写图)
- Modify: `docs/Obsidian/operations/observability-ops.md:1` (仅补链接)
- Modify: `docs/Obsidian/architecture/developer-entrypoint.md:1` (仅补链接)

**Step 1: flows/README 指向 `flows/*.md`**

- `登录` -> `[[architecture/flows/login]]`
- `会话(批量异步)` -> `[[architecture/flows/sync-session]]`
- `账户同步` -> `[[architecture/flows/accounts-sync]]`
- `容量同步` -> `[[architecture/flows/capacity-sync]]`
- `聚合统计` -> `[[architecture/flows/aggregation-stats]]`
- `标签 bulk` -> `[[architecture/flows/tags-bulk]]`
- `自动分类` -> `[[architecture/flows/auto-classify]]`

同时保留深读链接到 `[[architecture/spec]]` 的对应章节.

**Step 2: 与运维口径对齐**

- 3 个定时任务的 SOP 必须链接 `[[operations/scheduler-jobstore-ops]]`
- 排障路径统一链接 `[[operations/observability-ops]]` 和 `docs/Obsidian/getting-started/debugging.md`

---

## Task 9: Verification

**Step 1: 半角字符扫描(仅新改 docs)**

Run:
```bash
rg -n -P \"[\\x{3000}\\x{3001}\\x{3002}\\x{3010}\\x{3011}\\x{FF01}\\x{FF08}\\x{FF09}\\x{FF0C}\\x{FF1A}\\x{FF1B}\\x{FF1F}\\x{2018}\\x{2019}\\x{201C}\\x{201D}\\x{2013}\\x{2014}\\x{2026}]\" docs/Obsidian/architecture/flows docs/Obsidian/architecture/spec.md docs/Obsidian/operations docs/Obsidian/getting-started
```
Expected: no output for newly edited sections.

**Step 2: Mermaid basic sanity**

- 确认每个 ` ```mermaid ` block 可在 Obsidian 预览正常渲染(至少不报语法错误).

**Step 3: Unit tests**

Run:
```bash
uv run pytest -m unit
```
Expected: exit 0.
