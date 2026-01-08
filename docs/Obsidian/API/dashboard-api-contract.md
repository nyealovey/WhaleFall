---
title: Dashboard - API Contract
aliases:
  - dashboard-api-contract
tags:
  - api/contract
  - dashboard
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/dashboard.py
---

# Dashboard - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/dashboard.py`（挂载：`/api/v1/dashboard`）
>

## Scope

- ✅ Overview / Charts / Activities / Status

## 快速导航

- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 全部为 GET，无 CSRF 要求。

## Endpoints 总览

| Method | Path | Purpose | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/dashboard/overview` | 系统概览 | - | - | - |
| GET | `/api/v1/dashboard/charts` | 图表数据 | - | - | query：`type`（默认 `all`） |
| GET | `/api/v1/dashboard/activities` | 活动列表 | - | - | 当前固定返回空数组 |
| GET | `/api/v1/dashboard/status` | 系统状态 | - | - | - |

