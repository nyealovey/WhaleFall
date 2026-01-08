---
title: WhaleFall 变更文档(docs/changes)规范
aliases:
  - changes-standards
tags:
  - standards
  - standards/general
status: active
created: 2025-12-25
updated: 2026-01-08
owner: WhaleFall Team
scope: "`docs/changes/**` 下所有变更文档(含后续新增)"
related:
  - "[[standards/documentation-standards]]"
---

# WhaleFall 变更文档(docs/changes)规范

---

## 1. 目的

- 把“为什么改 / 改了什么 / 怎么验收 / 怎么回滚”沉淀为可追踪文档，与 PR/Issue 对齐。
- 明确 `plan`（方案）与 `progress`（进度）两类文档的边界，支持跨多 PR 的持续推进。
- 统一目录与命名，降低检索成本，避免“同一件事写多份、进度散落在评论/聊天”。

## 2. 目录结构（标准）

`docs/changes/` 下按变更类型分目录：

```text
docs/changes/
├── README.md
├── refactor/    # 重构（行为不变的结构调整）
├── bugfix/      # 修复（缺陷修复）
├── docs/        # 文档（新增/调整/规范更新）
├── feature/     # 新增功能
├── perf/        # 性能专项
└── security/    # 安全治理/修补
```

> 约束：禁止在 `docs/changes/` 下新增与上述并列的“新一级目录”。如确需新增，必须先更新本规范与 `docs/changes/README.md`。

## 3. 文档类型（plan / progress / record）

### 3.1 `plan`：方案文档（MUST when multi-PR）

适用场景：

- 变更预期会拆成多个 PR（多阶段/多模块/跨多人协作）。
- 需要明确边界、验收口径、回滚策略、风险点。

强约束：

- MUST：文件名以 `-plan.md` 结尾。
- MUST：包含“分阶段计划”（每阶段验收口径/验证命令）。
- MUST：明确“不变约束”（行为/契约/性能门槛等）。

### 3.2 `progress`：进度文档（MUST when multi-PR）

适用场景：

- 与 `plan` 配套，记录落地进度与剩余工作（Checklist + 变更记录）。

强约束：

- MUST：文件名以 `-progress.md` 结尾。
- MUST：标题下方第一屏明确“关联方案（plan）”的相对路径链接。
- MUST：每次推进（合并 PR / 阶段完成）都更新“最后更新”日期，并追加“变更记录”条目。

### 3.3 `record`：单次变更记录（默认）

适用场景：

- 单 PR 即可完成，且不需要长期跟踪进度（多数 bugfix、文档修订属于此类）。

强约束：

- MUST：写清“验证与测试”“风险与回滚”。

## 4. 命名与编号规则

### 4.1 编号（MUST）

- MUST：`docs/changes/**` 下新增文档文件名必须带三位编号前缀，从 `001` 开始递增；每个子目录独立计数。

### 4.2 文件名（MUST）

- 单次记录：`NNN-short-title.md`
- 方案文档：`NNN-short-title-plan.md`
- 进度文档：`NNN-short-title-progress.md`

> 约束：`short-title` 必须为英文 `kebab-case`，同一项计划的 `plan/progress` 必须共享相同的 `NNN-short-title` 前缀。

参考示例（已有实践）：

- `docs/changes/refactor/001-backend-repository-serializer-boundary-plan.md`
- `docs/changes/refactor/001-backend-repository-serializer-boundary-progress.md`
- `docs/changes/refactor/002-backend-write-operation-boundary-plan.md`

## 5. 最小结构（模板）

### 5.1 `refactor/*-plan.md`（重构方案）

必填章节：

- 动机与范围
- 不变约束（行为/契约/性能门槛）
- 分层边界（依赖方向/禁止项）
- 分阶段计划（每阶段验收口径）
- 风险与回滚
- 验证与门禁

### 5.2 `refactor/*-progress.md`（重构进度）

必填章节：

- 当前状态（摘要）
- Checklist（按 Phase 分组，使用 `[ ]/[x]`）
- 变更记录（按日期追加）

### 5.3 `bugfix/*.md`（修复记录）

必填章节：

- 症状与影响
- 复现步骤
- 根因分析
- 修复方案
- 回归验证
- 风险与回滚

> 如修复跨多 PR 推进，允许升级为 `*-plan.md` + `*-progress.md`。

### 5.4 `docs/*.md`（文档变更）

必填章节：

- 背景与目标（为什么要改）
- 变更清单（新增/删除/移动/重命名的文档与路径）
- 受影响入口（`docs/README.md`、目录 `README.md`、链接引用）
- 验证方式（至少包含：断链检查/关键路径可读性复核）
- 回滚策略（如何恢复到改动前）

## 6. 与 PR/Issue 的对齐规则

- MUST：每个 PR 描述里必须链接到对应的 `docs/changes/**` 文档。
- MUST：若使用 `progress` 文档推进，每次合并 PR 必须更新一次进度（Checklist + 变更记录）。
- SHOULD：一个计划（`plan/progress`）对应一个编号（`NNN`），避免多编号碎片化描述同一主题。

## 7. 生命周期与归档

- `Draft`：方案/进度仍在讨论或推进中。
- `Active`：正在推进，且是当前真源。
- `Archived`：变更完成且无需继续更新；按 [[standards/documentation-standards]] 的归档规则迁移到 `docs/_archive/changes/<category>/YYYY/`。

## 8. 门禁/检查建议（可选）

如后续需要自动化门禁，建议覆盖：

- `docs/changes/**` 新增文件名是否满足 `NNN-*-{plan|progress}.md` 规则。
- `progress` 文档是否包含“关联方案”链接与“最后更新”字段。
- `docs/*.md` 是否包含“变更清单/验证方式/回滚策略”章节。

## 9. 变更历史

- 2025-12-25：建立 `docs/changes` 的目录类型（含 docs）与 `plan/progress` 规范。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
