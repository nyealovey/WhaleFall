# Remove `app/errors/` Directory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 移除 `app/errors/` 目录(不再作为独立“层/目录”存在)，但保留现有 `AppError` 体系、全局错误封套与 `from app.errors import ...` 的调用方式不变。

**Architecture:** 将 `app/errors/__init__.py` 迁移为单文件模块 `app/errors.py`。代码层面保持同名模块路径，避免大范围 import 改动；文档层面把 `app/errors/**` 的描述统一改为 `app/errors.py`。

**Tech Stack:** Python 3.13, Flask, structlog, Pydantic, Obsidian docs/canvas.

---

### Task 1: 迁移异常定义到单文件模块

**Files:**
- Create: `app/errors.py`
- Delete: `app/errors/__init__.py`
- Modify: `app/utils/error_mapping.py`(文档字符串引用)

**Step 1: 创建 `app/errors.py`**
- 将 `app/errors/__init__.py` 的实现原样迁移到 `app/errors.py`。
- 保持 `__all__` 与导出符号完全一致，确保 `from app.errors import AppError` 等 import 不变。

**Step 2: 删除 `app/errors/__init__.py`**
- 删除后 `app/errors/` 目录应为空并在 git 中消失。

**Step 3: 快速 import 自检**
- 运行 `python -c "from app.errors import AppError; print(AppError)"`，确保模块解析无异常。

---

### Task 2: 更新标准与架构文档(路径口径)

**Files:**
- Modify: `docs/Obsidian/architecture/module-dependency-graph.md`
- Modify: `docs/Obsidian/architecture/project-structure.md`
- Delete: `docs/Obsidian/standards/backend/layer/errors-layer-standards.md`

**Step 1: 替换 `app/errors/**` 为 `app/errors.py`**
- 保持语义不变：仍然是“统一错误类型(AppError 体系)”，只是载体从目录变为单文件模块。

**Step 2: 校对引用**
- 确保文档中关于“不能依赖 flask/werkzeug/utils/services”之类的约束仍成立，仅调整路径表述。

---

### Task 3: 更新 Obsidian Canvas 文本节点引用(可选但推荐)

**Files:**
- Modify: `docs/Obsidian/canvas/global-layer-first-module-dependency-graph.canvas`
- Modify: `docs/Obsidian/canvas/global-c4-l3-component-layering.canvas`

**Step 1: 文本节点路径替换**
- 将 canvas 文本节点中的 `app/errors/**` 或 `app/errors/*` 更新为 `app/errors.py`。

---

### Task 4: 验证

**Step 1: 单元测试**
- Run: `uv run pytest -m unit`

**Step 2: 类型检查**
- Run: `make typecheck`

**Step 3: Ruff(可选)**
- Run: `ruff check app docs`
