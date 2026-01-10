---
title: Permission strings catalog
aliases:
  - permissions-catalog
  - permission-strings
tags:
  - reference
  - reference/security
  - permissions
status: active
created: 2026-01-10
updated: 2026-01-10
owner: WhaleFall Team
scope: API v1 contract 的 Permission 列, 以及当前代码中的权限字符串约定
related:
  - "[[API/api-v1-api-contract]]"
  - "[[standards/doc/api-contract-markdown-standards]]"
  - "[[architecture/identity-access]]"
  - "[[standards/backend/layer/api-layer-standards]]"
---

# Permission strings catalog

> [!info] Purpose
> 把 API contract 中的 `Permission` 列, 与代码侧实际使用的 permission strings 对齐, 让评审者与实现者用同一套词表沟通.

## 1. `Permission` 列与 login 的关系

- `Permission` 列仅表示"动作级权限"(permission check), 不等价于"是否需要登录"(authentication).
- 是否需要登录由代码侧 `api_login_required` 决定, contract 会在各 domain 的 "鉴权, 权限, CSRF" 章节描述默认口径.
- 因此你会看到:
  - `Permission: -`, 但仍需要登录(例如 `POST /api/v1/auth/logout`).
  - `Permission: -`, 且不需要登录(例如 `POST /api/v1/auth/login`).

## 2. Catalog(API v1)

> [!note] Source of truth
> - Permission check decorator: `app/api/v1/resources/decorators.py`
> - Permission evaluator(current stub): `app/utils/decorators.py` -> `has_permission(...)`
> - Contract SSOT: `docs/Obsidian/API/*-api-contract.md`

| Permission | Meaning | Typical endpoints | Enforced by | Notes |
| --- | --- | --- | --- | --- |
| `-` | 不做动作级权限校验 | auth, health-like, or "login only" endpoints | - | 仍可能需要 `api_login_required` |
| `view` | 读取资源, 列表/详情/统计 | `GET /api/v1/**` | `api_permission_required("view")` | 对齐 CRUD 中的 Read |
| `create` | 创建资源 | `POST /api/v1/**`(create) | `api_permission_required("create")` | 对齐 CRUD 中的 Create |
| `update` | 更新资源, 或触发带 side effect 的动作 | `PUT/POST /actions/*` | `api_permission_required("update")` | action endpoints 通常用 `update` |
| `delete` | 删除资源 | `DELETE /api/v1/**` | `api_permission_required("delete")` | 删除前可有业务阻断(409) |
| `admin` | 管理员级别操作(危险/运维/全局影响) | scheduler, logs, cache, partition, capacity aggregations | `api_permission_required("admin")` | 当前实现等价于 "role == admin" |

## 3. 其他 code-side permission strings(不进入 contract)

这些字符串当前主要用于日志字段或 Web 侧占位实现, 不应出现在 `docs/Obsidian/API/*-api-contract.md` 的 `Permission` 列中:

| Permission | Where | Purpose |
| --- | --- | --- |
| `login` | `api_login_required` 的 `extra.permission_type` | 仅用于标记本次失败是未登录导致 |
| `instance_management.instance_list.view` | `has_permission` 示例 mapping | 占位: 未来更细粒度 RBAC 的方向, 当前不是稳定契约 |

## 4. 变更历史

- 2026-01-10: 新增 permission strings catalog, 对齐 API contract 的 Permission 列.
