---
title: Classification domain
aliases:
  - classification-domain
tags:
  - architecture
  - architecture/domain
  - domain/classification
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: accounts classifications(分类/规则/分配/DSL), 以及与 permission snapshot/facts 的依赖关系
related:
  - "[[architecture/flows/auto-classify]]"
  - "[[API/accounts-api-contract]]"
  - "[[reference/errors/message-code-catalog]]"
  - "[[canvas/account-classification/account-classification-domain-components.canvas]]"
  - "[[canvas/account-classification/account-classification-flow.canvas]]"
  - "[[canvas/account-classification/account-classification-sequence.canvas]]"
  - "[[canvas/account-classification/account-classification-state-machine.canvas]]"
  - "[[canvas/account-classification/account-classification-erd.canvas]]"
---

# Classification domain

## 边界与职责

- 管理 classification 的定义与颜色, 规则(rule_expression), 分配(assignments), 以及权限映射.
- auto-classify 依赖 permission snapshot(v4) 与 permission facts, 属于典型写操作(action endpoint).

## 关键约束

- rule_expression 必须是 DSL v4.
- auto-classify 是写操作, API 与 UI 都需要 CSRF.

## 代码落点(常用)

- API:
  - `app/api/v1/namespaces/accounts_classifications.py`
- Services:
  - `app/services/account_classification/**`

## 图(Canvas)

- Domain components: [[canvas/account-classification/account-classification-domain-components.canvas]]
- Flow: [[canvas/account-classification/account-classification-flow.canvas]]
- Sequence: [[canvas/account-classification/account-classification-sequence.canvas]]
- State machine: [[canvas/account-classification/account-classification-state-machine.canvas]]
- ERD: [[canvas/account-classification/account-classification-erd.canvas]]

## 相关流程

- [[architecture/flows/auto-classify]]
