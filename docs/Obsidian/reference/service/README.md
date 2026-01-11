---
title: Service 服务层文档索引
aliases:
  - service-docs
  - reference-service
  - server-docs
  - reference-server
tags:
  - reference
  - reference/service
  - reference/index
  - service
status: active
created: 2026-01-09
updated: 2026-01-10
owner: WhaleFall Team
scope: app/services/** 的服务层实现解读文档索引
related:
  - "[[reference/README]]"
  - "[[architecture/flows/README]]"
  - "[[standards/doc/document-boundary-standards]]"
  - "[[standards/doc/service-layer-documentation-standards]]"
---

# Service 服务层文档索引

> [!note] 目标
> 本目录存放 `app/services/**` 的服务层实现解读文档(流程/失败语义/决策表/兼容兜底清单/图).

- 标准: [[standards/doc/service-layer-documentation-standards|服务层文档标准(Service Docs)]]
- 流程(SOP): [[architecture/flows/README]]
- 一次性产物: 计划/进度/复杂度报告位于 `docs/plans/**`, `docs/reports/**`(禁止从 vault 反向引用具体文件; 需长期保留的结论请沉淀到 `docs/Obsidian/**`)

> [!important] 去重原则
> Top 38 每个 `app/services/**` 文件只归属一个主文档(当前实现解读 SSOT). 其余位置仅做链接, 避免重复解释同一条链路.

## 常用入口(少量)

- [[reference/service/accounts-sync-overview|Accounts Sync 概览]]
- [[reference/service/aggregation-pipeline|Aggregation Pipeline]]
- [[reference/service/database-sync-overview|Database Sync 概览]]
- [[reference/service/instances-write-and-batch|Instances Write + Batch]]
- [[reference/service/sync-session-service|Sync Session Service]]

## 全量浏览(不维护手工清单)

```query
path:"reference/service"
```

> [!tip]
> 你也可以直接搜 `tag:#reference/service` 或 `path:"reference/service"`.
