---
title: Partitions - API Contract
aliases:
  - partition-api-contract
tags:
  - api/contract
  - partitions
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/partition.py
---

# Partitions - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/partition.py`（挂载：`/api/v1/partitions`）
>

## Scope

- ✅ Partitions：info / status / list
- ✅ Partition Actions：create / cleanup
- ✅ Statistics：statistics / core-metrics

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]

## 统一封套与分页

> [!info]
> JSON 封套口径见: [[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)|API 响应封套]].

### Pagination（page/limit）

- `GET /api/v1/partitions` 使用 `page` + `limit`：
  - `page`: 最小为 1；非法值回退默认值。
  - `limit`: 最小为 1、最大为 200；非法值回退默认值（默认 20）。

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限粒度（`api_permission_required`）：
  - 读：`view`
  - 管理：`admin`
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含 action endpoints）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path                                           | Purpose | Service | Permission | CSRF | Notes                                                  |
| ------ | ---------------------------------------------- | ------- | ------- | ---------- | ---- | ------------------------------------------------------ |
| GET    | `/api/v1/partitions/info`                      | 分区信息快照  | `PartitionReadService.get_partition_info_snapshot` | `view`     | -    | -                                                      |
| GET    | `/api/v1/partitions/status`                    | 分区状态快照  | `PartitionReadService.get_partition_status_snapshot` | `view`     | -    | -                                                      |
| GET    | `/api/v1/partitions`                           | 分区列表    | `PartitionReadService.list_partitions` | `view`     | -    | query：`search/table_type/status/sort/order/page/limit` |
| POST   | `/api/v1/partitions`                           | 创建分区    | `PartitionManagementService.create_partition` | `admin`    | ✅    | body：`date(YYYY-MM-DD)`；仅允许当前或未来月份                     |
| POST   | `/api/v1/partitions/actions/cleanup`           | 清理旧分区   | `PartitionManagementService.cleanup_old_partitions` | `admin`    | ✅    | body：`retention_months?`（默认 12）                        |
| GET    | `/api/v1/partitions/statistics`                | 分区统计    | `PartitionStatisticsService.get_partition_statistics` | `view`     | -    | -                                                      |
| GET    | `/api/v1/partitions/core-metrics`              | 核心指标    | `PartitionReadService.build_core_metrics` | `view`     | -    | query：`period_type`（默认 daily）/`days`（默认 7）             |
