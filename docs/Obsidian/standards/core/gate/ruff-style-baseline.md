---
title: Ruff(style) 基线门禁（禁止新增 violations）
aliases:
  - ruff-style-guard
tags:
  - standards
  - standards/core
status: active
enforcement: gate
created: 2026-01-25
updated: 2026-01-25
owner: WhaleFall Team
scope: "Python 风格增量治理：锁定现状 baseline，禁止新增 Ruff(style) violations（允许减少）"
related:
  - "[[standards/core/guide/coding]]"
  - "[[standards/core/guide/scripts]]"
---

# Ruff(style) 基线门禁（禁止新增 violations）

## 目的

- 把代码风格（docstring/import/pycodestyle/ruff 内建规则等）从“全仓一次性清理”改为**增量门禁**。
- 避免历史遗留问题阻塞开发，同时确保问题不会继续增长。

## 适用范围

- Ruff 规则集（style 模式）：`D,I,PLC,G`（以脚本实现为准）。
- 门禁脚本：`./scripts/ci/ruff-style-guard.sh`
- 基线文件：`scripts/ci/baselines/ruff_style.txt`

## 规则（MUST/SHOULD/MAY）

### 1) 禁止新增（MUST）

- MUST：任何 PR **不得新增** Ruff(style) violations。
- MAY：允许减少 violations（修复/重构/补 docstring 等）。

### 2) baseline 更新受控（MUST）

- MUST：仅在“确有必要”时更新 baseline，并在 PR 描述中写明原因与后续清理计划。
- MUST：更新 baseline 必须通过脚本参数完成，禁止手工编辑基线文件：
  - `./scripts/ci/ruff-style-guard.sh --update-baseline`

### 3) 输出口径稳定（SHOULD）

- SHOULD：baseline 内容不包含行号/列号等易漂移字段，仅锁定相对路径 + code + 归一化 message，降低无效 churn。

## 正反例

### 正例：减少 violations

- 修复 D/I/PLC/G 相关问题后提交；门禁脚本应通过（violations 数减少或不变）。

### 反例：新增 violations 但未更新 baseline

- 现象：`./scripts/ci/ruff-style-guard.sh` 阻断并打印新增命中。
- 修复方式：优先修复触发规则；仅在确需引入且不可避免时，按“baseline 更新受控”流程更新。

## 门禁/检查方式

- 执行门禁：`./scripts/ci/ruff-style-guard.sh`
- 更新 baseline：`./scripts/ci/ruff-style-guard.sh --update-baseline`
- 报告（非门禁）：`./scripts/ci/ruff-report.sh style`

## 变更历史

- 2026-01-25：补齐 Ruff(style) baseline 门禁标准文档，形成“脚本 <-> 标准”闭环入口。

