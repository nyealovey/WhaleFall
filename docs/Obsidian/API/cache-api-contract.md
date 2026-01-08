---
title: Cache - API Contract
aliases:
  - cache-api-contract
tags:
  - api/contract
  - cache
  - admin
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/cache.py
---

# Cache - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/cache.py`（挂载：`/api/v1/cache`）
>

## Scope

- ✅ Cache Stats
- ✅ Cache Clear Actions（user/instance/all）
- ✅ Classification Cache（clear + stats）

## 快速导航

- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Clear Actions]]

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限以代码侧 `api_permission_required(...)` 为准（`admin/view/update`）。
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含 action endpoints）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path | Purpose | Service | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/cache/stats` | 缓存统计 | `cache_service.get_cache_stats` | - | - | 需要登录；缓存服务未初始化会返回 500 |
| POST | `/api/v1/cache/actions/clear-user` | 清除用户缓存 | `cache_service.invalidate_user_cache` | `admin` | ✅ | body：`instance_id/username`；可能返回 404/409 |
| POST | `/api/v1/cache/actions/clear-instance` | 清除实例缓存 | `cache_service.invalidate_instance_cache` | `admin` | ✅ | body：`instance_id`；可能返回 404/409 |
| POST | `/api/v1/cache/actions/clear-all` | 清除所有实例缓存 | `cache_service.invalidate_instance_cache` | `admin` | ✅ | 遍历活跃实例；返回 `data.cleared_count` |
| POST | `/api/v1/cache/actions/clear-classification` | 清除分类缓存 | `AccountClassificationService.invalidate_cache`<br>`AccountClassificationService.invalidate_db_type_cache` | `update` | ✅ | body：`db_type?`（mysql/postgresql/sqlserver/oracle）；为空则清全量分类缓存 |
| GET | `/api/v1/cache/classification/stats` | 分类缓存统计 | `cache_service.get_classification_rules_by_db_type_cache` | `view` | - | 返回 `cache_stats/db_type_stats/cache_enabled` |

## Clear Actions

### `POST /api/v1/cache/actions/clear-user`

请求体（JSON）：

- `instance_id: int`（必填）
- `username: string`（必填）

### `POST /api/v1/cache/actions/clear-classification`

请求体（JSON）：

- `db_type: string`（可选；仅支持 `mysql/postgresql/sqlserver/oracle`）
