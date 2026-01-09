# Route Layer Thin Service Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于“路由层只负责鉴权/封套”的约束，将 `app/api/v1/namespaces/**` 与 `app/routes/**` 中的“动作编排/DB 访问/循环批量/导出序列化/线程后台执行”等逻辑下沉到 `app/services/**`；路由层仅保留：鉴权/CSRF、参数解析、`safe_call`/封套与状态码选择。

**Architecture:** 以“一个高层 action endpoint 对应一个无状态 actions service”为主线（参考 `AccountsSyncActionsService`）。每个 service：
- 输入：尽量是已解析的基础类型（int/str/list/dict），避免直接依赖 Flask `request`。
- 输出：`dataclass` result（包含 `success/message` 与必要的 `http_status/message_key/extra`），或抛出项目既有的 `ValidationError/NotFoundError/ConflictError` 等。
- 事务：不在 service 内 `commit/rollback`，由 `safe_route_call` 统一提交（确保回滚语义不变）。
- 兼容/回退：现有兼容分支（如 tags 参数逗号分隔、reject offset）迁移到 service 或保留在参数解析层，保持对外契约不变。
- 文档同步：每完成一个路由文件的重构，必须同步更新对应 `docs/Obsidian/API/**-api-contract.md` 的 Endpoints 总览表 `Service` 列，明确 API 层调用的 service（避免分层漂移）。

**Tech Stack:** Flask-RESTX、Flask Blueprint、SQLAlchemy、pytest（unit）、现有 `safe_route_call`（commit/rollback 边界）。

---

## Refactor Targets（来自 2026-01-08 扫描）

> 完整路由清单见：`docs/plans/2026-01-08-route-layer-scan-inventory.md`。

**API action/批量类（高优先级）**
- `POST /api/v1/instances/<id>/actions/sync-capacity`（`app/api/v1/namespaces/instances.py`）
- `POST /api/v1/tags/bulk/actions/*` + `POST /api/v1/tags/bulk/instance-tags`（`app/api/v1/namespaces/tags.py`）
- `POST /api/v1/cache/actions/*` + `GET /api/v1/cache/classification/stats`（`app/api/v1/namespaces/cache.py`）
- `POST /api/v1/scheduler/jobs/<id>/actions/run` + `POST /api/v1/scheduler/jobs/actions/reload`（`app/api/v1/namespaces/scheduler.py`）

**API export/格式化类（中优先级）**
- `GET /api/v1/databases/ledgers/exports`（`app/api/v1/namespaces/databases.py`）

**API auth/校验类（中优先级）**
- `POST /api/v1/auth/login`（`app/api/v1/namespaces/auth.py`）
- `POST /api/v1/accounts/classifications/rules/actions/validate-expression`（`app/api/v1/namespaces/accounts_classifications.py`）

**页面路由（低优先级，可分期）**
- `app/routes/auth.py`（页面登录）
- `app/routes/instances/manage.py`（实例页直接 query Credential）
- `app/routes/credentials.py`（detail 直接 query）
- `app/routes/accounts/statistics.py`（统计页兜底/fallback 分支集中）

---

### Task 0: 冻结对外契约（确保改动只影响内部结构）

**Files:**
- Modify: `docs/Obsidian/standards/backend/api-contract-markdown-standards.md`
- Modify: `docs/Obsidian/API/*-api-contract.md`
- Verify: `tests/unit/routes/test_api_v1_instances_sync_capacity_contract.py`
- Verify: `tests/unit/routes/test_api_v1_tags_bulk_contract.py`
- Verify: `tests/unit/routes/test_api_v1_cache_contract.py`
- Verify: `tests/unit/routes/test_api_v1_scheduler_contract.py`
- Verify: `tests/unit/routes/test_api_v1_files_contract.py`
- Verify: `tests/unit/routes/test_api_v1_auth_contract.py`
- Verify: `tests/unit/routes/test_api_v1_accounts_classifications_contract.py`

**Step 0: 为 API contract 表增加 `Service` 列（一次性准备工作）**

- 在 `docs/Obsidian/standards/backend/api-contract-markdown-standards.md` 中，将 Endpoints 总览表表头扩展为：
  - `| Method | Path | Purpose | Service | Permission | CSRF | Notes |`
- 在 `docs/Obsidian/API/*-api-contract.md` 的 Endpoints 总览表中：
  - 新增 `Service` 列
  - 写清楚 API 路由层“直接调用”的 service（多调用用 `<br>` 分行）
  - 若暂时仍为路由内实现：`Service` 填 `-`，并在 `Notes` 标注 `TODO: move to ...`
- 同步更新 frontmatter 的 `updated`（YYYY-MM-DD）。

**Step 1: Run unit tests (baseline)**

Run:
- `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_sync_capacity_contract.py -q`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_tags_bulk_contract.py -q`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_cache_contract.py -q`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_scheduler_contract.py -q`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_files_contract.py -q`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_auth_contract.py -q`
- `uv run pytest -m unit tests/unit/routes/test_api_v1_accounts_classifications_contract.py -q`

Expected: PASS

**Step 2: Only if coverage is missing**
- 仅当发现某 endpoint 未被契约测试覆盖时，再补最小用例（不要写内部实现断言）。

---

### Task 1: 下沉 instances sync-capacity（动作编排 -> service）

**Files:**
- Create: `app/services/capacity/instance_capacity_sync_actions_service.py`
- Modify: `app/api/v1/namespaces/instances.py`
- Modify: `docs/Obsidian/API/instances-api-contract.md`
- Test: `tests/unit/routes/test_api_v1_instances_sync_capacity_contract.py`

**Step 1: Add service result type（不改变行为）**

在 `app/services/capacity/instance_capacity_sync_actions_service.py` 定义最小返回结构：

```python
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True, slots=True)
class InstanceCapacitySyncActionResult:
    success: bool
    message: str
    result: dict[str, Any]
    http_status: int = 200
    message_key: str = "OPERATION_SUCCESS"
    extra: Mapping[str, Any] | None = None
```

**Step 2: Move orchestration out of route**
- 把 `CapacitySyncCoordinator` 的 connect/inventory/collect/save/aggregate/disconnect 与 normalized result 构造，完整迁移到 service。
- 保留现有关键语义：
  - “业务失败返回 409 但仍提交 inventory（不 rollback）”的路径必须仍是**返回值**而不是抛异常（契约测试依赖）。
  - 维持 `message_key` 与状态码口径不变（如 `DATABASE_CONNECTION_ERROR`、`SYNC_DATA_ERROR`）。
- 保持 monkeypatch 点可用：service 内仍通过 `import app.services.database_sync as database_sync_module` / `import app.services.aggregation as aggregation_module` 引用协调器与聚合服务。

**Step 3: Route becomes thin**
- `InstanceSyncCapacityActionResource.post` 仅保留：鉴权/CSRF、调用 service、用 `self.success / self.error_message` 封套返回。

**Step 4: Run**
Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_instances_sync_capacity_contract.py -q`
Expected: PASS

**Step 5: Update API contract**
- 更新 `docs/Obsidian/API/instances-api-contract.md` 的 Endpoints 总览表：
  - 将 `POST /api/v1/instances/{instance_id}/actions/sync-capacity` 的 `Service` 从“路由内实现”改为 `InstanceCapacitySyncActionsService`（或最终命名）
  - 更新 frontmatter `updated`

---

### Task 2: 下沉 tags bulk actions（批量循环/DB query -> service）

**Files:**
- Create: `app/services/tags/tags_bulk_actions_service.py`
- Modify: `app/api/v1/namespaces/tags.py`
- Modify: `docs/Obsidian/API/tags-api-contract.md`
- Test: `tests/unit/routes/test_api_v1_tags_bulk_contract.py`

**Step 1: Create actions service skeleton**

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TagsBulkAssignResult:
    assigned_count: int

class TagsBulkActionsService:
    def assign(self, *, instance_ids: list[int], tag_ids: list[int], actor_id: int | None) -> TagsBulkAssignResult: ...
    def remove(self, *, instance_ids: list[int], tag_ids: list[int], actor_id: int | None) -> dict: ...
    def remove_all(self, *, instance_ids: list[int], actor_id: int | None) -> dict: ...
    def list_instance_tags(self, *, instance_ids: list[int]) -> dict: ...
```

**Step 2: Move DB access + loops**
- `Instance.query.filter(Instance.id.in_(...))` / `Tag.query.filter(Tag.id.in_(...))` + 双重循环 append/remove 下沉。
- 保持异常口径不变（`ValidationError/NotFoundError`）。

**Step 3: Keep route-only responsibilities**
- 路由层仅保留：payload 读取、ID 列表转换（如果你希望“解析也下沉”，可在 service 接受 raw payload；但本计划默认路由保留最小解析）。
- route 内不再出现 `Instance.query` / `Tag.query` / `for instance in instances`。

**Step 4: Run**
Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_tags_bulk_contract.py -q`
Expected: PASS

**Step 5: Update API contract**
- 更新 `docs/Obsidian/API/tags-api-contract.md` 的 Endpoints 总览表：
  - 将 `/api/v1/tags/bulk/actions/assign|remove|remove-all` 与 `/api/v1/tags/bulk/instance-tags` 的 `Service` 从 `-` 改为 `TagsBulkActionsService.*`
  - 更新 frontmatter `updated`

---

### Task 3: 下沉 cache actions（实例校验/批量循环 -> service）

**Files:**
- Create: `app/services/cache/__init__.py`
- Create: `app/services/cache/cache_actions_service.py`
- Modify: `app/api/v1/namespaces/cache.py`
- Modify: `docs/Obsidian/API/cache-api-contract.md`
- Test: `tests/unit/routes/test_api_v1_cache_contract.py`

**Step 1: Implement CacheActionsService**
- 迁移 `_require_cache_service`、clear-user/clear-instance/clear-all/clear-classification/classification-stats 的核心逻辑到 service。
- 保持 monkeypatch 点：仍通过 `import app.services.cache_service as cache_service_module` 读取 `cache_service_module.cache_service`。
- `clear-all` 与 `classification-stats` 的 “try/except 记录日志后继续” 保持一致（不要改变吞错范围）。

**Step 2: Route becomes thin**
- 路由只做：payload/args 读取 + 调用 service + `safe_call` 封套。

**Step 3: Run**
Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_cache_contract.py -q`
Expected: PASS

**Step 4: Update API contract**
- 更新 `docs/Obsidian/API/cache-api-contract.md` 的 Endpoints 总览表：
  - 将 cache actions / classification stats 的 `Service` 统一为 `CacheActionsService.*`
  - 更新 frontmatter `updated`

---

### Task 4: 下沉 scheduler run/reload（线程后台执行/循环删除 -> service）

**Files:**
- Create: `app/services/scheduler/scheduler_actions_service.py`
- Modify: `app/api/v1/namespaces/scheduler.py`
- Modify: `docs/Obsidian/API/scheduler-api-contract.md`
- Test: `tests/unit/routes/test_api_v1_scheduler_contract.py`

**Step 1: Create SchedulerActionsService**
- `run_job_in_background(job_id, created_by)`：返回 `manual_job_id`（线程名）并负责后台执行。
- `reload_jobs()`：删除现有任务、调用 `_reload_all_jobs()`、返回 deleted/reloaded 统计。
- 保持 monkeypatch 点：仍使用 `import app.scheduler as scheduler_module`。

**Step 2: Route becomes thin**
- 路由层仅保留：鉴权/CSRF + `safe_call` + 返回封套。

**Step 3: Run**
Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_scheduler_contract.py -q`
Expected: PASS

**Step 4: Update API contract**
- 更新 `docs/Obsidian/API/scheduler-api-contract.md` 的 Endpoints 总览表：
  - 将 `actions/run` 与 `jobs/actions/reload` 的 `Service` 改为 `SchedulerActionsService.*`
  - 更新 frontmatter `updated`

---

### Task 5: 下沉 databases ledgers export（CSV 序列化 -> service）

**Files:**
- Create: `app/services/files/database_ledger_export_service.py`
- Modify: `app/api/v1/namespaces/databases.py`
- Modify: `docs/Obsidian/API/databases-api-contract.md`
- Test: `tests/unit/routes/test_api_v1_files_contract.py`

**Step 1: Create export service**
- 将 CSV header/row 写入、字段选择与 `sanitize_csv_row` 调用迁移到 service。
- service 内仍调用 `DatabaseLedgerService().iterate_all(...)`，以保持现有 monkeypatch 点（`test_api_v1_files_contract`）。

**Step 2: Route becomes thin**
- 路由保留 tags 参数兼容解析（`getlist` 与逗号分隔 fallback）或迁移到 service（两者任选其一，但不要改对外行为）。
- route 返回 `Response`（attachment）保持一致。

**Step 3: Run**
Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_files_contract.py -q`
Expected: PASS

**Step 4: Update API contract**
- 更新 `docs/Obsidian/API/databases-api-contract.md` 的 Endpoints 总览表：
  - 将 `/api/v1/databases/ledgers/exports` 的 `Service` 改为 `DatabaseLedgerExportService.*`（或最终命名）
  - 更新 frontmatter `updated`

---

### Task 7: 下沉 API 登录（User.query + token 生成 -> service）

**Files:**
- Create: `app/services/auth/login_service.py`
- Modify: `app/api/v1/namespaces/auth.py`
- Modify: `docs/Obsidian/API/auth-api-contract.md`
- Test: `tests/unit/routes/test_api_v1_auth_contract.py`

**Step 1: Create LoginService**
- `authenticate(username, password) -> user/None` 与 `build_login_response(user)` 分离，避免路由层直接 query + check_password。
- 保持 `message_key`/错误口径不变（`INVALID_CREDENTIALS`、`ACCOUNT_DISABLED`）。

**Step 2: Route becomes thin**
- `LoginResource.post` 仅保留 payload 解析/必填校验 + 调用 LoginService + 成功封套返回。

**Step 3: Run**
Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_auth_contract.py -q`
Expected: PASS

**Step 4: Update API contract**
- 更新 `docs/Obsidian/API/auth-api-contract.md` 的 Endpoints 总览表：
  - 将 `POST /api/v1/auth/login` 的 `Service` 从 `-` 改为 `LoginService.*`
  - 更新 frontmatter `updated`

---

### Task 8: 下沉 validate-expression（DSL v4 parse/validate -> service）

**Files:**
- Create: `app/services/accounts/account_classification_expression_validation_service.py`
- Modify: `app/api/v1/namespaces/accounts_classifications.py`
- Modify: `docs/Obsidian/API/accounts-api-contract.md`
- Test: `tests/unit/routes/test_api_v1_accounts_classifications_contract.py`

**Step 1: Extract validation**
- service 提供 `parse_and_validate(expression: object) -> object`：
  - 支持 string JSON -> object
  - 强制 DSL v4（`message_key="DSL_V4_REQUIRED"`）
  - 收集 errors（`message_key="INVALID_DSL_EXPRESSION"`，`extra={"errors": ...}`）

**Step 2: Route becomes thin**
- route 只做：payload 读取 + 调用 service + success envelope。

**Step 3: Run**
Run: `uv run pytest -m unit tests/unit/routes/test_api_v1_accounts_classifications_contract.py -q`
Expected: PASS

**Step 4: Update API contract**
- 更新 `docs/Obsidian/API/accounts-api-contract.md` 的 Endpoints 总览表：
  - 将 `POST /api/v1/accounts/classifications/rules/actions/validate-expression` 的 `Service` 从 `-` 改为 `AccountClassificationExpressionValidationService.*`（或最终命名）
  - 更新 frontmatter `updated`

---

### Task 9: 页面路由下沉（可选 Phase 2）

**Files:**
- Optional Modify: `app/routes/auth.py`
- Optional Modify: `app/routes/instances/manage.py`
- Optional Modify: `app/routes/credentials.py`
- Optional Modify: `app/routes/accounts/statistics.py`

**Step 1: Extract read services**
- 将页面路由中直接 `Model.query...` 的部分提取到对应 `app/services/**` read service（或复用现有 repository/service）。

**Step 2: Keep routes view-only**
- 路由层只保留渲染模板与最小参数读取；失败兜底策略集中在 service（由 service 返回“兜底上下文”）。

**Step 3: Manual smoke check**
- 本计划不强制为 HTML 路由补单测；如有现成测试框架再补最小 smoke。

---

### Task 10: 回归验证 + 清理

**Files:**
- None

**Step 1: Run unit tests**
Run: `uv run pytest -m unit -q`
Expected: PASS

**Step 2: Static checks**
Run:
- `./scripts/ci/ruff-report.sh style`
- `./scripts/ci/pyright-report.sh`

---

### (Optional) Task 11: 增加“薄路由”门禁（防回退）

**Files:**
- Optional Create: `scripts/ci/routes-layer-thin-guard.sh`

**Idea:**
- `rg -n \"\\.query\\b\" app/api/v1/namespaces app/routes` 作为最小门禁（需要允许白名单/例外，避免误伤）。
- 该门禁应仅作为“提醒/报告”，避免一次性阻塞所有遗留（可先做 report 模式）。
