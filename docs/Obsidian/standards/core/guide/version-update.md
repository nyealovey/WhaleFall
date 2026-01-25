---
title: 版本更新与版本漂移控制
aliases:
  - version-update-guide
tags:
  - standards
  - standards/general
status: active
enforcement: guide
created: 2025-11-27
updated: 2026-01-09
owner: WhaleFall Team
scope: 发布版本号(`MAJOR.MINOR.PATCH`)更新、版本展示与版本漂移治理
related:
  - "[[standards/core/guide/git-workflow]]"
  - "[[reference/development/version-update-checklist]]"
---

# 版本更新与版本漂移控制

## 目的

- 保证项目版本号在“运行时/构建配置/对外展示/部署资产”之间一致，避免版本漂移。
- 让版本更新变成可审查、可回滚、可快速验证的标准化动作。

## 适用范围

- 运行时版本：`app/settings.py` 的 `APP_VERSION`
- 构建/依赖：`pyproject.toml`、`uv.lock`
- 对外展示：模板页脚、Nginx 错误页、README 徽章、CHANGELOG
- 发布脚本与环境示例：`scripts/deploy/`、`env.example`

## 规则（MUST/SHOULD/MAY）

### 1) 版本号来源（单一真源）

- MUST：每次版本更新必须先修改 `app/settings.py` 中的 `APP_VERSION`，其作为运行时版本号来源。
- MUST：`pyproject.toml` 的 `[project].version` 与 `APP_VERSION` 保持一致。
- SHOULD：对外展示与脚本内出现的版本号字符串与 `APP_VERSION` 同步（见 2)）。

### 2) 必须更新的文件清单（最小集）

版本更新的执行清单(最小集)已拆分为 reference, 避免 standards 混入 runbook/checklist:

- [[reference/development/version-update-checklist|版本更新 checklist]]

### 3) 版本更新时的“最小扰动”原则

- SHOULD：避免为了版本号而修改与本次发布无关的大文档（例如架构白皮书/评审报告）。如确有内容更新，需要在 PR 描述中说明“为什么必须同步改动”。
- MUST：不得把第三方依赖版本号（例如 `flask==...`）误替换为项目版本号。

## 正反例

### 正例：只改最小集并补齐验证

- 版本号替换仅落在“必需文件清单”与本次功能相关文件中。
- PR 描述包含：
  - 版本号从 `x.y.z` → `x.y.(z+1)` 的说明
  - 自检命令与结果（如 `ruff check`、`make typecheck`、`pytest -m unit`）

### 反例：全仓无差别替换

- 直接 `rg` 全仓替换导致大量 `docs/reports/*`、历史方案文档发生纯字符串变更，增加审核噪音。

## 门禁/检查方式

- 版本一致性自检（建议）：
  - `rg -n "<旧版本号>"`：确认改动只落在“必需文件清单 + 功能相关文件”
  - `./scripts/setup/validate-env.sh`：确认示例环境变量完整性（按需）
- 代码质量自检（按实际改动取子集）：
  - `make format`
  - `ruff check <paths>`
  - `make typecheck`
  - `pytest -m unit`

## 页面回归检查(建议)

最小回归建议已拆分为 reference checklist, 见:

- [[reference/development/version-update-checklist|版本更新 checklist]]

## 变更历史

- 2025-12-25：按 `documentation-standards.md` 重写为“版本漂移控制标准”，移除过期脚本引用与历史案例段落，补齐门禁与回归检查。
- 2026-01-08: 迁移至 Obsidian vault, 将元信息改为 YAML frontmatter.
