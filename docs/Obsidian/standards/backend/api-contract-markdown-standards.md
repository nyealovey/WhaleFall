---
title: API Contract Markdown 标准(SSOT)
aliases:
  - api-contract-markdown-standards
tags:
  - standards
  - standards/backend
  - api/contract
status: active
created: 2026-01-08
updated: 2026-01-08
owner: WhaleFall Team
scope: "`/api/v1/**` 路由清单, `docs/Obsidian/API/**-api-contract.md`"
related:
  - "[[standards/backend/api-naming-standards]]"
  - "[[standards/documentation-standards]]"
  - "[[API/api-v1-api-contract]]"
  - "[[API/accounts-api-contract]]"
---

# API Contract Markdown 标准(SSOT)

## 1. 目的

- 为 `/api/v1/**` 的 API contract 提供单一真源(SSOT), 避免 contract 与代码实现漂移.
- 让评审者在 30 秒内确认: 新增/删除/改名的 endpoint 已同步更新 contract.
- 统一 contract 写法, 降低不同域之间的阅读与维护成本.

## 2. 适用范围

- MUST: 所有对外 JSON API(`/api/v1/**`) 的 endpoint 清单(method + path).
- MAY: 仅用于索引与审查, schema 细节仍以 OpenAPI 为准.
- MUST NOT: 将页面路由(HTML)与内部调试路由纳入本规范.

## 3. 规则

### 3.1 单一真源(SSOT)

- MUST: `/api/v1/**` 的 endpoint 清单以 `docs/Obsidian/API/**-api-contract.md` 为准.
- MUST: 每个 OpenAPI operation(method + path) 必须至少出现在 1 个 `**-api-contract.md` 的 "Endpoints 总览" 表格中.
- SHOULD: 同一个 operation 只出现在 1 个 contract 文档中; 如确需跨域重复, 必须在 Notes 说明原因.
- MUST NOT: 新增或继续维护 `docs/Obsidian/canvas/**-api-contract.canvas` 作为 contract SSOT. Canvas 仅允许作为历史遗留或辅助可视化.

### 3.2 文件位置与命名

- MUST: contract 文档放在 `docs/Obsidian/API/`.
- SHOULD: 文件名使用 `kebab-case` 并以 `-api-contract.md` 结尾, 例如 `accounts-api-contract.md`.
- MUST: 文档必须包含 YAML frontmatter(用于 Obsidian 元信息与检索), 且至少包含:
  - `title`
  - `aliases`(至少 1 个稳定 alias, 例如 `accounts-api-contract`)
  - `tags`(至少包含 `api/contract`)
  - `status`(draft/active/deprecated)
  - `created`/`updated`(YYYY-MM-DD)
  - `source_code`(对应的路由实现文件列表)

### 3.3 Endpoints 总览表(必须)

- MUST: 每个 contract 文档必须包含 "Endpoints 总览" 章节, 并使用 Markdown 表格维护 endpoint 清单.
- MUST: 表头列(顺序固定):

`| Method | Path | Purpose | Permission | CSRF | Notes |`

字段约定:

- `Method`: HTTP method, 全大写.
- `Path`: 必须包含 `/api/v1` 前缀, 并使用 OpenAPI 风格参数(例如 `/api/v1/users/{user_id}`).
- `Purpose`: 端点语义(一句话).
- `Permission`: `view/create/update/delete` 等权限动作(对应 `api_permission_required`).
- `CSRF`: `✅` 或 `-`(写接口要求 CSRF 时标记为 `✅`).
- `Notes`: 非显性约束与迁移说明(例如分页, side effects, 依赖前置条件).

CSRF 约定:

- MUST: 写接口(POST/PUT/PATCH/DELETE, 包含 action endpoints)默认需要 CSRF.
- MUST: CSRF token 仅允许通过 header `X-CSRFToken` 传递.
- MUST NOT: 通过 JSON body 传递 `csrf_token`.

### 3.4 详细说明(建议)

- SHOULD: 在 "Endpoints 总览" 之后按资源/子域拆分详细章节, 说明 query/body/响应关键字段与常见错误码.
- SHOULD: 提供 "快速导航" 并使用 Obsidian wikilink 链接到关键章节(参考 `accounts-api-contract.md`).

### 3.5 Obsidian 写作约束

- SHOULD: 使用 callouts 表达强提醒(例如 `> [!warning]`), 避免散落在段落里导致忽略.
- SHOULD: 使用 wikilink(`[[#Heading]]`) 形成可点击导航.
- MUST: contract 文档的可读性优先, 避免将 contract 写成代码生成物.

### 3.6 变更流程

- MUST: 任何新增/删除/改动 endpoint 的 PR, 必须同步更新受影响的 `docs/Obsidian/API/**-api-contract.md`.
- SHOULD: 同步更新 frontmatter 的 `updated` 日期.
- MAY: 在 contract 的 "Notes" 中记录重要迁移/弃用信息, 但不要求维护历史版本.
