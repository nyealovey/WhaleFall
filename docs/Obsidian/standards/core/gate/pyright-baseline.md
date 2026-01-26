---
title: Pyright 基线门禁（禁止新增 diagnostics）
aliases:
  - pyright-guard
tags:
  - standards
  - standards/core
status: active
enforcement: gate
created: 2026-01-25
updated: 2026-01-25
owner: WhaleFall Team
scope: "Python 类型检查增量治理：锁定现状 baseline，禁止新增 Pyright diagnostics（允许减少）"
related:
  - "[[standards/core/guide/coding]]"
  - "[[standards/core/guide/scripts]]"
---

# Pyright 基线门禁（禁止新增 diagnostics）

## 目的

- 在不一次性清理全仓历史问题的前提下，**阻止类型问题继续增长**。
- 让类型治理具备“可执行/可审查”的最小闭环：新增诊断必阻断；减少诊断可逐步落地。

## 适用范围

- 类型检查工具：Pyright（`pyrightconfig.json`）。
- 门禁脚本：`./scripts/ci/pyright-guard.sh`
- 基线文件：`scripts/ci/baselines/pyright.txt`

## 规则（MUST/SHOULD/MAY）

### 1) 禁止新增（MUST）

- MUST：任何 PR **不得新增** Pyright diagnostics。
- MAY：允许减少 diagnostics（修类型、补注解、收敛 Any 等）。

### 2) baseline 更新受控（MUST）

- MUST：仅在“确有必要”时更新 baseline，并在 PR 描述中写明：
  - 为何必须更新 baseline（新增诊断的来源/原因）
  - 是否有后续清理计划（何时减少回去）
- MUST：更新 baseline 必须通过脚本参数完成，禁止手工编辑基线文件：
  - `./scripts/ci/pyright-guard.sh --update-baseline`

### 3) 输出口径稳定（SHOULD）

- SHOULD：baseline 内容不包含行号/列号等易漂移字段，仅锁定相对路径 + 规则 + 归一化 message，降低无效 churn。

## 正反例

### 正例：减少 diagnostics

- 修复类型问题后直接提交；门禁脚本应通过（diagnostics 数减少或不变）。

### 反例：新增 diagnostics 但未更新 baseline

- 现象：`./scripts/ci/pyright-guard.sh` 阻断并打印新增命中。
- 修复方式：优先修类型；仅在确需引入且无法规避时，按“baseline 更新受控”流程更新。

## 门禁/检查方式

- 执行门禁：`./scripts/ci/pyright-guard.sh`
- 更新 baseline：`./scripts/ci/pyright-guard.sh --update-baseline`
- 报告（非门禁）：`./scripts/ci/pyright-report.sh`

## 变更历史

- 2026-01-25：补齐 Pyright baseline 门禁标准文档，形成“脚本 <-> 标准”闭环入口。

