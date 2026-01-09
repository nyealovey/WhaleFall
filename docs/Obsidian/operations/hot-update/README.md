---
title: 热更新 Runbook 索引
aliases:
  - operations-hot-update
tags:
  - operations
  - operations/hot-update
  - operations/index
status: draft
created: 2025-12-25
updated: 2026-01-09
owner: WhaleFall Team
scope: 热更新与应急回滚 Runbook 入口与索引
related:
  - "[[operations/README|运维 Runbook]]"
  - "[[operations/deployment/deployment-guide|标准部署 Runbook]]"
---

# 热更新

> [!warning] 风险提示
> 热更新脚本会 `git reset --hard origin/main` 并覆盖运行中容器内 `/app/`.
> 使用前务必确认: 仓库工作区无未提交改动, 且你接受 "以远端 main 为准".

## 索引

- [[operations/hot-update/hot-update-guide|热更新 Runbook: 覆盖代码 + 迁移 + 重启]]
