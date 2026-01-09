# Standards -> Obsidian Standards Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `docs/standards/**` 全量迁移并重写为 Obsidian 笔记形态, 统一落在 `docs/Obsidian/standards/**`, 并更新仓库内所有引用.

**Architecture:** 采用 `git mv` 保留历史, 逐文件迁移到 `docs/Obsidian/standards/` 后按 Obsidian Markdown 习惯(Frontmatter + wikilinks + callouts)重写内容与链接; 最后删除旧 `docs/standards/` 并全局消除引用.

**Tech Stack:** Markdown, Obsidian vault(`docs/Obsidian/`), Git, ripgrep(`rg`), (可选)最小 CI guard 脚本.

---

## 0. 进度表(一次性重写清单)

> 说明: `Status` 建议使用 `TODO / DOING / DONE / BLOCKED`.

| Old Path | New Path | Status | Notes |
| --- | --- | --- | --- |
| `docs/standards/README.md` | `docs/Obsidian/standards/README.md` | TODO | 新的 standards 入口与索引 |
| `docs/standards/documentation-standards.md` | `docs/Obsidian/standards/doc/documentation-standards.md` | TODO | 需要重写目录结构描述(standards 已迁移) |
| `docs/standards/halfwidth-character-standards.md` | `docs/Obsidian/standards/halfwidth-character-standards.md` | TODO | 更新路径与检查规则描述 |
| `docs/standards/coding-standards.md` | `docs/Obsidian/standards/coding-standards.md` | TODO | 统一链接写法与例子 |
| `docs/standards/naming-standards.md` | `docs/Obsidian/standards/naming-standards.md` | TODO | 更新所有引用路径 |
| `docs/standards/testing-standards.md` | `docs/Obsidian/standards/testing-standards.md` | TODO | 更新测试命令引用 |
| `docs/standards/git-workflow-standards.md` | `docs/Obsidian/standards/git-workflow-standards.md` | TODO | 更新 references |
| `docs/standards/scripts-standards.md` | `docs/Obsidian/standards/scripts-standards.md` | TODO | 更新 references |
| `docs/standards/terminology.md` | `docs/Obsidian/standards/terminology.md` | TODO | 转为 Obsidian 术语表格式 |
| `docs/standards/changes-standards.md` | `docs/Obsidian/standards/doc/changes-standards.md` | TODO | 与 changes 目录索引互链 |
| `docs/standards/new-feature-delivery-standard.md` | `docs/Obsidian/standards/new-feature-delivery-standard.md` | TODO | 更新“上升为标准”路径 |
| `docs/standards/version-update-guide.md` | `docs/Obsidian/standards/version-update-guide.md` | TODO | 与发版 skill/脚本互链 |
| `docs/standards/backend/README.md` | `docs/Obsidian/standards/backend/README.md` | TODO | backend standards 索引 |
| `docs/standards/backend/action-endpoint-failure-semantics.md` | `docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md` | TODO | - |
| `docs/standards/backend/api-contract-markdown-standards.md` | `docs/Obsidian/standards/doc/api-contract-markdown-standards.md` | TODO | SSOT 标准 |
| `docs/standards/backend/api-naming-standards.md` | `docs/Obsidian/standards/backend/layer/api-layer-standards.md` | TODO | merged (api naming) |
| `docs/standards/backend/api-response-envelope.md` | `docs/Obsidian/standards/backend/layer/api-layer-standards.md` | TODO | merged (response envelope) |
| `docs/standards/backend/configuration-and-secrets.md` | `docs/Obsidian/standards/backend/configuration-and-secrets.md` | TODO | - |
| `docs/standards/backend/database-migrations.md` | `docs/Obsidian/standards/backend/database-migrations.md` | TODO | - |
| `docs/standards/backend/error-message-schema-unification.md` | `docs/Obsidian/standards/backend/error-message-schema-unification.md` | TODO | - |
| `docs/standards/backend/request-payload-and-schema-validation.md` | `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md` | TODO | - |
| `docs/standards/backend/sensitive-data-handling.md` | `docs/Obsidian/standards/backend/sensitive-data-handling.md` | TODO | - |
| `docs/standards/backend/task-and-scheduler.md` | `docs/Obsidian/standards/backend/task-and-scheduler.md` | TODO | - |
| `docs/standards/backend/write-operation-boundary.md` | `docs/Obsidian/standards/backend/write-operation-boundary.md` | TODO | - |
| `docs/standards/ui/README.md` | `docs/Obsidian/standards/ui/README.md` | TODO | UI standards 索引 |
| `docs/standards/ui/async-task-feedback-guidelines.md` | `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md` | TODO | - |
| `docs/standards/ui/button-hierarchy-guidelines.md` | `docs/Obsidian/standards/ui/button-hierarchy-guidelines.md` | TODO | - |
| `docs/standards/ui/close-button-accessible-name-guidelines.md` | `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md` | TODO | - |
| `docs/standards/ui/color-guidelines.md` | `docs/Obsidian/standards/ui/color-guidelines.md` | TODO | - |
| `docs/standards/ui/component-dom-id-scope-guidelines.md` | `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md` | TODO | - |
| `docs/standards/ui/danger-operation-confirmation-guidelines.md` | `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md` | TODO | - |
| `docs/standards/ui/design-token-governance-guidelines.md` | `docs/Obsidian/standards/ui/design-token-governance-guidelines.md` | TODO | - |
| `docs/standards/ui/grid-list-page-skeleton-guidelines.md` | `docs/Obsidian/standards/ui/grid-list-page-skeleton-guidelines.md` | TODO | - |
| `docs/standards/ui/grid-wrapper-performance-logging-guidelines.md` | `docs/Obsidian/standards/ui/grid-wrapper-performance-logging-guidelines.md` | TODO | - |
| `docs/standards/ui/gridjs-migration-standard.md` | `docs/Obsidian/standards/ui/gridjs-migration-standard.md` | TODO | - |
| `docs/standards/ui/javascript-module-standards.md` | `docs/Obsidian/standards/ui/javascript-module-standards.md` | TODO | - |
| `docs/standards/ui/layout-sizing-guidelines.md` | `docs/Obsidian/standards/ui/layout-sizing-guidelines.md` | TODO | - |
| `docs/standards/ui/pagination-sorting-parameter-guidelines.md` | `docs/Obsidian/standards/ui/pagination-sorting-parameter-guidelines.md` | TODO | - |

---

## 1. 写作与结构模板(Obsidian Markdown)

> 目标: 所有 `docs/Obsidian/standards/**/*.md` 都满足:
> - 有 YAML frontmatter(可检索/可链接/可维护)
> - 有清晰的 "Scope / Rules / Examples / References" 结构
> - 内部引用优先使用 wikilinks, 代码/路径/命令使用 inline code

### 1.1 Frontmatter 模板

```yaml
---
title: <中文标题(可带英文副标题)>
aliases:
  - <kebab-case-basename>
tags:
  - standards
  - standards/<backend|ui|general>
status: draft
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: WhaleFall Team
scope: <一句话范围>
related:
  - <相对路径或说明>
---
```

### 1.2 正文最小结构模板

- `# {title}`
- `> [!note]` 或 `> [!info]` 说明 SSOT/适用范围
- `## 目的`
- `## 适用范围`
- `## 规则`
- `## 示例`(可选)
- `## 门禁/检查方式`(可选)
- `## 变更历史`(保留原日期, updated 用本次迁移日期)

---

## 2. 执行步骤(按 Task 拆分)

### Task 1: 迁移目录(保留 git 历史)

**Files:**
- Move: `docs/standards/**` -> `docs/Obsidian/standards/**`
- Modify: `docs/Obsidian/README.md`

**Step 1: git mv 整体目录**

Run:
```bash
git mv docs/standards docs/Obsidian/standards
```
Expected: `git status` 显示大量 rename.

**Step 2: 更新 Obsidian vault 说明**

Modify `docs/Obsidian/README.md`: 增加 `standards/` 的约定与入口链接.

**Step 3: Commit**

Run:
```bash
git add docs/Obsidian/standards docs/Obsidian/README.md
git commit -m "docs: move standards into Obsidian vault"
```

### Task 2: 重写核心 standards(Obsidian Markdown)

**Files:**
- Rewrite:
  - `docs/Obsidian/standards/README.md`
  - `docs/Obsidian/standards/doc/documentation-standards.md`
  - `docs/Obsidian/standards/halfwidth-character-standards.md`
  - `docs/Obsidian/standards/coding-standards.md`
  - `docs/Obsidian/standards/naming-standards.md`
  - `docs/Obsidian/standards/testing-standards.md`
  - `docs/Obsidian/standards/git-workflow-standards.md`
  - `docs/Obsidian/standards/scripts-standards.md`
  - `docs/Obsidian/standards/terminology.md`
  - `docs/Obsidian/standards/doc/changes-standards.md`
  - `docs/Obsidian/standards/new-feature-delivery-standard.md`
  - `docs/Obsidian/standards/version-update-guide.md`

**Step 1: 按 Obsidian 模板重写每个文档**

- 将原 `> 状态/负责人/创建/更新/范围/关联` 转为 YAML frontmatter.
- 将文内引用统一为新路径, 并在 `docs/Obsidian/**` 内优先使用 `[[standards/...]]`.
- 更新与本次迁移相关的描述(例如 `documentation-standards` 中 "规范标准" 目录不再是 `docs/standards/`).

**Step 2: Commit(建议按 3-4 个文件一组)**

Run:
```bash
git add docs/Obsidian/standards
git commit -m "docs: rewrite core standards as Obsidian notes"
```

### Task 3: 重写 backend standards(Obsidian Markdown)

**Files:**
- Rewrite: `docs/Obsidian/standards/backend/**`

**Step 1: 重写每个 backend 文档**

- 统一 frontmatter 字段(尤其是 status/created/updated/related).
- 将 cross-links 更新为 `[[standards/backend/<name>]]` 或 `[[standards/<name>]]`.

**Step 2: Commit**

```bash
git add docs/Obsidian/standards/backend
git commit -m "docs: rewrite backend standards as Obsidian notes"
```

### Task 4: 重写 ui standards(Obsidian Markdown)

**Files:**
- Rewrite: `docs/Obsidian/standards/ui/**`

**Step 1: 重写每个 UI 文档**

- 统一 frontmatter 与章节结构.
- 与代码/脚本的路径引用统一为 inline code, 避免歧义.

**Step 2: Commit**

```bash
git add docs/Obsidian/standards/ui
git commit -m "docs: rewrite UI standards as Obsidian notes"
```

### Task 5: 全仓库更新引用(从 docs/standards -> docs/Obsidian/standards)

**Files:**
- Modify (examples, non-exhaustive):
  - `AGENTS.md`
  - `CLAUDE.md`
  - `README.md`
  - `CONTRIBUTING.md`
  - `docs/README.md`
  - `docs/plans/README.md`
  - `scripts/README.md`
  - `scripts/ci/*.sh`
  - `docs/**` (architecture/prompts/changes/reports 等)
  - `docs/Obsidian/canvas/**` (若含旧路径引用)

**Step 1: 扫描旧引用**

Run: `rg -n "docs/standards" -S .`
Expected: 仅剩计划保留的 legacy 描述(否则逐条修复).

**Step 2: 批量替换路径**

将 `docs/standards/...` 替换为 `docs/Obsidian/standards/...`.

**Step 3: 处理 Markdown 链接与 Obsidian wikilinks 的差异**

- `docs/Obsidian/**` 内: 优先使用 `[[standards/...]]`.
- 仓库其他 `docs/**`/根目录文件: 继续使用可点击的相对路径 Markdown 链接(例如 `(docs/Obsidian/standards/...)`), 避免 GitHub 渲染断链.

**Step 4: Commit**

```bash
git add AGENTS.md CLAUDE.md README.md CONTRIBUTING.md docs scripts
git commit -m "docs: repoint standards links to Obsidian standards"
```

### Task 6: 移除旧目录 + 最终校验

**Files:**
- Ensure removed: `docs/standards/**`(应在 Task 1 后不存在)
- (Optional) Create: `scripts/ci/no-legacy-standards-dir.sh` (禁止回归)

**Step 1: 确认旧目录不存在**

Run:
```bash
test ! -e docs/standards
```
Expected: 命令返回 0.

**Step 2: 最终扫描**

Run:
```bash
rg -n "docs/standards" -S . || true
```
Expected: 无输出(或仅允许明确标注 legacy 的一两处, 且指向新 SSOT).

**Step 3: 运行基础验证(可选但推荐)**

Run: `uv run pytest -m unit`
Expected: PASS(文档改动不应影响单测).

**Step 4: Commit**

```bash
git add -A
git commit -m "docs: move standards into Obsidian vault"
```

---

## 3. Definition of Done

- `docs/Obsidian/standards/**` 覆盖原 `docs/standards/**` 全量文档, 且每篇满足 frontmatter + 最小结构模板.
- 仓库内不再引用 `docs/standards/**` 路径.
- `docs/README.md` 与 root 文档入口均指向新的 standards 位置.
- (若执行了可选项) CI/脚本层面阻止新增 `docs/standards/` 回归.
