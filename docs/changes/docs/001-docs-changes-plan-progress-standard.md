# 001 docs/changes：补齐 docs 类型与 plan/progress 进度文档规范

> 状态：Active
> 负责人：WhaleFall Team
> 创建：2025-12-25
> 更新：2025-12-25
> 范围：`docs/changes/**`、`docs/standards/**`
> 关联：`docs/changes/refactor/001-backend-repository-serializer-boundary-progress.md`、`docs/changes/refactor/002-backend-write-operation-boundary-plan.md`

---

## 背景与目标

`docs/changes/` 已有 `feature/bugfix/refactor/perf/security` 分类，但缺少“文档变更（docs）”的固定归档位置，也缺少对“多 PR 推进事项”的 `plan/progress` 配套规则，导致：

- 文档新增/调整散落在其他类型目录，检索困难。
- 多阶段推进的事项进度易散落在 PR 描述/评论中，缺少统一可追踪入口。

本变更目标：

- 在 `docs/changes/` 下新增 `docs/` 分类，用于承载“新增/调整/迁移/规范更新”等文档变更记录。
- 固化 `plan/progress` 规则：对多 PR / 多阶段推进事项，使用 `*-plan.md` + `*-progress.md` 配套跟踪。

## 变更清单

- 新增规范：`docs/standards/changes-standards.md`
- 更新规范：`docs/standards/documentation-standards.md`（补充 `changes/docs` 与 `*-progress` 模板入口）
- 更新索引：`docs/standards/README.md`
- 更新目录入口：`docs/changes/README.md`
- 新增目录：`docs/changes/docs/README.md`
- 同步目录 README：将 `docs/changes/*/README.md` 状态调整为 `Active` 并补充对 `plan/progress` 的引用

## 受影响入口

- `docs/changes/README.md`（子目录列表新增 `docs/`）
- `docs/standards/README.md`（新增变更文档规范入口）

## 验证方式

- 检查 `docs/changes/` 下存在 `docs/` 目录与 `README.md`。
- 检查 `docs/standards/README.md` 可定位到 `docs/standards/changes-standards.md`。
- 人工抽查 2 份既有文档，确认 `plan/progress` 写法与规范一致：
  - `docs/changes/refactor/001-backend-repository-serializer-boundary-progress.md`
  - `docs/changes/refactor/002-backend-write-operation-boundary-plan.md`

## 回滚策略

- 回滚本变更时，删除新增的 `docs/standards/changes-standards.md` 与 `docs/changes/docs/` 目录，并恢复 `docs/standards/documentation-standards.md` 与各 `docs/changes/*/README.md` 的引用与状态字段。

