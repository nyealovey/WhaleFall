---
title: 运维 Runbook 索引
aliases:
  - operations
  - ops-runbook
tags:
  - operations
  - operations/index
status: draft
created: 2025-12-25
updated: 2026-01-09
owner: WhaleFall Team
scope: docs/Obsidian/operations 入口与索引
related:
  - "[[standards/doc/documentation-standards]]"
---

# 运维 Runbook

> [!info] Purpose
> 本目录沉淀可复制执行的运维 Runbook (部署, 热更新, 回滚, 排障).
> 编写规范见 [[standards/doc/documentation-standards]].

## 索引

- [[operations/deployment/README|部署]]
- [[operations/hot-update/README|热更新]]
- [[operations/observability-ops|可观测与排障(Observability Ops)]]
- [[operations/scheduler-jobstore-ops|Scheduler/jobstore 运维口径]]

## 约定

- 命令必须可复制执行, 不依赖口头约定.
- 每个 Runbook 必须包含: 适用场景, 前置条件, 步骤, 验证, 回滚, 故障排查.
- 高风险操作必须在正文显式标注风险与数据损失面.
