# Architecture Flows SOP Notes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 把 `docs/Obsidian/architecture/flows/` 从"索引"补齐为 4 份可执行 SOP(含流程图/入口代码/常见排障与自查命令), 让开发与排障能直接按文档操作.

**Architecture:** 以 4 个关键流程为单位(登录/同步会话/容量采集/scheduler), 每个流程 1 份 Obsidian 笔记, 统一结构: 背景与范围 -> Mermaid 图 -> 代码入口 -> 可复制复现 -> 常见错误码 -> 自查 SQL/rg -> 关联 standards/reference/API contract.

**Tech Stack:** Obsidian Markdown(YAML frontmatter + wikilinks + callouts) + Mermaid, 代码定位工具 `rg`, API 调用 `curl`, DB 自查 SQL.

---

## Task 1: Create flow note `login.md`

**Files:**
- Create: `docs/Obsidian/architecture/flows/login.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: 写 frontmatter + 目录结构骨架**

必含:
- `title/aliases/tags/status/created/updated/owner/scope/related`
- headings: `适用场景`, `流程图`, `代码入口`, `可复制复现`, `常见 message_code`, `自查命令`, `相关文档`

**Step 2: Mermaid(2 张)**

- sequence: Web 登录(页面) -> `app/routes/auth.py` -> `LoginService` -> `User`
- sequence: API 登录(REST) -> `GET /api/v1/auth/csrf-token` -> `POST /api/v1/auth/login` -> cookie + JWT

要求:
- 图内只写真实组件名/路由/服务名(以当前代码为准)
- 关键边界注明: CSRF header only, cookie vs JWT

**Step 3: 代码入口清单 + `rg` 定位命令**

建议包含:
- `app/routes/auth.py`
- `app/services/auth/login_service.py`
- `app/api/v1/namespaces/auth.py`
- `app/utils/decorators.py`(`require_csrf`)
- `app/api/v1/resources/decorators.py`(`api_login_required`)

示例命令:
- `rg -n \"class LoginResource\" app/api/v1/namespaces/auth.py`
- `rg -n \"def login\\(\" app/services/auth/login_service.py`

**Step 4: 可复制复现**

复用 `[[reference/examples/api-v1-cookbook]]` 的最小 curl, 只保留关键步骤并链接回 cookbook.

**Step 5: 常见 message_code**

至少列:
- `CSRF_MISSING`, `CSRF_INVALID`
- `AUTHENTICATION_REQUIRED`
- `INVALID_CREDENTIALS`, `ACCOUNT_DISABLED`, `RATE_LIMIT_EXCEEDED`

链接到:
- `[[reference/errors/message-code-catalog]]`

---

## Task 2: Create flow note `sync-session.md`

**Files:**
- Create: `docs/Obsidian/architecture/flows/sync-session.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: 写 frontmatter + SOP 骨架**

scope 要明确: session 是跨流程的观测与聚合对象(不是某个单域的实现细节).

**Step 2: Mermaid**

- flowchart: "触发入口" -> 创建 `SyncSession` -> per-instance `SyncInstanceRecord` -> 更新统计/终态 -> UI/日志查询

**Step 3: 代码入口**

至少包含:
- models: `app/models/sync_session.py`, `app/models/sync_instance_record.py`
- session service(如果存在): `app/services/sync_session_service.py`(或实际落点)
- 触发入口: `app/api/v1/namespaces/sessions.py` / 相关 task/service
- 清理: `app/tasks/log_cleanup_tasks.py`

**Step 4: 自查 SQL**

包含:
- 按 `session_id` 查失败实例
- 最近 24h 失败 session 概览

**Step 5: 常见 message_code**

至少列:
- `SYNC_DATA_ERROR`, `SNAPSHOT_MISSING`, `PERMISSION_FACTS_MISSING`

---

## Task 3: Create flow note `capacity-collection.md`

**Files:**
- Create: `docs/Obsidian/architecture/flows/capacity-collection.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: SOP 骨架**

需要明确 3 段:
- inventory 同步(数据库列表)
- 采集并落库 stats
- 聚合触发(失败不影响主流程)

**Step 2: Mermaid**

- sequence: `POST /api/v1/instances/{id}/actions/sync-capacity` -> `InstanceCapacitySyncActionsService` -> `CapacitySyncCoordinator` -> adapters -> save stats -> trigger aggregation

**Step 3: 代码入口**

至少包含:
- API: `app/api/v1/namespaces/instances.py`(sync-capacity action)
- service: `app/services/capacity/instance_capacity_sync_actions_service.py`
- coordinator/adapters: `app/services/database_sync/**`(按实际 factory/adapters)
- stats models:
  - `app/models/database_size_stat.py`
  - `app/models/instance_size_stat.py`
  - `app/models/database_size_aggregation.py`
  - `app/models/instance_size_aggregation.py`
- 分区/保留期:
  - `app/tasks/partition_management_tasks.py`
  - `app/services/partition_management_service.py`

**Step 4: 自查 SQL**

至少包含:
- 某实例最近 N 天 `database_size_stats` 采集情况
- 某实例最新 `instance_size_stats`/聚合表

**Step 5: 常见 message_code**

至少列:
- `DATABASE_CONNECTION_ERROR`, `SYNC_DATA_ERROR`

---

## Task 4: Create flow note `scheduler-execution.md`

**Files:**
- Create: `docs/Obsidian/architecture/flows/scheduler-execution.md`
- Modify: `docs/Obsidian/architecture/flows/README.md:1`

**Step 1: SOP 骨架**

需要明确:
- scheduler 何时启动/何时跳过(ENABLE_SCHEDULER, reloader, gunicorn)
- jobstore(SQLite) 的职责与风险
- 手动触发(run/reload)与日志定位方式

**Step 2: Mermaid**

- flowchart: 进程启动 -> `_should_start_scheduler` -> `_acquire_scheduler_lock` -> `init_scheduler` -> load jobs -> add default jobs -> run job -> write logs

**Step 3: 代码入口**

至少包含:
- `app/scheduler.py`
- `app/config/scheduler_tasks.yaml`
- API: `app/api/v1/namespaces/scheduler.py`
- service: `app/services/scheduler/scheduler_actions_service.py`

**Step 4: 与运维口径对齐**

文档中必须引用:
- `[[operations/scheduler-jobstore-ops]]`

**Step 5: 常见 message_code**

至少列:
- `CONSTRAINT_VIOLATION`(调度器未启动时的 ConflictError 默认), `FORBIDDEN`, `VALIDATION_ERROR`

---

## Task 5: Update flow index + cross-links

**Files:**
- Modify: `docs/Obsidian/architecture/flows/README.md:1`
- Modify: `docs/Obsidian/architecture/spec.md:1` (仅在需要时补充 links, 不重写图)
- Modify: `docs/Obsidian/operations/observability-ops.md:1` (仅补链接, 不改 SOP 逻辑)

**Step 1: flows/README 由"指向 spec"改为"指向 flows/*.md"**

- `登录` -> `[[architecture/flows/login]]`
- `同步会话` -> `[[architecture/flows/sync-session]]`
- `容量采集与聚合` -> `[[architecture/flows/capacity-collection]]`
- `scheduler 执行` -> `[[architecture/flows/scheduler-execution]]`

同时保留 "深读" 链接到 `[[architecture/spec]]` 的对应章节.

**Step 2: 入口文档串联**

如有必要, 在以下入口补 1 行链接:
- `docs/Obsidian/architecture/developer-entrypoint.md`
- `docs/getting-started/debugging.md`

---

## Task 6: Verification

**Step 1: 半角字符扫描(仅新改 docs)**

Run:
```bash
rg -n -P \"[\\x{3000}\\x{3001}\\x{3002}\\x{3010}\\x{3011}\\x{FF01}\\x{FF08}\\x{FF09}\\x{FF0C}\\x{FF1A}\\x{FF1B}\\x{FF1F}\\x{2018}\\x{2019}\\x{201C}\\x{201D}\\x{2013}\\x{2014}\\x{2026}]\" docs/Obsidian/architecture/flows docs/Obsidian/architecture/spec.md docs/Obsidian/operations docs/getting-started
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

