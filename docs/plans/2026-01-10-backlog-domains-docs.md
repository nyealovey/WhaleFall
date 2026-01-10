# Backlog Domain Docs + Canvas Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 补齐 `docs/Obsidian/architecture/README.md` 中 3 个 backlog domain notes, 并为新增 Mermaid 图补齐对应 `.canvas`(双向互链).

**Architecture:** 以 as-built 代码为准, 每个 domain 文档包含: 边界/职责, 入口与落点, 关键 endpoints, 常见坑与排障锚点, 以及最少 1 张 Mermaid 图 + 对应 Canvas.

**Tech Stack:** Obsidian Markdown(wikilinks + frontmatter), Mermaid, JSON Canvas.

---

## Task 1: 盘点缺口与命名

**Files:**
- Modify: `docs/Obsidian/architecture/README.md`
- Modify: `docs/Obsidian/canvas/README.md`

**Steps:**
1) 确认 backlog: `databases-ledger-domain`, `files-exports`, `dashboard-domain`.
2) 决定文件命名:
   - `docs/Obsidian/architecture/databases-ledger-domain.md`
   - `docs/Obsidian/architecture/files-exports-domain.md`(aliases: `files-exports`)
   - `docs/Obsidian/architecture/dashboard-domain.md`

---

## Task 2: 新增 databases ledger domain 文档 + 图 + canvas

**Files:**
- Create: `docs/Obsidian/architecture/databases-ledger-domain.md`
- Create: `docs/Obsidian/canvas/databases-ledger/databases-ledger-domain-components.canvas`
- Create: `docs/Obsidian/canvas/databases-ledger/databases-ledger-flow.canvas`

**Steps:**
1) 写 domain 边界与职责, 列出 Web/UI/API/Service/Repo/Model 的落点.
2) 增加 Mermaid(components + flow), 并在图下方写 `Canvas: [[canvas/...]]`.
3) 创建对应 `.canvas`, 含 `file` node 回链到文档并指向对应小节标题.

---

## Task 3: 新增 files exports domain 文档 + 图 + canvas

**Files:**
- Create: `docs/Obsidian/architecture/files-exports-domain.md`
- Create: `docs/Obsidian/canvas/files/files-exports-flow.canvas`

**Steps:**
1) 明确这是 cross-cutting capability: CSV exports + template download.
2) 解释 "成功返回 CSV, 失败仍返回 JSON envelope" 的 contract 口径与实现落点.
3) 强调 CSV 公式注入防护(`sanitize_csv_row`).
4) 增加 Mermaid(flow), 并创建对应 canvas(双向互链).

---

## Task 4: 新增 dashboard domain 文档 + 图 + canvas

**Files:**
- Create: `docs/Obsidian/architecture/dashboard-domain.md`
- Create: `docs/Obsidian/canvas/dashboard/dashboard-domain-components.canvas`

**Steps:**
1) 描述 Web `/` 与 API `/api/v1/dashboard/*` 的边界与缓存策略.
2) 列出关键 services/repositories 与典型排障锚点(缓存, DB rollback, health checks).
3) 增加 Mermaid(components), 并创建对应 canvas(双向互链).

---

## Task 5: 更新索引与清理

**Files:**
- Modify: `docs/Obsidian/architecture/README.md`
- Modify: `docs/Obsidian/canvas/README.md`

**Steps:**
1) 将 3 个 backlog 项移动到 "Domain notes" 并改为 wikilinks.
2) 视情况移除空的 Backlog notes 小节或标记为 "无".
3) 给 Canvas README 增加 3 组 canvas 索引.

---

## Task 6: 校验与验证

**Steps:**
1) Mermaid 校验:
   - `~/.codex/skills/mermaid-diagrams-4/scripts/validate_mermaid.sh docs/Obsidian/architecture/databases-ledger-domain.md`
   - `~/.codex/skills/mermaid-diagrams-4/scripts/validate_mermaid.sh docs/Obsidian/architecture/files-exports-domain.md`
   - `~/.codex/skills/mermaid-diagrams-4/scripts/validate_mermaid.sh docs/Obsidian/architecture/dashboard-domain.md`
2) Canvas JSON 校验:
   - `python3 -m json.tool docs/Obsidian/canvas/**/**/*.canvas >/dev/null`
3) 基本回归:
   - `uv run pytest -m unit`

