# Core Constants & Types Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 将 `app/core/constants/**` 与 `app/core/types/**` 物理迁移到 `app/core/` 下（分别为 `app/core/constants/**`、`app/core/types/**`），全仓改用新 import 路径，并且不保留任何 re-export/兼容门面。

**Architecture:** `app/core/**` 作为 shared kernel 的唯一路径承载：语义对象（`exceptions.py`）、常量 primitives（`core/constants`）、类型 primitives（`core/types`）。HTTP/DB/框架边界仍由外层（API/Infra/Utils/Routes）负责，shared kernel 不依赖它们。

**Tech Stack:** Python + Flask + ruff + pyright + pytest.

---

## Verification Baseline（每个阶段完成后必跑）

Run:

```bash
./.venv/bin/ruff check app tests
./scripts/ci/pyright-guard.sh
./.venv/bin/pytest -m unit
```

Expected:

- `ruff` Exit 0
- `pyright` diagnostics: 0
- `pytest` Exit 0

---

### Task 1: 迁移目录结构（无 re-export）

**Files:**

- Move: `app/core/constants/**` → `app/core/constants/**`
- Move: `app/core/types/**` → `app/core/types/**`
- Modify: `app/core/__init__.py`（必要时补充说明）

**Step 1: 执行目录迁移**

Run:

```bash
git mv app/core/constants app/core/constants
git mv app/core/types app/core/types
```

Expected:

- 工作区不再存在 `app/core/constants/**`、`app/core/types/**`
- 新路径存在 `app/core/constants/**`、`app/core/types/**`

**Step 2: 快速 smoke**

Run:

```bash
python -c "import app.core.constants, app.core.types; print('ok')"
```

Expected: 输出 `ok`

---

### Task 2: 全仓替换 import 路径（代码 + 测试）

**Files:**

- Modify: 所有引用 `app.core.constants*` 与 `app.core.types*` 的 Python 文件（含 `tests/**`）

**Step 1: 批量替换 import**

规则（示例）：

- `from app.core.constants import X` → `from app.core.constants import X`
- `from app.core.constants.xxx import Y` → `from app.core.constants.xxx import Y`
- `from app.core.types import X` → `from app.core.types import X`
- `from app.core.types.xxx import Y` → `from app.core.types.xxx import Y`
- `app.core.constants.xxx` → `app.core.constants.xxx`
- `app.core.types.xxx` → `app.core.types.xxx`

**Step 2: 修复迁移后出现的内部相对 import/循环依赖**

- `app/core/constants/**` 内部优先用相对 import（例如 `from .system_constants import ...`）
- `app/core/types/**` 内部优先用相对 import
- 禁止 `core/constants` 与 `core/types` 反向依赖 `app/core/exceptions.py`（避免 core 内部环）

**Step 3: 运行验证基线**

Run:

```bash
./.venv/bin/ruff check app tests
./scripts/ci/pyright-guard.sh
./.venv/bin/pytest -m unit
```

Expected: 全部通过

---

### Task 3: 更新标准文档与依赖图

**Files:**

- Modify: `docs/Obsidian/standards/backend/shared-kernel-standards.md`
- Modify: `docs/Obsidian/standards/backend/layer/README.md`（mermaid 路径/节点）
- Modify: `docs/Obsidian/standards/backend/layer/constants-layer-standards.md`（scope/path）
- Modify: `docs/Obsidian/standards/backend/layer/types-layer-standards.md`（scope/path）
- Modify: `docs/Obsidian/standards/backend/layer/utils-layer-standards.md`（说明 “纯工具/边界工具” 的依赖约束）

**Step 1: 修正 scope**

- constants scope 改为 `app/core/constants/**`
- types scope 改为 `app/core/types/**`

**Step 2: 修正依赖图**

- 移除 `app/core/constants` 与 `app/core/types` 的旧路径引用
- 明确 constants/types 属于 shared kernel 子包

