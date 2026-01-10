---
title: 关键流程索引
aliases:
  - architecture-flows
  - flows
tags:
  - architecture
  - architecture/flows
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: 产品核心能力的关键流程 SOP 索引入口
related:
  - "[[architecture/spec]]"
  - "[[architecture/identity-access]]"
  - "[[operations/observability-ops]]"
  - "[[API/api-v1-api-contract]]"
  - "[[reference/server/README]]"
  - "[[canvas/README]]"
---

# 关键流程索引

> [!note] 说明
> - 本目录(`architecture/flows/*`)是关键流程 SOP 的 SSOT.
> - `[[architecture/spec]]` 是 as-built 概览与背景说明.
> - 可编辑图在 `[[canvas/README]]`, Mermaid 与 Canvas 需要互链.

## 登录

- SOP: [[architecture/flows/login]]
- 深读:
  - [[architecture/spec#5.1 Web 登录(页面)]]
  - [[architecture/spec#5.2 API 登录与调用(REST)]]

## 同步会话

- SOP: [[architecture/flows/sync-session]]
- 深读:
  - [[reference/server/sync-session-service]]

## 账户同步

- SOP: [[architecture/flows/accounts-sync]]
- 深读:
  - [[reference/server/accounts-sync-overview]]
  - [[reference/server/accounts-sync-adapters]]
  - [[reference/server/accounts-sync-permission-manager]]
  - [[reference/server/accounts-permissions-facts-builder]]

## 容量同步

- SOP: [[architecture/flows/capacity-sync]]
- 深读:
  - [[reference/server/database-sync-overview]]
  - [[reference/server/database-sync-adapters]]
  - [[reference/server/database-sync-table-sizes]]

## 聚合统计

- SOP: [[architecture/flows/aggregation-stats]]
- 深读:
  - [[reference/server/aggregation-pipeline]]
  - [[reference/server/capacity-current-aggregation-service]]

## 标签 bulk

- SOP: [[architecture/flows/tags-bulk]]
- 深读:
  - [[reference/server/tags-bulk-actions-service]]
  - [[reference/server/tags-write-service]]

## 自动分类

- SOP: [[architecture/flows/auto-classify]]
- 深读:
  - [[reference/server/account-classification-orchestrator]]
  - [[reference/server/account-classification-dsl-v4]]
  - [[reference/server/accounts-classifications-write-service]]
  - [[reference/server/accounts-permissions-facts-builder]]

## scheduler 与排障

- scheduler 运维口径: [[operations/scheduler-jobstore-ops]]
- 统一日志与排障: [[operations/observability-ops]]
