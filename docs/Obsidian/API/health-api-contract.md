---
title: Health - API Contract
aliases:
  - health-api-contract
tags:
  - api/contract
  - health
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/health.py
---

# Health - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/health.py`（挂载：`/api/v1/health`）
>

## Scope

- ✅ Public Health：ping / basic / health / detailed
- ✅ Authenticated Health：cache

## 快速导航

- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]

## 鉴权、权限、CSRF

- 多数健康检查接口为公共 GET（无需登录）。
- `GET /api/v1/health/cache` 需要登录（`api_login_required`）。
- 全部为 GET，无 CSRF 要求。

## Endpoints 总览

| Method | Path | Purpose | Service | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/health/ping` | ping | `health_checks_service.check_ping` | - | - | public |
| GET | `/api/v1/health/basic` | 基础健康状态 | `health_checks_service.get_basic_health` | - | - | public; `version` 当前为硬编码值 |
| GET | `/api/v1/health` | 健康检查（db + redis + uptime） | `check_database_health`<br>`check_cache_health`<br>`get_system_uptime` | - | - | public |
| GET | `/api/v1/health/cache` | 缓存健康检查 | `check_cache_health` | - | - | requires login |
| GET | `/api/v1/health/detailed` | 详细健康检查（components） | `check_database_health`<br>`check_cache_health`<br>`check_system_health` | - | - | public |
