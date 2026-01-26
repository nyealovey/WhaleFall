# Standards Docs Reorg Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `docs/Obsidian/standards/**` 按“领域优先(core/backend/ui/doc) -> enforcement(hard/gate/guide/design)”重排，并统一文件名为不带 `-standards/-guidelines/-guide` 后缀的 kebab-case；同时全仓更新引用，避免断链。

**Architecture:** 保留各领域 `README.md` 作为索引入口；其余文档移动到 `<domain>/<enforcement>/...` 下。通过 `git mv` 保留历史，随后用 `rg` 批量更新 Obsidian wikilinks 与仓库内 Markdown 路径引用，最后做一次全仓“旧路径/旧文件名”残留扫描。

**Tech Stack:** Git、Obsidian Markdown、ripgrep(`rg`)

---

### Task 1: 新目录骨架

**Files:**
- Create: `docs/Obsidian/standards/core/.gitkeep` (仅在 Git 需要时)
- Create: `docs/Obsidian/standards/core/standard/.gitkeep`
- Create: `docs/Obsidian/standards/core/gate/.gitkeep`
- Create: `docs/Obsidian/standards/core/guide/.gitkeep`
- Create: `docs/Obsidian/standards/core/design/.gitkeep`
- Create: `docs/Obsidian/standards/backend/standard/.gitkeep`
- Create: `docs/Obsidian/standards/backend/gate/.gitkeep`
- Create: `docs/Obsidian/standards/backend/guide/.gitkeep`
- Create: `docs/Obsidian/standards/backend/design/.gitkeep`
- Create: `docs/Obsidian/standards/ui/hard/.gitkeep`
- Create: `docs/Obsidian/standards/ui/gate/.gitkeep`
- Create: `docs/Obsidian/standards/ui/guide/.gitkeep`
- Create: `docs/Obsidian/standards/ui/design/.gitkeep`
- Create: `docs/Obsidian/standards/doc/hard/.gitkeep`
- Create: `docs/Obsidian/standards/doc/gate/.gitkeep`
- Create: `docs/Obsidian/standards/doc/guide/.gitkeep`
- Create: `docs/Obsidian/standards/doc/design/.gitkeep`

**Step 1: 创建目录**

Run:
```bash
mkdir -p docs/Obsidian/standards/{core,backend,ui,doc}/{hard,gate,guide,design}
```

Expected: 目录创建成功；不产生文档内容变更。

---

### Task 2: core 文档移动 + 重命名

**Files:**
- Move: `docs/Obsidian/standards/standards-governance.md` -> `docs/Obsidian/standards/core/standard/governance.md`
- Move: `docs/Obsidian/standards/naming-standards.md` -> `docs/Obsidian/standards/core/gate/naming.md`
- Move: `docs/Obsidian/standards/coding-standards.md` -> `docs/Obsidian/standards/core/guide/coding.md`
- Move: `docs/Obsidian/standards/git-workflow-standards.md` -> `docs/Obsidian/standards/core/guide/git-workflow.md`
- Move: `docs/Obsidian/standards/testing-standards.md` -> `docs/Obsidian/standards/core/guide/testing.md`
- Move: `docs/Obsidian/standards/terminology.md` -> `docs/Obsidian/standards/core/guide/terminology.md`
- Move: `docs/Obsidian/standards/halfwidth-character-standards.md` -> `docs/Obsidian/standards/core/guide/halfwidth-characters.md`
- Move: `docs/Obsidian/standards/scripts-standards.md` -> `docs/Obsidian/standards/core/guide/scripts.md`
- Move: `docs/Obsidian/standards/version-update-guide.md` -> `docs/Obsidian/standards/core/guide/version-update.md`
- Move: `docs/Obsidian/standards/new-feature-delivery-standard.md` -> `docs/Obsidian/standards/core/guide/new-feature-delivery.md`

**Step 1: git mv**

Run:
```bash
git mv docs/Obsidian/standards/standards-governance.md docs/Obsidian/standards/core/standard/governance.md
git mv docs/Obsidian/standards/naming-standards.md docs/Obsidian/standards/core/gate/naming.md
git mv docs/Obsidian/standards/coding-standards.md docs/Obsidian/standards/core/guide/coding.md
git mv docs/Obsidian/standards/git-workflow-standards.md docs/Obsidian/standards/core/guide/git-workflow.md
git mv docs/Obsidian/standards/testing-standards.md docs/Obsidian/standards/core/guide/testing.md
git mv docs/Obsidian/standards/terminology.md docs/Obsidian/standards/core/guide/terminology.md
git mv docs/Obsidian/standards/halfwidth-character-standards.md docs/Obsidian/standards/core/guide/halfwidth-characters.md
git mv docs/Obsidian/standards/scripts-standards.md docs/Obsidian/standards/core/guide/scripts.md
git mv docs/Obsidian/standards/version-update-guide.md docs/Obsidian/standards/core/guide/version-update.md
git mv docs/Obsidian/standards/new-feature-delivery-standard.md docs/Obsidian/standards/core/guide/new-feature-delivery.md
```

Expected: `git status` 显示为 rename/move。

**Step 2: 更新 YAML aliases/related（保留旧名 alias）**

Run:
```bash
rg -n \"aliases:|related:\" docs/Obsidian/standards/core -S
```

Expected: 每个移动的文件保留旧文件名作为 alias，且 related 链接更新为新路径。

---

### Task 3: doc 文档移动 + 重命名

**Files:**
- Move: `docs/Obsidian/standards/doc/documentation-standards.md` -> `docs/Obsidian/standards/doc/guide/documentation.md`
- Move: `docs/Obsidian/standards/doc/document-boundary-standards.md` -> `docs/Obsidian/standards/doc/guide/document-boundary.md`
- Move: `docs/Obsidian/standards/doc/changes-standards.md` -> `docs/Obsidian/standards/doc/guide/changes.md`
- Move: `docs/Obsidian/standards/doc/service-layer-documentation-standards.md` -> `docs/Obsidian/standards/doc/guide/service-layer-documentation.md`
- Move: `docs/Obsidian/standards/doc/api-contract-markdown-standards.md` -> `docs/Obsidian/standards/doc/guide/api-contract-markdown.md`

**Step 1: git mv**

Run:
```bash
git mv docs/Obsidian/standards/doc/documentation-standards.md docs/Obsidian/standards/doc/guide/documentation.md
git mv docs/Obsidian/standards/doc/document-boundary-standards.md docs/Obsidian/standards/doc/guide/document-boundary.md
git mv docs/Obsidian/standards/doc/changes-standards.md docs/Obsidian/standards/doc/guide/changes.md
git mv docs/Obsidian/standards/doc/service-layer-documentation-standards.md docs/Obsidian/standards/doc/guide/service-layer-documentation.md
git mv docs/Obsidian/standards/doc/api-contract-markdown-standards.md docs/Obsidian/standards/doc/guide/api-contract-markdown.md
```

**Step 2: 更新 doc/README.md 内部链接**

Run:
```bash
rg -n \"\\[\\[standards/doc/\" docs/Obsidian/standards/doc/README.md -n
```

Expected: 所有链接指向 `standards/doc/guide/...` 新路径。

---

### Task 4: backend 文档移动 + 重命名（含 layer）

**Files:**
- Move (hard): `action-endpoint-failure-semantics.md` -> `backend/hard/action-endpoint-failure-semantics.md`
- Move (gate): `bootstrap-and-entrypoint.md` -> `backend/gate/bootstrap-and-entrypoint.md`
- Move (design): `compatibility-and-deprecation.md` -> `backend/design/compatibility-and-deprecation.md`
- Move (hard): `configuration-and-secrets.md` -> `backend/hard/configuration-and-secrets.md`
- Move (hard): `database-migrations.md` -> `backend/hard/database-migrations.md`
- Move (hard): `error-message-schema-unification.md` -> `backend/hard/error-message-schema-unification.md`
- Move (gate): `internal-data-contract-and-versioning.md` -> `backend/gate/internal-data-contract-and-versioning.md`
- Move (gate): `or-fallback-decision-table.md` -> `backend/gate/or-fallback-decision-table.md`
- Move (gate): `request-payload-and-schema-validation.md` -> `backend/gate/request-payload-and-schema-validation.md`
- Move (guide): `resilience-and-fallback-standards.md` -> `backend/guide/resilience-and-fallback.md`
- Move (hard): `sensitive-data-handling.md` -> `backend/hard/sensitive-data-handling.md`
- Move (design): `shared-kernel-standards.md` -> `backend/design/shared-kernel.md`
- Move (guide): `structured-logging-context-fields.md` -> `backend/guide/structured-logging-context-fields.md`
- Move (guide): `structured-logging-minimum-fields.md` -> `backend/guide/structured-logging-minimum-fields.md`
- Move (hard): `task-and-scheduler.md` -> `backend/hard/task-and-scheduler.md`
- Move (hard): `write-operation-boundary.md` -> `backend/hard/write-operation-boundary.md`
- Move (gate): `yaml-config-validation.md` -> `backend/gate/yaml-config-validation.md`
- Move (layer): `backend/layer/*` -> `backend/<enforcement>/layer/*`（按各文件 frontmatter）

**Step 1: git mv（非 layer）**：逐个执行，避免一次性出错难排查。

**Step 2: layer 子目录迁移**：按文件 `enforcement` 分组移动到对应 `<enforcement>/layer/`。

**Step 3: 更新 backend/README.md 与相关文档的 wikilinks**。

---

### Task 5: ui 文档移动 + 重命名（含 layer + modal-crud-forms）

**Files:**
- Move (design): `docs/Obsidian/standards/modal-crud-forms-standards.md` -> `docs/Obsidian/standards/ui/design/modal-crud-forms.md`
- Move: `docs/Obsidian/standards/ui/*.md` -> `docs/Obsidian/standards/ui/<enforcement>/*.md`（按各文件 frontmatter）
- Move (layer): `docs/Obsidian/standards/ui/layer/*` -> `docs/Obsidian/standards/ui/<enforcement>/layer/*`

**Step 1: git mv + 重命名**

**Step 2: 更新 ui/README.md 的入口链接**

---

### Task 6: 全仓引用更新（Obsidian wikilinks + Markdown path）

**Files:**
- Modify: `docs/Obsidian/standards/README.md`
- Modify: `docs/Obsidian/standards/backend/README.md`
- Modify: `docs/Obsidian/standards/ui/README.md`
- Modify: `AGENTS.md`
- Modify: `CONTRIBUTING.md`
- Modify: `README.md`
- Modify: `docs/agent/README.md`（如有引用）
- Modify: 其他命中 `rg` 的文件

**Step 1: 批量扫描旧路径/旧文件名**

Run:
```bash
rg -n \"docs/Obsidian/standards/|\\[\\[standards/\" -S
```

**Step 2: 逐条替换为新路径**

原则：优先改成新路径；同时为每个移动文件在 frontmatter `aliases` 中保留旧文件名（不带路径）以兼容历史引用。

---

### Task 7: 验证（防断链）

**Step 1: 检查旧文件名残留**

Run（示例，按实际旧名补充）：
```bash
rg -n \"coding-standards|naming-standards|standards-governance|grid-standards|documentation-standards\" -S
```

Expected: 除了 alias/变更记录，不应再出现旧路径引用。

**Step 2: 检查旧目录残留**

Run:
```bash
find docs/Obsidian/standards -maxdepth 2 -type d -print
```

Expected: `core/backend/ui/doc` 下只保留 `hard/gate/guide/design`（外加各自 `README.md`）。

---

### Task 8: 变更整理（可选）

**Step 1: git status / git diff 检查**

Run:
```bash
git status
git diff --stat
```

Expected: 以 rename/move 为主；少量内容修改用于更新链接与 aliases。

