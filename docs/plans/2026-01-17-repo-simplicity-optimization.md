# Repo Simplicity Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 对整个仓库做 code-simplicity-reviewer 式极简化优化（严格 YAGNI），并按功能模块交付“模块文档 + 进度勾选追踪”。

**Architecture:** 先做模块识别与依赖排序，再逐模块进行“分析文档→落地删减/简化→格式化/类型检查/单测验证→勾选进度”。每个模块严格不改对外行为/接口/迁移历史；禁止无依据兜底/防御性分支/吞异常继续。

**Tech Stack:** Python (Flask), Ruff, Pyright, pytest (unit), make, uv.

---

### Task 1: 建立验证基线（可重复）

**Files:**
- Modify: `docs/optimization/progress.md`（记录验证结果与时间戳）

**Step 1: 运行格式化**

Run: `make format`
Expected: 退出码 0

**Step 2: 运行类型检查**

Run: `make typecheck`
Expected: 退出码 0

**Step 3: 运行单元测试**

Run: `uv run pytest -m unit`
Expected: 退出码 0

**Step 4: 记录结果**

在 `docs/optimization/progress.md` 写入本次验证的时间与结果（PASS/FAIL + 摘要）。

---

### Task 2: 模块识别与排序（一次）

**Files:**
- Create: `docs/optimization/progress.md`
- Create: `docs/optimization/modules/`（目录）

**Step 1: 统计依赖/耦合信号（import 计数）**

Run: `python3 scripts/optimization/module_import_stats.py`（如不存在则临时用一段脚本在命令行统计）
Expected: 输出 `app.<module>` 与 `app.services.<submodule>` 的引用计数

**Step 2: 生成模块清单（排序规则）**

规则：
- 先基础/被依赖最多的模块（core/utils/config/settings/infra/schemas...）
- 再高耦合模块（services/*、routes/views/tasks/scheduler...）
- 同层级内：CRUD → 同步/自动化（账户同步/容量同步/自动分类等）

**Step 3: 写入 progress 勾选列表**

在 `docs/optimization/progress.md` 创建按排序的模块清单（`- [ ]`），并给出每个模块的目标路径范围。

---

### Task 3+: 逐模块执行（循环）

对 `docs/optimization/progress.md` 中的每个模块重复以下步骤：

**Files:**
- Create: `docs/optimization/modules/<module>.md`
- Modify: 该模块覆盖的代码文件（以删减为主）
- Modify: `docs/optimization/progress.md`（勾选 + 记录验证）

**Step 1: 写模块文档（先写后改）**

在 `docs/optimization/modules/<module>.md` 写入：
- Core Purpose
- Unnecessary Complexity Found（带 `file:line`）
- Code to Remove（带 `file:line` + 可删 LOC 估算）
- Simplification Recommendations（可落地步骤 + 风险点）
- YAGNI Violations
- Final Assessment（LOC reduction 估算、复杂度评估、推荐动作）

**Step 2: 落地极简化改动（删减优先）**

策略：
- 删除死代码/未使用的 helper/无意义抽象
- 内联仅使用一次的抽象（函数/类/配置层）
- 早返回降嵌套；去重复；移除“兜底/吞异常继续”
- 不改变对外行为/接口/迁移历史

**Step 3: 运行验证命令**

Run: `make format && make typecheck && uv run pytest -m unit`
Expected: 全部 PASS

**Step 4: 更新进度**

将该模块在 `docs/optimization/progress.md` 从 `- [ ]` 改为 `- [x]`，并记录验证时间与结果。

