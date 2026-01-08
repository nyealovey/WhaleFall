# Standards -> Obsidian Standards Migration Progress

> 状态: Completed
> 负责人: WhaleFall Team
> 创建: 2026-01-08
> 更新: 2026-01-08
> 范围: `docs/standards/**` -> `docs/Obsidian/standards/**`
> 关联: `docs/plans/2026-01-08-standards-to-obsidian-standards.md`

## Milestones

- [x] Task 1: 迁移目录(保留 git 历史)
- [x] Task 2: 重写核心 standards(Obsidian Markdown)
- [x] Task 3: 重写 backend standards(Obsidian Markdown)
- [x] Task 4: 重写 ui standards(Obsidian Markdown)
- [x] Task 5: 全仓库更新引用(从 docs/standards -> docs/Obsidian/standards)
- [x] Task 6: 最终校验 + 清理 legacy

## Timeline（建议）

> 说明：这是“工作日”节奏建议；实际可根据写作/评审资源压缩或拆分。日期以 2026-01-08 为起点。

| Day | Date | Focus | Exit Criteria |
| --- | --- | --- | --- |
| D0 | 2026-01-08 | 明确 SSOT、盘点文件、冻结旧入口 | 本文件 + Implementation Plan 完整、文件清单无遗漏 |
| D1 | 2026-01-09 | Task 1 + Task 2（核心 standards） | `docs/Obsidian/standards/*` 重写完成；`docs/Obsidian/README.md` 补入口 |
| D2 | 2026-01-10 | Task 3（backend standards） | `docs/Obsidian/standards/backend/*` 重写完成；内部 wikilinks 连通 |
| D3 | 2026-01-11 | Task 4（ui standards）+ Task 5（全仓库引用） | `rg -n "docs/standards" -S .` 仅剩 legacy 允许项或 0 命中 |
| D4 | 2026-01-12 | Task 6（最终校验/清理） | `docs/standards/` 不存在；可选单测通过；DoD 全满足 |

## File-level Progress

> 说明: `Status` 建议使用 `TODO / DOING / DONE / BLOCKED`.

| Old Path | New Path | Status | Notes |
| --- | --- | --- | --- |
| `docs/standards/README.md` | `docs/Obsidian/standards/README.md` | DONE | 新的 standards 入口与索引 |
| `docs/standards/documentation-standards.md` | `docs/Obsidian/standards/documentation-standards.md` | DONE | 需要重写目录结构描述(standards 已迁移) |
| `docs/standards/halfwidth-character-standards.md` | `docs/Obsidian/standards/halfwidth-character-standards.md` | DONE | 更新路径与检查规则描述 |
| `docs/standards/coding-standards.md` | `docs/Obsidian/standards/coding-standards.md` | DONE | 统一链接写法与例子 |
| `docs/standards/naming-standards.md` | `docs/Obsidian/standards/naming-standards.md` | DONE | 更新所有引用路径 |
| `docs/standards/testing-standards.md` | `docs/Obsidian/standards/testing-standards.md` | DONE | 更新测试命令引用 |
| `docs/standards/git-workflow-standards.md` | `docs/Obsidian/standards/git-workflow-standards.md` | DONE | 更新 references |
| `docs/standards/scripts-standards.md` | `docs/Obsidian/standards/scripts-standards.md` | DONE | 更新 references |
| `docs/standards/terminology.md` | `docs/Obsidian/standards/terminology.md` | DONE | 转为 Obsidian 术语表格式 |
| `docs/standards/changes-standards.md` | `docs/Obsidian/standards/changes-standards.md` | DONE | 与 changes 目录索引互链 |
| `docs/standards/new-feature-delivery-standard.md` | `docs/Obsidian/standards/new-feature-delivery-standard.md` | DONE | 更新“上升为标准”路径 |
| `docs/standards/version-update-guide.md` | `docs/Obsidian/standards/version-update-guide.md` | DONE | 与发版 skill/脚本互链 |
| `docs/standards/backend/README.md` | `docs/Obsidian/standards/backend/README.md` | DONE | backend standards 索引 |
| `docs/standards/backend/action-endpoint-failure-semantics.md` | `docs/Obsidian/standards/backend/action-endpoint-failure-semantics.md` | DONE | - |
| `docs/standards/backend/api-contract-canvas-standards.md` | - | DONE | 标准已取消，迁移后已删除（不再保留 legacy 记录） |
| `docs/standards/backend/api-contract-markdown-standards.md` | `docs/Obsidian/standards/backend/api-contract-markdown-standards.md` | DONE | SSOT 标准 |
| `docs/standards/backend/api-naming-standards.md` | `docs/Obsidian/standards/backend/api-naming-standards.md` | DONE | - |
| `docs/standards/backend/api-response-envelope.md` | `docs/Obsidian/standards/backend/api-response-envelope.md` | DONE | - |
| `docs/standards/backend/configuration-and-secrets.md` | `docs/Obsidian/standards/backend/configuration-and-secrets.md` | DONE | - |
| `docs/standards/backend/database-migrations.md` | `docs/Obsidian/standards/backend/database-migrations.md` | DONE | - |
| `docs/standards/backend/error-message-schema-unification.md` | `docs/Obsidian/standards/backend/error-message-schema-unification.md` | DONE | - |
| `docs/standards/backend/request-payload-and-schema-validation.md` | `docs/Obsidian/standards/backend/request-payload-and-schema-validation.md` | DONE | - |
| `docs/standards/backend/sensitive-data-handling.md` | `docs/Obsidian/standards/backend/sensitive-data-handling.md` | DONE | - |
| `docs/standards/backend/task-and-scheduler.md` | `docs/Obsidian/standards/backend/task-and-scheduler.md` | DONE | - |
| `docs/standards/backend/write-operation-boundary.md` | `docs/Obsidian/standards/backend/write-operation-boundary.md` | DONE | - |
| `docs/standards/ui/README.md` | `docs/Obsidian/standards/ui/README.md` | DONE | UI standards 索引 |
| `docs/standards/ui/async-task-feedback-guidelines.md` | `docs/Obsidian/standards/ui/async-task-feedback-guidelines.md` | DONE | - |
| `docs/standards/ui/button-hierarchy-guidelines.md` | `docs/Obsidian/standards/ui/button-hierarchy-guidelines.md` | DONE | - |
| `docs/standards/ui/close-button-accessible-name-guidelines.md` | `docs/Obsidian/standards/ui/close-button-accessible-name-guidelines.md` | DONE | - |
| `docs/standards/ui/color-guidelines.md` | `docs/Obsidian/standards/ui/color-guidelines.md` | DONE | - |
| `docs/standards/ui/component-dom-id-scope-guidelines.md` | `docs/Obsidian/standards/ui/component-dom-id-scope-guidelines.md` | DONE | - |
| `docs/standards/ui/danger-operation-confirmation-guidelines.md` | `docs/Obsidian/standards/ui/danger-operation-confirmation-guidelines.md` | DONE | - |
| `docs/standards/ui/design-token-governance-guidelines.md` | `docs/Obsidian/standards/ui/design-token-governance-guidelines.md` | DONE | - |
| `docs/standards/ui/grid-list-page-skeleton-guidelines.md` | `docs/Obsidian/standards/ui/grid-list-page-skeleton-guidelines.md` | DONE | - |
| `docs/standards/ui/grid-wrapper-performance-logging-guidelines.md` | `docs/Obsidian/standards/ui/grid-wrapper-performance-logging-guidelines.md` | DONE | - |
| `docs/standards/ui/gridjs-migration-standard.md` | `docs/Obsidian/standards/ui/gridjs-migration-standard.md` | DONE | - |
| `docs/standards/ui/javascript-module-standards.md` | `docs/Obsidian/standards/ui/javascript-module-standards.md` | DONE | - |
| `docs/standards/ui/layout-sizing-guidelines.md` | `docs/Obsidian/standards/ui/layout-sizing-guidelines.md` | DONE | - |
| `docs/standards/ui/pagination-sorting-parameter-guidelines.md` | `docs/Obsidian/standards/ui/pagination-sorting-parameter-guidelines.md` | DONE | - |
