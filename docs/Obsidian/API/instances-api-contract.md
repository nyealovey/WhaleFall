---
title: Instances - API Contract
aliases:
  - instances-api-contract
tags:
  - api/contract
  - instances
  - connections
  - sync
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/instances.py
  - app/api/v1/namespaces/instances_accounts_sync.py
  - app/api/v1/namespaces/instances_connections.py
---

# Instances - API Contract

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/instances.py`（挂载：`/api/v1/instances`）
> - `app/api/v1/namespaces/instances_accounts_sync.py`（挂载同上，side-effect 注册）
> - `app/api/v1/namespaces/instances_connections.py`（挂载同上，side-effect 注册）
>

## Scope

- ✅ Instances：options / list / CRUD / exports / import template
- ✅ Instances Actions：sync-capacity / restore / batch-create / batch-delete
- ✅ Instances Statistics
- ✅ Instances Accounts Sync Actions：sync-accounts(all/single)
- ✅ Instances Connections：test / validate params / batch test / status

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Instances]]
- [[#Instances Actions]]
- [[#Instances Accounts Sync]]
- [[#Instances Connections]]

## 统一封套与分页

> [!info]
> JSON 封套口径见：[[standards/backend/api-response-envelope|API 响应封套]]。

### Pagination（page/limit）

- 列表分页统一使用 `page` + `limit`。
- `GET /api/v1/instances`：
  - `page`: 最小为 1；非法值回退默认值。
  - `limit`: 最小为 1、最大为 100；非法值回退默认值（默认 20）。

### 非 JSON 响应

> [!note]
> 以下接口成功时返回文件（非 JSON），失败时仍返回 JSON Envelope：
> - `GET /api/v1/instances/exports`（CSV）
> - `GET /api/v1/instances/imports/template`（CSV）
>

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限以代码侧 `api_permission_required(...)` 为准。
- 需要 CSRF 的接口：所有 `POST/PUT/PATCH/DELETE`（包含 action endpoints）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

| Method | Path                                                    | Purpose            | Service                                                     | Permission                                        | CSRF | Notes                                                                    |
| ------ | ------------------------------------------------------- | ------------------ | ----------------------------------------------------------- | ------------------------------------------------- | ---- | ------------------------------------------------------------------------ |
| GET    | `/api/v1/instances/options`                             | 获取实例选项             | `FilterOptionsService.get_common_instances_options`         | `view`                                            | -    | query：`db_type?`                                                         |
| GET    | `/api/v1/instances`                                     | 实例列表               | `InstanceListService.list_instances`                        | `view`                                            | -    | query：`search/db_type/status/tags/include_deleted/sort/order/page/limit` |
| POST   | `/api/v1/instances`                                     | 创建实例               | `InstanceWriteService.create`                               | `create`                                          | ✅    | JSON body：`name/db_type/host/port/...`                                   |
| GET    | `/api/v1/instances/exports`                             | 导出实例（CSV）          | `InstancesExportService.export_instances_csv`               | `view`                                            | -    | 成功返回 CSV（非 JSON）                                                         |
| GET    | `/api/v1/instances/imports/template`                    | 下载导入模板（CSV）        | `InstancesImportTemplateService.build_template_csv`         | `view`                                            | -    | 成功返回 CSV(非 JSON)                                                      |
| GET    | `/api/v1/instances/{instance_id}`                       | 实例详情               | `InstanceDetailReadService.get_active_instance`             | `view`                                            | -    | 仅返回 active instance（回收站实例会视为不存在）                                         |
| PUT    | `/api/v1/instances/{instance_id}`                       | 更新实例               | `InstanceWriteService.update`                               | `update`                                          | ✅    | JSON body 同创建                                                            |
| DELETE | `/api/v1/instances/{instance_id}`                       | 移入回收站（soft delete） | `InstanceWriteService.soft_delete`                          | `delete`                                          | ✅    | -                                                                        |
| POST   | `/api/v1/instances/{instance_id}/actions/restore`       | 恢复实例               | `InstanceWriteService.restore`                              | `update`                                          | ✅    | -                                                                        |
| POST   | `/api/v1/instances/{instance_id}/actions/sync-capacity` | 同步实例容量             | `InstanceCapacitySyncActionsService.sync_instance_capacity` | `update`                                          | ✅    | 可能返回 409：`DATABASE_CONNECTION_ERROR`/`SYNC_DATA_ERROR`                   |
| POST   | `/api/v1/instances/actions/batch-create`                | 批量创建实例（CSV 上传）     | `InstanceBatchCreationService.create_instances`             | `create`                                          | ✅    | `multipart/form-data`：`file`（.csv）                                       |
| POST   | `/api/v1/instances/actions/batch-delete`                | 批量删除实例             | `InstanceBatchDeletionService.delete_instances`             | `delete`                                          | ✅    | body：`instance_ids[]`；`deletion_mode?=soft/hard`                         |
| GET    | `/api/v1/instances/statistics`                          | 实例统计               | `InstanceStatisticsReadService.build_statistics`            | `view`                                            | -    | -                                                                        |
| POST   | `/api/v1/instances/actions/sync-accounts`               | 全量账户同步（后台任务）       | `AccountsSyncActionsService.trigger_background_full_sync`   | `update`                                          | ✅    | 成功返回 `data.session_id`                                                   |
| POST   | `/api/v1/instances/{instance_id}/actions/sync-accounts` | 单实例账户同步            | `AccountsSyncActionsService.sync_instance_accounts`         | `update`                                          | ✅    | 返回 `data.result`（包含 status/message/success）                              |
| POST   | `/api/v1/instances/actions/test-connection`             | 连接测试               | `ConnectionTestService.test_connection`                     | `view`                                            | ✅    | body：`instance_id?` 或 `db_type/host/port/credential_id`                  |
| POST   | `/api/v1/instances/actions/validate-connection-params`  | 校验连接参数（动作型校验）      | `_validate_connection_payload`                              | `view`                                            | ✅    | body：`db_type/port/credential_id?`                                       |
| POST   | `/api/v1/instances/actions/batch-test-connections`      | 批量连接测试             | `ConnectionTestService.test_connection`                     | `view`                                            | ✅    | body：`instance_ids[]`（最大 50）                                             |
| GET    | `/api/v1/instances/{instance_id}/connection-status`     | 获取连接状态             | `InstanceConnectionStatusService.get_status`                | `view`                                            | -    | -                                                                        |

## Instances

### `GET /api/v1/instances`

query（常用）：

- `search`: string（可选）
- `db_type`: string（可选）
- `status`: string（可选）
- `tags`: string[]（重复 key：`?tags=prod&tags=mysql`）
- `include_deleted`: `true/false`（可选；`true/1/on/yes` 视为 true）
- `sort`: string（默认 `id`）
- `order`: `asc/desc`（默认 `desc`）
- `page/limit`（`limit` 最大 100）

### `POST /api/v1/instances`

请求体（JSON）：

- `name: string`（必填）
- `db_type: string`（必填）
- `host: string`（必填）
- `port: int`（必填）
- `database_name: string`（可选）
- `credential_id: int`（可选）
- `description: string`（可选）
- `is_active: boolean`（可选）
- `tag_names: string[]`（可选）

## Instances Actions

### `POST /api/v1/instances/{instance_id}/actions/sync-capacity`

> [!note]
> action：会主动连接实例并采集容量数据；成功返回 `data.result`（包含 inventory、databases 等）。

### `POST /api/v1/instances/actions/batch-create`

- `Content-Type: multipart/form-data`
- form field：
  - `file`: `.csv`（必填）

### `POST /api/v1/instances/actions/batch-delete`

请求体（JSON）：

- `instance_ids: int[]`（必填）
- `deletion_mode: "soft"|"hard"`（可选，默认 `soft`）

## Instances Accounts Sync

### `POST /api/v1/instances/actions/sync-accounts`

> [!note]
> 触发后台任务：成功返回 `data.session_id`，用于在会话中心查看进度（见 `GET /api/v1/sync-sessions`）。

### `POST /api/v1/instances/{instance_id}/actions/sync-accounts`

- 成功：`data.result`（包含 `status/message/success` 以及同步结果字段）

## Instances Connections

### `POST /api/v1/instances/actions/test-connection`

请求体二选一：

- 测试既有实例：`{"instance_id": 1}`
- 测试新连接：`{"db_type":"mysql","host":"127.0.0.1","port":3306,"credential_id":1,"name":"temp_test"}`

### `POST /api/v1/instances/actions/batch-test-connections`

- `instance_ids` 最大 50；超过会直接 400。
