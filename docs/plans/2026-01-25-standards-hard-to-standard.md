# Standards `hard/` -> `standard/` Refactor Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `docs/Obsidian/standards/**/hard/` 目录统一重命名为 `standard/`，并全仓更新引用（含 Obsidian wikilinks、脚本报错提示、README/AGENTS 入口），避免断链。

**Architecture:** 仅做“路径/目录名”重构：保持文件名不变；用 `git mv` 保留历史；用批量替换更新引用；最后用 `rg`/脚本做残留扫描与最小验证。

**Tech Stack:** Git、ripgrep(`rg`)、Python 3（批量替换与校验）

---

### Task 1: 目录重命名（git mv）

**Files:**
- Move: `docs/Obsidian/standards/core/standard/` -> `docs/Obsidian/standards/core/standard/`
- Move: `docs/Obsidian/standards/backend/standard/` -> `docs/Obsidian/standards/backend/standard/`

**Step 1: git mv**

Run:
```bash
git mv docs/Obsidian/standards/core/standard docs/Obsidian/standards/core/standard
git mv docs/Obsidian/standards/backend/standard docs/Obsidian/standards/backend/standard
```

Expected: `git status` 显示为 rename/move（目录下文件整体迁移）。

---

### Task 2: 全仓引用更新（hard -> standard）

**Files:**
- Modify: 命中 `standards/*/hard/*` 与 `docs/Obsidian/standards/*/hard/*` 的所有文件

**Step 1: 扫描旧引用**

Run:
```bash
rg -n "standards/(core|backend)/hard/|docs/Obsidian/standards/(core|backend)/hard/" -S
```

Expected: 命中列表可控（用于替换前对账）。

**Step 2: 批量替换**

替换映射：
- `standards/core/standard/` -> `standards/core/standard/`
- `standards/backend/standard/` -> `standards/backend/standard/`
- `docs/Obsidian/standards/core/standard/` -> `docs/Obsidian/standards/core/standard/`
- `docs/Obsidian/standards/backend/standard/` -> `docs/Obsidian/standards/backend/standard/`

---

### Task 3: 验证（防断链）

**Step 1: 残留扫描**

Run:
```bash
rg -n "standards/(core|backend)/hard/|docs/Obsidian/standards/(core|backend)/hard/" -S || true
```

Expected: 无命中（或仅剩历史说明/示例，按需人工确认）。

**Step 2: Shell 语法检查（可选）**

Run:
```bash
bash -n scripts/ci/*.sh
```

Expected: 通过。

**Step 3: 引用存在性校验（可选）**

- 校验 `scripts/ci` 引用的 standards 文档都存在
- 校验 standards 文档里引用的 `./scripts/ci/*.sh` 都存在

