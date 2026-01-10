---
title: Tags domain
aliases:
  - tags-domain
tags:
  - architecture
  - architecture/domain
  - domain/tags
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: Tag 模型, instance_tags 关联表, 以及批量操作的边界
related:
  - "[[API/tags-api-contract]]"
  - "[[architecture/flows/tags-bulk]]"
  - "[[canvas/tags/tags-bulk-flow.canvas]]"
---

# Tags domain

## 边界与职责

- 管理 Tag 元数据与分类(category), 以及 Instance <-> Tag 的关联关系.
- 批量操作属于典型写操作(action endpoints), 需要 CSRF.

## 关键表(SSOT 以 models 为准)

- `tags`
- `instance_tags`(join table)

## 代码落点(常用)

- API:
  - `app/api/v1/namespaces/tags.py`
- Services:
  - `app/services/tags/**`
- Models:
  - `app/models/tag.py`

## 图(Canvas)

- Bulk flow: [[canvas/tags/tags-bulk-flow.canvas]]

## 相关流程

- [[architecture/flows/tags-bulk]]
