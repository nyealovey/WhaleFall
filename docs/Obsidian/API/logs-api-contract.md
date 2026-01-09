---
title: Logs - API Contract
aliases:
  - logs-api-contract
tags:
  - api/contract
  - logs
  - admin
status: draft
created: 2026-01-08
updated: 2026-01-09
source_code:
  - app/api/v1/namespaces/logs.py
---

# Logs - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/logs.py`（挂载：`/api/v1/logs`）
>

## Scope

- ✅ Logs：list / statistics / modules / detail

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Logs List]]

## 统一封套与分页

> [!info]
> JSON 封套口径见：[[standards/backend/api-response-envelope|API 响应封套]]。

### Pagination（page/limit）

- `GET /api/v1/logs` 使用 `page` + `limit`：
  - `page`: 最小为 1；非法值回退默认值。
  - `limit`: 最小为 1、最大为 200；非法值回退默认值（默认 20）。

## 鉴权、权限、CSRF

- 所有接口需要登录。
- 本域为管理端接口：以 `admin` 权限为准（代码侧使用 `api_permission_required("admin")` / `api_admin_required`）。
- 均为 GET，无 CSRF 要求。

## Endpoints 总览

| Method | Path | Purpose | Service | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/logs` | 日志列表 | `HistoryLogsListService.list_logs` | `admin` | - | query：`level/module/search/start_time/end_time/hours/sort/order/page/limit` |
| GET | `/api/v1/logs/statistics` | 日志统计 | `HistoryLogsExtrasService.get_statistics` | `admin` | - | query：`hours`（默认 24；最大 2160） |
| GET | `/api/v1/logs/modules` | 模块列表 | `HistoryLogsExtrasService.list_modules` | `admin` | - | - |
| GET | `/api/v1/logs/{log_id}` | 日志详情 | `HistoryLogsExtrasService.get_log_detail` | `admin` | - | - |

## Logs List

### `GET /api/v1/logs`

query（常用）：

- `level`: string（可选；枚举见 `LogLevel`）
- `module`: string（可选）
- `search`: string（可选）
- `start_time/end_time`: ISO8601 datetime（可选）
- `hours`: int（可选；提供后用于限定时间范围；最大 2160）
- `sort`: string（默认 `timestamp`）
- `order`: `asc/desc`（默认 `desc`）
- `page/limit`
