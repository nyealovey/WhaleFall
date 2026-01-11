# Backend Layer Boundary Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 依照 `docs/reports/2026-01-11-backend-layer-boundary-audit*.md` 的 Phase 1-4 进度表, 分阶段消除分层边界跨越, 并固化可验证的门禁口径.

**Architecture:** 以现有 `layer standards` 为单一真源, 优先让 `app/forms/**` 与 `app/tasks/**` 满足“零查库/零跨层依赖”的硬门槛, 再逐步把 Service 内的 `.query/db.session.query/execute` 下沉到 Repository. 全程避免引入额外框架与过度抽象, 以最小改动保持行为不变.

**Tech Stack:** Flask + SQLAlchemy ORM + structlog + pytest + uv.

---

## Verification Baseline(每个阶段都跑)

Run:

```bash
./scripts/ci/db-session-write-boundary-guard.sh
```

Expected:

- Exit 0

---

## Task 1: Phase 1 - Forms 去 DB/去跨层依赖

**Goal:** `app/forms/**` 中不再出现 `from app.(models|services|repositories)` / `Model.query` / `db.session`.

**Files:**

- Modify: `app/views/mixins/resource_forms.py`
- Modify: `app/forms/definitions/base.py`
- Modify: `app/forms/definitions/*.py`
- Move+Modify: `app/forms/handlers/*.py` -> `app/views/form_handlers/*.py`
- Modify: `app/views/*_forms.py` (为每个 view 显式绑定 `service_class`)
- Create: `app/views/form_handlers/__init__.py`
- Create: `app/constants/tag_categories.py`
- Modify: `app/models/tag.py` (改为读取常量, 移除 category choices 硬编码)
- Modify: `app/services/common/filter_options_service.py` (去掉对 `Tag.get_category_choices()` 的依赖)
- Modify: `app/services/tags/tags_bulk_actions_service.py` (同上)
- Modify: `app/forms/definitions/account_classification_constants.py` (若存在跨层 import, 只保留 constants re-export)

**Steps:**

1) 调整 `ResourceFormDefinition` 使其不再强制携带 `service_class`
2) 调整 `ResourceFormView` 支持从 View 自身获取 `service_class`(优先)或从 form_definition 获取(兼容迁移期), 并在缺失时抛错
3) 将 `app/forms/handlers/**` 全部迁移到 `app/views/form_handlers/**`, 并消除其中的 DB/query/repository 直用: 统一改为调用 Service(读/写/选项服务)完成 load/upsert/context
4) 更新所有 `app/forms/definitions/*.py` 去掉 handler import 与 `service_class=` 字段(保持字段定义与模板配置不变)
5) 更新每个 `app/views/*_forms.py` 显式设置 `service_class = ...` 指向对应的 `app/views/form_handlers/**`
6) 运行门禁自查:

```bash
rg -n "from app\\.(models|services|repositories)|db\\.session|\\.query\\b" app/forms
```

Expected:

- 0 命中

---

## Task 2: Phase 2 - Tasks 禁止 query/execute, 任务变薄(优先简单任务)

**Goal:** `app/tasks/**` 中不再出现 `.query` 与 `db.session.(query|execute)`.

**Files:**

- Modify: `app/tasks/log_cleanup_tasks.py`
- Create: `app/services/logging/log_cleanup_service.py`
- Create: `app/repositories/log_cleanup_repository.py` (如需要)
- Modify: `app/tasks/accounts_sync_tasks.py`
- Create: `app/services/accounts_sync/accounts_sync_task_service.py` (或在现有 coordinator 外包一层)
- (可选) Modify: `app/tasks/capacity_collection_tasks.py`, `app/tasks/capacity_aggregation_tasks.py` 仅保留薄入口, 重逻辑下沉到 `app/services/capacity/**`/`app/services/aggregation/**`

**Steps:**

1) 为 log cleanup 新增 service/repository, task 仅做 app_context + 调用 + commit/rollback
2) accounts sync task 获取 active instances 的 `.query` 改为调用 service(内部走 repository)
3) 对 capacity tasks: 先保证 task 文件内无 `.query/db.session.query/execute`, 再按需拆分 runner
4) 运行门禁自查:

```bash
rg -n "\\.query\\b|db\\.session\\.(query|execute)\\b" app/tasks
```

Expected:

- 0 命中

---

## Task 3: Phase 3 - Services 数据访问经 Repository(先 Instances/SyncSession)

**Goal:** 在指定 service 内, 移除 `.query/db.session.query/execute`, 统一下沉到 repository.

**Files:**

- Modify: `app/services/instances/instance_write_service.py`
- Modify: `app/repositories/instances_repository.py`
- (按需) Create: `app/repositories/credentials_repository.py` 新增校验/读取方法
- Modify: `app/services/sync_session_service.py`(如命中)
- Create/Modify: `app/repositories/sync_sessions_repository.py`(如需要)

**Steps:**

1) 为 instance 名称唯一性检查、credential 校验等新增 repository 方法
2) service 中只做编排与校验, 不再直接 `Instance.query/...` 或 `Credential.query/...`
3) 增量自查:

```bash
rg -n "\\.query\\b|db\\.session\\.(query|execute)\\b" app/services/instances/instance_write_service.py
```

Expected:

- 0 命中(或显著下降并标注剩余原因)

---

## Task 4: Phase 4 - API v1 去 models 依赖(按 namespace 逐个迁移)

**Goal:** `app/api/v1/**` 不再 `import app.models.*`, 统一通过 service DTO 输出.

**Files:**

- Modify: `app/api/v1/**`
- Modify/Create: 对应 `app/services/**` 的 read/list service + `app/types/**` DTO

**Steps:**

1) 逐个 namespace 替换 model import 为 service 调用
2) 保持接口返回封套与字段不变, 如需调整同步更新 API contract 文档
3) 自查:

```bash
rg -n "from app\\.models|import app\\.models" app/api/v1
```

Expected:

- 0 命中

