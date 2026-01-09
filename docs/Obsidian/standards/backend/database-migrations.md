---
title: 数据库迁移(Alembic/Flask-Migrate)
aliases:
  - database-migrations
tags:
  - standards
  - standards/backend
status: active
created: 2025-12-25
updated: 2026-01-09
owner: WhaleFall Team
scope: "`migrations/**`, `sql/init/postgresql/init_postgresql.sql` 与生产库结构演进"
related:
  - docs/Obsidian/reference/database/schema-baseline.md
---

# 数据库迁移(Alembic/Flask-Migrate)

## 目的

- 让数据库结构变更可追溯、可回滚、可复现，避免“手工 DDL + 环境漂移”。
- 统一“空库初始化”“已有库升级”“基线对齐”的操作边界。

## 适用范围

- 所有需要改动表结构/索引/约束/触发器/分区的变更。
- 新环境建库、生产环境热更新、以及 schema 基线维护。

## 规则（MUST/SHOULD/MAY）

### 1) 迁移文件不可变

- MUST：已合并的迁移脚本不可再编辑（包括 revision id、upgrade/downgrade 逻辑）。
- MUST：任何结构变更必须通过新增迁移实现，而不是“修改历史迁移”。

### 2) 基线与初始化方式（必须遵守）

- MUST：仓库的 Alembic 基线 revision 为 `20251219161048`（见 `migrations/versions/20251219161048_baseline_production_schema.py`）。
- MUST：空库初始化二选一，禁止重复执行两条路径：
  - 方案 A：执行 `sql/init/postgresql/init_postgresql.sql`（及分区脚本）后，必须执行 `flask db stamp 20251219161048`
  - 方案 B：直接执行 `flask db upgrade`
- SHOULD：详细操作与校验参考 `docs/Obsidian/reference/database/schema-baseline.md`。

### 3) 迁移编写准则（面向生产）

- MUST：upgrade 必须幂等地覆盖预期差异，不得依赖“手工先执行某条 SQL”才能成功。
- SHOULD：对大表变更优先采用“分阶段、可回滚”的迁移策略（例如：先加 nullable 列 → 回填 → 再加 NOT NULL/约束）。
- SHOULD：迁移中避免长事务与锁表；必要时在 PR 描述中给出风险评估与执行窗口建议。

### 4) 迁移验证（提交前最低要求）

- MUST：在空库演练 `flask db upgrade` 或按初始化路径跑完并验证关键表/索引存在。
- SHOULD：执行一次 `alembic revision --autogenerate`（或等价检查）不应再生成“同一约束差异”，避免反复漂移。
- MAY：通过 `pg_dump --schema-only` 与初始化脚本做 diff，快速发现遗漏的约束/索引。

## 正反例

### 正例：新迁移修复差异

- 发现约束缺失 → 新增 revision 补齐约束 → 在空库与已有库升级路径都可成功执行。

### 反例：修改历史迁移

- 为了“让当前分支能跑”直接改 `baseline` 迁移脚本，导致已部署环境无法对齐版本链。

## 门禁/检查方式

- 迁移基线与初始化说明：`docs/Obsidian/reference/database/schema-baseline.md`
- 部署脚本内的防御逻辑（参考）：`scripts/deploy/deploy-prod-all.sh` / `scripts/deploy/update-prod-flask.sh`

## 变更历史

- 2025-12-25：新增标准文档，固化基线 revision、初始化二选一策略与最小验证要求。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
