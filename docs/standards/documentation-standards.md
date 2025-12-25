# WhaleFall 文档结构与编写规范

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：仓库 `docs/` 下所有文档（含后续新增）

## 1. 目标与原则

### 1.1 目标

- 让读者能在 30 秒内判断“该看哪类文档、入口在哪里”。
- 消除分类漂移（例如 `refactor` vs `refactoring`）、重复文档与断链。
- 形成可长期维护的“单一真源”（single source of truth）。

### 1.2 原则

- **按用途分层**：架构/参考/运维/规范/变更/报告分开。
- **单一真源**：同一主题只允许一个权威文档；历史版本进入归档。
- **新增文档英文命名**：文件名统一英文 `kebab-case.md`；正文默认中文。
- **链接可追溯**：仓库内链接必须使用相对路径，且在迁移时同步更新。

## 2. 文档目录结构（标准）

`docs/` 下目录按“用途”划分：

- `docs/README.md`：文档总入口（唯一入口）。
- `docs/getting-started/`：快速开始/本地开发/调试。
- `docs/architecture/`：架构设计（为什么/怎么设计）。
- `docs/reference/`：参考手册（是什么/参数/字段/契约）。
- `docs/operations/`：运维手册（Runbook，可执行步骤）。
- `docs/standards/`：规范标准（MUST/SHOULD/MAY）。
- `docs/changes/`：变更记录（与 PR/Issue 对齐）。
- `docs/reports/`：评审/审计/分析报告（阶段性产物）。
- `docs/prompts/`：Prompts 与协作模板（可复用）。
- `docs/_archive/`：归档区（只读）。

> 约束：禁止在 `docs/` 下新增与上述并列的“新一级目录”。如确需新增一级目录，必须先更新 `docs/README.md` 与本规范，并在评审中说明理由。

## 3. 命名规范（新增文档强制）

### 3.1 目录名

- MUST：全小写 `kebab-case`。
- MUST NOT：下划线、空格、中文目录名、大小写混用。

### 3.2 文件名

- MUST：全小写英文 `kebab-case.md`。
- MUST（`docs/changes/**`）：文件名必须带三位递增编号前缀，从 `001` 开始；每个子目录独立计数、各自从 `001` 重置；新文档按顺序取下一个编号。
  - 形式：`NNN-short-title.md`（`NNN` 为三位数字，包含前导零，例如 `001`）。
  - 如为多 PR 推进的计划文档，使用后缀区分：`NNN-short-title-plan.md` / `NNN-short-title-progress.md`。
  - 示例：`docs/changes/bugfix/001-instance-recycle-bin-restore.md`、`docs/changes/refactor/ui/002-filter-card-single-row.md`。
- SHOULD（`docs/reports/**`）：加日期前缀便于归档与检索，例如 `2025-12-25_security-audit-report.md`。
- ADR：沿用 `NNNN-short-title.md`（编号为四位数字）。

### 3.3 标题与路径

- MUST：标题表达清晰主题，避免“杂项/备忘录/临时”。
- MUST：仓库内链接使用相对路径（例如 `../reference/config/environment-variables.md`）。
- SHOULD：避免跨层级深链（例如从 `changes/` 直接链到 `reports/artifacts/`），优先链到对应目录的 `README.md`。

## 4. 文档元信息块（必填）

除目录索引类 README 外，新增文档 MUST 在标题下包含元信息块（纯文本即可）：

- 状态：`Draft | Active | Deprecated | Archived`
- 负责人：`@name` 或 `team`
- 创建：`YYYY-MM-DD`
- 更新：`YYYY-MM-DD`
- 范围：模块/目录/接口/人群
- 关联：Issue/PR/相关文档（相对路径）

示例：

```text
> 状态：Draft
> 负责人：@your-name
> 创建：2025-12-25
> 更新：2025-12-25
> 范围：accounts 同步链路
> 关联：PR #123；docs/reference/api/api-routes-documentation.md
```

## 5. 文档类型与最小结构（模板）

> 说明：`docs/changes/**` 的目录结构、`plan/progress` 配套规则与更详细模板，见 `docs/standards/changes-standards.md`。

### 5.1 `changes/feature`（新增功能）

必填章节：

- 背景与问题
- 目标 / 非目标
- 方案概述
- 变更清单（API/DB/配置/前端）
- 兼容性与迁移（含回滚）
- 验证与测试
- 影响面与监控
- 后续清理（删除开关/兼容分支/临时代码）

### 5.2 `changes/bugfix`（缺陷修复）

必填章节：

- 症状与影响
- 复现步骤
- 根因分析
- 修复方案
- 回归验证
- 风险与回滚
- 遗留问题

### 5.3 `changes/refactor`（重构）

必填章节：

- 动机与范围
- 不变约束（行为/契约/性能门槛）
- 分阶段计划（每阶段验收口径）
- 兼容/适配/回退策略（如存在）
- 验收指标
- 清理计划（删除旧实现/兼容逻辑）

### 5.4 `changes/docs`（新增/调整文档）

必填章节：

- 背景与目标
- 变更清单（新增/删除/移动/重命名的文档）
- 受影响入口（`docs/README.md`、目录 `README.md`、引用链接）
- 验证方式（断链检查/关键路径复核）
- 回滚策略（如何恢复）

### 5.5 `changes/*-progress`（进度文档）

适用：当一个变更拆分为多 PR/多阶段推进时，必须配套 `*-plan.md` 与 `*-progress.md`。

必填章节：

- 当前状态（摘要）
- Checklist（按 Phase 分组）
- 变更记录（按日期追加）

### 5.6 `operations/*`（运维 Runbook）

必填章节：

- 适用场景
- 前置条件
- 步骤（可复制执行）
- 验证
- 回滚
- 故障排查

### 5.7 `reference/*`（参考手册）

必填章节：

- 字段/参数表
- 默认值/约束
- 示例
- 版本/兼容性说明
- 常见错误

### 5.8 `standards/*`（规范标准）

必填章节：

- 目的
- 适用范围
- 规则（MUST/SHOULD/MAY）
- 正反例
- 门禁/检查方式
- 变更历史

### 5.9 `reports/*`（评审/审计报告）

必填章节：

- 摘要结论（先给结论）
- 范围与方法
- 发现清单（按 P0/P1/P2）
- 建议与后续行动
- 证据与数据来源（可链接到 `reports/artifacts/`）

## 6. 生命周期与归档规则

### 6.1 状态定义

- `Draft`：草案，未达成一致或尚未落地。
- `Active`：当前生效、团队遵循。
- `Deprecated`：仍可参考，但已有替代方案；必须指向替代文档。
- `Archived`：冻结只读；不再维护。

### 6.2 归档触发条件

- `changes/*`：对应 PR 已合并且“无需持续更新”时归档。
- `standards/*`：不轻易归档；如需替换版本，旧文档改为 `Deprecated` 并链接到新标准。
- `reports/*`：默认保留在 `reports/`；仅当过旧且仍需保留时迁入 `_archive/reports/`。

### 6.3 归档路径

- `_archive/changes/<category>/YYYY/` 下按日期归档。
- `_archive/reports/YYYY/` 下按日期归档。

> 约束：归档后必须在原目录 `README.md` 中保留“归档链接 + 替代/总结链接”，避免知识消失。

## 7. 维护流程（强约束）

- 新增/移动/重命名文档 MUST 同步更新：
  - `docs/README.md`
  - 对应目录 `README.md`
  - 仓库内引用该文档的链接（通过搜索确认）
- 出现重复文档时 MUST 做到：
  - 选定一份作为真源；其余要么删除，要么移入 `_archive/`（并在原处给出指向真源的链接）。
- 出现断链时 MUST 优先修复链接，而不是“再写一份新的”。

## 8. 质量门禁建议（可选）

如后续需要引入自动化门禁，建议的最小集合：

- 检测 `docs/` 内是否存在 `refactor/`、`refactoring/`、`bugifx/` 等不合规目录名。
- 检测仓库内 `docs/` 链接是否指向不存在文件（断链）。
- 检测新增文档文件名是否符合 `kebab-case.md`。
- 检测 `docs/changes/**` 下新增文档是否符合 `NNN-short-title.md`（三位编号前缀、每目录递增）。
