# Backend Standards Audit Report (2026-01-13) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 复核 `docs/Obsidian/standards/backend/**` 的一致性(冲突/歧义), 并基于标准对 `app/**` 做静态审计, 产出一份 `docs/reports/2026-01-13-backend-standards-audit-report.md` 报告.

**Architecture:** 以标准文档为“规范真源”, 先做规则抽取与交叉比对找出冲突/歧义, 再结合仓库现有门禁脚本与补充静态扫描定位违规代码, 最后把证据与建议固化到报告.

**Tech Stack:** Shell(`rg/find/sed`), 项目内 CI 门禁脚本(`scripts/ci/*.sh`), Python 代码静态扫描(文本/必要时 AST).

---

### Task 1: 汇总 backend 标准清单与关键规则

**Files:**
- Read: `docs/Obsidian/standards/backend/**/*.md`

**Step 1: 列出标准文件清单**

Run: `find docs/Obsidian/standards/backend -type f -name "*.md" | sort`
Expected: 输出所有 backend 标准 markdown 文件路径.

**Step 2: 粗提取强约束关键词(MUST/SHOULD/MAY)**

Run: `rg -n "\\b(MUST|SHOULD|MAY|禁止|必须|应当)\\b" docs/Obsidian/standards/backend`
Expected: 命中若干条款, 作为后续冲突/歧义核对入口.

---

### Task 2: 识别冲突条款与模糊定义

**Files:**
- Read: `docs/Obsidian/standards/backend/**/*.md`
- Write: `docs/reports/2026-01-13-backend-standards-audit-report.md`

**Step 1: 交叉比对重复主题(依赖方向/错误封套/写边界/Schema 位置等)**

Action: 对同一主题出现多处定义的条款做“对照表”, 标出 MUST vs MAY/例外缺失/字段命名不一致等冲突.

**Step 2: 标注模糊条款(缺少可执行判定条件/缺少定义/边界不清)**

Action: 记录“模糊点 → 为什么模糊 → 建议补充的可执行判据(或示例/反例)”.

---

### Task 3: 基于标准扫描代码并收集证据

**Files:**
- Read: `app/**`
- Read: `scripts/ci/**`

**Step 1: 运行现有门禁脚本**

Run:
- `./scripts/ci/api-layer-guard.sh`
- `./scripts/ci/tasks-layer-guard.sh`
- `./scripts/ci/forms-layer-guard.sh`
- `./scripts/ci/services-repository-enforcement-guard.sh`
- `./scripts/ci/error-message-drift-guard.sh`
- `./scripts/ci/db-session-write-boundary-guard.sh`
- `./scripts/ci/secrets-guard.sh`
- `./scripts/ci/pyright-guard.sh`
Expected: 多数 exit 0. 若有 FAIL, 记录失败原因与影响面.

**Step 2: 补充静态扫描(按标准主题定向搜索)**

Run(示例):
- `rg -n "os\\.(environ\\.get|getenv)\\(" app | rg -v "app/settings\\.py|app\\.py|wsgi\\.py"`
- `rg -n "db\\.session\\.(commit|rollback)\\(" app/services`
- `rg -n "from flask import request|flask\\.request" app/services`
- `rg -n "\\bor\\b" app | rg -n "get\\(|\\.get\\("`
Expected: 命中点作为“疑似违规/兼容兜底”候选, 再结合条款逐条判定.

---

### Task 4: 生成并校对审计报告

**Files:**
- Create: `docs/reports/2026-01-13-backend-standards-audit-report.md`
- Reference: `docs/reports/2026-01-12-backend-standards-audit-report.md`

**Step 1: 复用报告结构并更新证据**

Action: 沿用 2026-01-12 报告结构(目标/方法/冲突歧义/违规代码/通过项/防御兼容清单), 但所有 PASS/FAIL 与违规点必须来自本次扫描结果.

**Step 2: 校对可执行性**

Action: 每条违规给出 `文件:行号`、标准依据(文档:行号)、修复建议与风险说明.

