# Tests Not Gates + CI Enforcement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 `tests/` 里“扫描源码=门禁”的用例迁移到 `scripts/ci/**`，并在 CI 中强制执行“测试必跑 + 门禁必跑”，使 `tests/` 只保留真实行为/契约测试，且所有测试都是必须的（无 skip）。

**Architecture:** 将“规则/约束/静态检查”归入门禁脚本（`scripts/ci`），将“运行时行为验证”保留在 `tests/`。CI 拆成 `pytest` job（全量跑）与 `gates` job（全量跑 scripts/ci 关键门禁），避免把门禁伪装成单元测试。

**Tech Stack:** pytest + uv（Python 3.13），bash + ripgrep，必要时使用 python3 AST 扫描（标准库）与 node（如需要 JS AST）。

---

### Task 1: 盘点并分类现有测试（Test vs Gate）

**Files:**
- Modify: `docs/Obsidian/standards/core/guide/testing.md`
- Modify: `docs/Obsidian/standards/core/guide/scripts.md`

**Step 1: 列出门禁型测试清单（以 file system 扫描/AST 扫描为判定）**

Run:
```bash
rg -l "Path\\(__file__\\)|rglob\\(|read_text\\(" tests/unit | sort
```
Expected: 输出一组 `tests/unit/test_*`，这些将迁移为门禁脚本或删除（如为一次性迁移残留）。

**Step 2: 列出真正的行为型测试（保留在 tests）**

Run:
```bash
rg -l "client\\.get\\(|client\\.post\\(|monkeypatch|pytest\\.raises" tests/unit | sort
```
Expected: 输出的测试应主要断言函数/接口行为，而非扫描仓库源码文本。

---

### Task 2: 将门禁型测试迁移到 scripts/ci（或合并到已有门禁）

**Files:**
- Create: `scripts/ci/routes-safe-route-call-guard.sh`
- Create: `scripts/ci/settings-env-read-guard.sh`
- Create: `scripts/ci/db-session-rollback-allowlist-guard.sh`
- Create: `scripts/ci/api-v1-ns-expect-guard.sh`
- Create: `scripts/ci/frontend-contracts-guard.sh`（整合前端注入/迁移约束类测试）
- Create: `scripts/ci/ui-standards-audit-guard.sh`（从 pytest 迁移 UI audit）
- Modify: `scripts/ci/pagination-param-guard.sh`（覆盖 TableQueryParams）
- Modify: `docs/Obsidian/standards/backend/gate/layer/api-layer.md`（补齐门禁入口）
- Modify: `docs/Obsidian/standards/backend/gate/layer/settings-layer.md`（补齐门禁入口）
- Modify: `docs/Obsidian/standards/backend/gate/layer/repository-layer.md`（补齐门禁入口）
- Modify: `docs/Obsidian/standards/ui/gate/grid.md`（对齐分页门禁覆盖范围）
- Modify: `docs/Obsidian/standards/ui/gate/*`（为新增门禁补齐入口；必要时新增 gate 文档）

**Step 1: 把“routes 必须使用 safe_route_call”的 pytest 门禁转为脚本**

Create `scripts/ci/routes-safe-route-call-guard.sh`：
- 用 python3 `ast` 扫描 `app/routes/**/*.py`
- 识别含 `.route/.add_url_rule` 的模块必须出现 `safe_route_call(...)`

**Step 2: 把“settings 之外禁止读 env”的 pytest 门禁转为脚本**

Create `scripts/ci/settings-env-read-guard.sh`：
- `rg -n "os\\.(environ\\.get|getenv)\\(" app --type py` 并排除 `app/settings.py`

**Step 3: 把“禁止 services/repositories rollback + infra allowlist”的 pytest 门禁转为脚本**

Create `scripts/ci/db-session-rollback-allowlist-guard.sh`：
- python3 AST：识别 `db.session.rollback()` 以及 `session = db.session` alias 的 `.rollback()`
- 对 `app/services/**`、`app/repositories/**`：严格禁止
- 对 `app/infra/**`：只允许 `app/infra/route_safety.py`、`app/infra/logging/queue_worker.py`

**Step 4: 把“API v1 request.get_json 必须 @ns.expect”的 pytest 门禁转为脚本**

Create `scripts/ci/api-v1-ns-expect-guard.sh`：
- python3 AST 扫 `app/api/v1/namespaces/**/*.py`
- 凡 method 内调用 `request.get_json()` 则要求 decorator 存在 `@ns.expect(...)`

**Step 5: 前端 contracts 迁移**

Create `scripts/ci/frontend-contracts-guard.sh`：
- 用 `rg`/python3 对固定文件做关键字/正则检查（保持与现有 tests 中的约束一致）
- 目标：删除 `tests/unit/test_frontend_*` 这批“扫描源码的 contracts”

**Step 6: UI audit 迁移**

Create `scripts/ci/ui-standards-audit-guard.sh`：
- 迁移 `tests/unit/test_ui_standards_audit_regressions.py` 的检查逻辑
- 若依赖 node/espree：在 CI 的 gates job 增加 `npm ci`（基于 `package-lock.json`）

**Step 7: 删除/迁移 pytest 门禁文件**

Delete（或拆分后仅保留行为测试部分）：
- `tests/unit/test_routes_safe_route_call_guard.py`
- `tests/unit/test_settings_no_env_reads_outside_settings.py`
- `tests/unit/test_services_no_db_session_rollback.py`
- `tests/unit/test_repositories_no_db_session_rollback.py`
- `tests/unit/test_infra_db_session_rollback_allowlist.py`
- `tests/unit/test_api_v1_namespaces_json_body_expect_guard.py`
- `tests/unit/test_ui_standards_audit_regressions.py`
- `tests/unit/test_internal_contract_no_alias_fallback_chains.py`（已由 `scripts/ci/or-fallback-pattern-guard.sh` 覆盖）
- `tests/unit/test_docs_no_migration_route_doc_tooling.py`（一次性迁移残留，直接移除）
- 其余 `test_frontend_*` / `test_ops_*` 逐个迁移后删除

---

### Task 3: 清理 “非必须测试”（skip / unstable）

**Files:**
- Modify: `tests/unit/services/test_permission_snapshot_view.py`
- Modify: `tests/unit/models/test_account_permission.py`
- Modify: `tests/integration/conftest.py`（如需：移除无用目录或改为明确 CI 依赖）

**Step 1: 移除 snapshot_view 相关 pytest.skip**

- 直接 import `app.services.accounts_permissions.snapshot_view`
- 删除对 `AccountPermission.permission_snapshot` 的 hasattr+skip（字段已落地）

**Step 2: 移除 AccountPermission columns contract 的 pytest.skip**

- 直接断言 `permission_snapshot/permission_facts` 列存在且类型为 JSONB

---

### Task 4: CI 强制“测试必跑 + 门禁必跑”

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: 增加 pytest job**

Run (CI):
```bash
uv run pytest
```
Expected: PASS（功能稳定 + 无 skip）

**Step 2: 增加 gates job**

Run (CI):
```bash
./scripts/ci/secrets-guard.sh
./scripts/ci/ruff-style-guard.sh
./scripts/ci/pyright-guard.sh
./scripts/ci/or-fallback-pattern-guard.sh
./scripts/ci/db-session-commit-allowlist-guard.sh
./scripts/ci/db-session-write-boundary-guard.sh
./scripts/ci/pagination-param-guard.sh
./scripts/ci/routes-safe-route-call-guard.sh
./scripts/ci/settings-env-read-guard.sh
./scripts/ci/db-session-rollback-allowlist-guard.sh
./scripts/ci/api-v1-ns-expect-guard.sh
./scripts/ci/frontend-contracts-guard.sh
./scripts/ci/ui-standards-audit-guard.sh
```
If required: add `npm ci` before UI audit.

---

### Task 5: 文档对齐（SSOT）

**Files:**
- Modify: `docs/Obsidian/standards/core/guide/testing.md`
- Modify: `docs/Obsidian/standards/core/guide/scripts.md`
- Modify: 相关 standards（新增门禁脚本必须写入“门禁/检查方式”）

**Step 1: 在 testing.md 明确“tests != gates”**

- MUST NOT：在 `tests/` 内写“扫描仓库源码/目录结构”作为门禁
- MUST：门禁类检查必须落在 `scripts/ci/**` 并在对应标准文档登记

**Step 2: 更新 scripts.md 的门禁脚本清单**

- 把新增的 `scripts/ci/*-guard.sh` 补进表格

---

### Task 6: 本地验证

Run:
```bash
bash -n scripts/ci/*.sh
./scripts/ci/secrets-guard.sh
uv run pytest
```
Expected: 全部通过。

