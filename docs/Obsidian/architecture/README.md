---
title: 架构文档索引
aliases:
  - architecture
tags:
  - architecture
  - architecture/index
status: draft
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: docs/Obsidian/architecture 入口与索引
related:
  - "[[standards/doc/documentation-standards]]"
  - "[[standards/halfwidth-character-standards]]"
  - "[[architecture/adr/README|ADR]]"
---

# 架构文档

> [!info] Purpose
> 本目录承载 WhaleFall 的架构设计说明, 分层边界, 关键数据流, 以及 ADR (Architecture Decision Records).

## 索引

- [[architecture/developer-entrypoint|开发者入口(常见任务导航)]]
- [[architecture/project-structure|项目结构与代码落点]]
- [[architecture/identity-access|认证与权限(Identity & Access)]]
- [[architecture/spec|技术规格与架构说明]]
- [[architecture/architecture-review|架构评审入口]]
- [[architecture/adr/README|ADR 索引]]

> [!todo] Planned notes
> 本目录仍存在待补齐的架构笔记(部分内容在 changes/plans/canvas 中被引用). 如需要落地, 建议按 ADR/计划文档推进, 并在此索引补齐:
> - `developer-entrypoint`
> - `module-dependency-graph`
> - `flows/*`
> - `common-options`
> - `layer-first-api-restructure`
> - domain notes: `accounts-permissions-domain`, `instances-domain`, `credentials-connections-domain`, `capacity-partitions-domain`, `databases-ledger-domain`, `scheduler-domain`, `classification-domain`, `tags-domain`, `files-exports`, `dashboard-domain`
