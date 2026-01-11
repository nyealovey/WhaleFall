# Backend Layer Phase 5 CI Guards Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 新增并在 CI(pre-commit) 中启用分层门禁脚本(forms/tasks/api/services)，用于“禁止新增边界跨越”。

**Architecture:** 基于现有 `scripts/ci/*-guard.sh` 的实现风格：Bash + ripgrep 扫描；对“必须为 0 命中”的层(Forms/Tasks/API)直接 fail；对 Services `.query/db.session.query/execute` 漂移采用 baseline 机制(允许减少，禁止新增)以避免一次性清仓。

**Tech Stack:** Bash + ripgrep(`rg`) + pre-commit(local hooks).

---

## Verification Baseline(每个任务都跑)

Run:

```bash
./scripts/ci/db-session-write-boundary-guard.sh
```

Expected:

- Exit 0

---

### Task 1: Add Forms Layer Guard

**Files:**
- Create: `scripts/ci/forms-layer-guard.sh`
- Modify: `.pre-commit-config.yaml`

**Step 1: Implement guard**
- 用 `rg` 扫描 `app/forms/**`，禁止：
  - `from app.(models|services|repositories)` / `import app.(models|services|repositories)`
  - `db.session`
  - `.query`

**Step 2: Run guard**
Run: `./scripts/ci/forms-layer-guard.sh`
Expected: PASS

---

### Task 2: Add Tasks Layer Guard

**Files:**
- Create: `scripts/ci/tasks-layer-guard.sh`
- Modify: `.pre-commit-config.yaml`

**Step 1: Implement guard**
- 用 `rg` 扫描 `app/tasks/**`，禁止：
  - `.query`
  - `db.session.(query|execute|add|add_all|delete|merge|flush)(`
  - 允许 `db.session.commit/rollback`(不纳入模式)

**Step 2: Run guard**
Run: `./scripts/ci/tasks-layer-guard.sh`
Expected: PASS

---

### Task 3: Add API v1 Layer Guard

**Files:**
- Create: `scripts/ci/api-layer-guard.sh`
- Modify: `.pre-commit-config.yaml`

**Step 1: Implement guard**
- 用 `rg` 扫描 `app/api/v1/**`，禁止：
  - `from app.models` / `import app.models`
  - `from app.routes` / `import app.routes`
  - `db.session`
  - `.query`

**Step 2: Run guard**
Run: `./scripts/ci/api-layer-guard.sh`
Expected: PASS

---

### Task 4: Add Services Repository Enforcement Guard (baseline)

**Files:**
- Create: `scripts/ci/services-repository-enforcement-guard.sh`
- Create: `scripts/ci/baselines/services-repository-enforcement.txt`
- Modify: `.pre-commit-config.yaml`

**Step 1: Implement guard**
- 用 `rg` 扫描 `app/services/**`：
  - 模式：`\\.query\\b|db\\.session\\.(query|execute)\\b`
  - 输出 baseline 采用“去掉行号、保留 path + 行文本(压缩空白)”的规范化格式，减少无意义漂移。
  - 机制：允许减少，禁止新增；支持 `--update-baseline`。

**Step 2: Generate baseline**
Run: `./scripts/ci/services-repository-enforcement-guard.sh --update-baseline`
Expected: baseline 文件生成成功。

**Step 3: Run guard**
Run: `./scripts/ci/services-repository-enforcement-guard.sh`
Expected: PASS

---

### Task 5: Enable Guards in pre-commit (CI)

**Files:**
- Modify: `.pre-commit-config.yaml`
- Modify: `docs/reports/2026-01-11-backend-layer-boundary-audit-progress.md`

**Step 1: Add local hooks**
- 为 4 个 guard 增加 local hook，`language: system`，`pass_filenames: false`。
- 用 `files:` 限定触发目录：
  - forms: `^app/forms/.*\\.py$`
  - tasks: `^app/tasks/.*\\.py$`
  - api: `^app/api/v1/.*\\.py$`
  - services: `^app/services/.*\\.py$`

**Step 2: Run verification**
Run:
```bash
./scripts/ci/forms-layer-guard.sh
./scripts/ci/tasks-layer-guard.sh
./scripts/ci/api-layer-guard.sh
./scripts/ci/services-repository-enforcement-guard.sh
./scripts/ci/db-session-write-boundary-guard.sh
uv run pytest -m unit
```
Expected: 全部 PASS

