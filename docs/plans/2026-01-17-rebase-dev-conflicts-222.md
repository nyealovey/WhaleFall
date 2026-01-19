# Rebase 222 onto dev 冲突解决实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将分支 `222` 基于 `dev`（包含 `41bbec19`）完成 rebase，解决冲突并确保 `uv run pytest -m unit` 通过。

**Architecture:** 以 `git rebase dev` 重放本分支提交（`b4a75738`、`4e8877ec`）；对每一次停下来的冲突提交，先用可重复的“批量择优策略”把冲突变成可运行状态，再通过单元测试与对比 diff 逐步补齐被覆盖的关键改动，最后做格式化与类型检查收尾。

**Tech Stack:** Git, Python/Flask, pytest, Ruff/Pyright（仓库脚本）。

---

### Task 1: Rebase 前置检查与备份

**Files:**
- Modify: 无（仅 Git 操作）

**Step 1: 确认工作区干净**

Run: `git status`
Expected: `working tree clean`

**Step 2: 记录当前分支与提交边界**

Run:
```bash
git branch --show-current
git log --oneline dev..HEAD
git log --oneline HEAD..dev
```
Expected: 显示本分支待重放提交 + dev 的新增提交。

**Step 3: 创建备份分支**

Run:
```bash
git branch backup/222-pre-rebase-20260117
git show -s --oneline backup/222-pre-rebase-20260117
```
Expected: 备份分支指向当前 HEAD。

---

### Task 2: 启动 rebase 并定位冲突点

**Files:**
- Modify: 多个（冲突解决）

**Step 1: 启动 rebase**

Run: `git rebase dev`
Expected: rebase 在某个提交处暂停，并提示冲突文件清单。

**Step 2: 输出当前冲突文件列表**

Run: `git diff --name-only --diff-filter=U`
Expected: 输出冲突文件路径（与 rebase 提示一致）。

---

### Task 3: 解决冲突（提交 b4a75738）

**Files:**
- Modify: `git diff --name-only --diff-filter=U` 输出的全部冲突文件
- Test: `uv run pytest -m unit`

**Step 1: 批量选择“theirs”（保留当前正在重放的提交改动）**

Run:
```bash
git checkout --theirs -- $(git diff --name-only --diff-filter=U)
git add $(git diff --name-only --diff-filter=U)
```
Expected: `git diff --name-only --diff-filter=U` 为空。

**Step 2: 继续 rebase**

Run: `git rebase --continue`
Expected: 若进入下一个提交仍有冲突，则继续下一 Task；若无冲突，则 rebase 自动推进。

**Step 3: 运行单元测试做第一轮回归**

Run: `uv run pytest -m unit`
Expected: 全绿；若失败，按失败栈追踪到具体文件后再做最小修复。

---

### Task 4: 解决冲突（提交 4e8877ec）

**Files:**
- Modify: `git diff --name-only --diff-filter=U` 输出的全部冲突文件
- Test: `uv run pytest -m unit`

**Step 1: 重复冲突处理流程**

Run:
```bash
git diff --name-only --diff-filter=U
git checkout --theirs -- $(git diff --name-only --diff-filter=U)
git add $(git diff --name-only --diff-filter=U)
git rebase --continue
```
Expected: rebase 继续推进直至完成（或提示新的冲突批次）。

**Step 2: 运行单元测试做第二轮回归**

Run: `uv run pytest -m unit`
Expected: 全绿；若失败，按失败栈做最小修复并回到此步骤重跑。

---

### Task 5: 收尾检查（格式 / 类型 / 最终差异）

**Files:**
- Modify: 视测试失败修复情况而定

**Step 1: Ruff / Pyright（按仓库约定）**

Run:
```bash
./scripts/ci/ruff-report.sh style
./scripts/ci/pyright-report.sh
```
Expected: 无错误（或仅有已知可接受的告警）。

**Step 2: 确认 rebase 已结束且工作区干净**

Run:
```bash
git status
git log --oneline --decorate -n 10
```
Expected: 不在 rebase 状态；分支历史已线性化。

**Step 3: 对比备份分支，确认未误删关键变更**

Run:
```bash
git diff --stat backup/222-pre-rebase-20260117..HEAD
```
Expected: 差异符合预期（仅为 rebase 导致的冲突合并/必要修复）。

