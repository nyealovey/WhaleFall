---
title: Accounts - API Contract (Ledgers & Classifications)
aliases:
  - accounts-api-contract
tags:
  - api/contract
  - accounts
  - ledgers
  - classifications
status: draft
created: 2026-01-08
updated: 2026-01-08
source_code:
  - app/api/v1/namespaces/accounts.py
  - app/api/v1/namespaces/accounts_classifications.py
---

# Accounts - API Contract (Ledgers & Classifications)

> [!note]
> 本文档以代码为准，对应：
> - `app/api/v1/namespaces/accounts.py`（挂载：`/api/v1/accounts`）
> - `app/api/v1/namespaces/accounts_classifications.py`（挂载：`/api/v1/accounts/classifications`）
>


## Scope

- ✅ Accounts：Ledgers / Statistics
- ✅ Accounts Classifications：colors / CRUD / rules / assignments / permissions / auto-classify

## 快速导航

- [[#统一封套与分页]]
- [[#鉴权、权限、CSRF]]
- [[#Endpoints 总览]]
- [[#Accounts（Ledgers & Statistics）]]
- [[#Accounts Classifications]]
- [[#关键约束与常见错误码]]

## 统一封套与分页

> [!info]
> JSON 封套口径见: [[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)|API 响应封套]].

### JSON Envelope（成功）

```json
{
  "success": true,
  "error": false,
  "message": "操作成功",
  "timestamp": "2026-01-08T00:00:00+08:00",
  "data": {}
}
```

### JSON Envelope（失败）

```json
{
  "success": false,
  "error": true,
  "error_id": "a1b2c3d4",
  "category": "system",
  "severity": "medium",
  "message_code": "INVALID_REQUEST",
  "message": "请求参数无效",
  "timestamp": "2026-01-08T00:00:00+08:00",
  "recoverable": true,
  "suggestions": ["请检查输入参数"],
  "context": {},
  "extra": {}
}
```

### Pagination（page/limit）

> [!warning]
> 代码侧分页参数统一使用 `page` + `limit`（不是 `page_size`）。

- `page`: 最小为 1；非法值回退默认值。
- `limit`: 最小为 1、最大为 200；非法值回退默认值（默认 20）。
- `GET /api/v1/accounts/ledgers` 的响应中会返回 `data.limit` 字段，其值即本次分页的 `limit`。

## 鉴权、权限、CSRF

- 所有接口默认需要登录（`api_login_required`）。
- 权限粒度（`api_permission_required`）：
  - 读：`view`
  - 创建：`create`
  - 更新：`update`
  - 删除：`delete`
- 需要 CSRF 的接口：所有 `POST/PUT/DELETE`（包含“动作型”校验接口）。
  - Header：`X-CSRFToken: <token>`
  - 禁止通过 JSON Body 传递 `csrf_token`

## Endpoints 总览

### Accounts（`/api/v1/accounts`）

| Method | Path | Purpose | Service | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/accounts/ledgers` | 账户台账列表 | `AccountsLedgerListService.list_accounts` | `view` | - | 支持筛选/排序；分页参数 `page/limit` |
| GET | `/api/v1/accounts/ledgers/exports` | 导出账户台账（CSV） | `AccountExportService.export_accounts_csv` | `view` | - | 成功返回 CSV（非 JSON）；失败仍为 JSON Envelope |
| GET | `/api/v1/accounts/ledgers/{account_id}/permissions` | 台账权限详情 | `AccountsLedgerPermissionsService.get_permissions` | `view` | - | 依赖权限快照 v4，否则 409 `SNAPSHOT_MISSING` |
| GET | `/api/v1/accounts/ledgers/{account_id}/change-history` | 台账变更历史 | `AccountsLedgerChangeHistoryService.get_change_history` | `view` | - | 读取 `account_change_log`（默认最多 50 条） |
| GET | `/api/v1/accounts/statistics` | 统计总览 | `AccountsStatisticsReadService.build_statistics` | `view` | - | 汇总 + `db_type_stats` + `classification_stats` |
| GET | `/api/v1/accounts/statistics/summary` | 统计汇总 | `AccountsStatisticsReadService.fetch_summary` | `view` | - | query：`instance_id` / `db_type`（可选） |
| GET | `/api/v1/accounts/statistics/db-types` | 按 db_type 统计 | `AccountsStatisticsReadService.fetch_db_type_stats` | `view` | - | 返回 `{db_type: {total/active/normal/locked/deleted}}` |
| GET | `/api/v1/accounts/statistics/classifications` | 按 classification 统计 | `AccountsStatisticsReadService.fetch_classification_stats` | `view` | - | 返回 `{classification_name: {account_count/color/display_name}}` |
| GET | `/api/v1/accounts/statistics/rules` | 规则命中统计 | `AccountClassificationsReadService.get_rule_stats` | `view` | - | query：`rule_ids=1,2,3`（可选） |

### Accounts Classifications（`/api/v1/accounts/classifications`）

| Method | Path | Purpose | Service | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/v1/accounts/classifications/colors` | 颜色选项 | `ThemeColors.COLOR_MAP` | `view` | - | 返回 `ThemeColors.COLOR_MAP` 与 choices |
| GET | `/api/v1/accounts/classifications` | 分类列表 | `AccountClassificationsReadService.list_classifications` | `view` | - | `data.classifications[]` |
| POST | `/api/v1/accounts/classifications` | 创建分类 | `AccountClassificationsWriteService.create_classification` | `create` | ✅ | body：`name/description/risk_level/color/icon_name/priority` |
| GET | `/api/v1/accounts/classifications/{classification_id}` | 分类详情 | `AccountClassificationsReadService.build_classification_detail` | `view` | - | `data.classification` |
| PUT | `/api/v1/accounts/classifications/{classification_id}` | 更新分类 | `AccountClassificationsWriteService.update_classification` | `update` | ✅ | 支持部分字段更新（未传字段保留原值） |
| DELETE | `/api/v1/accounts/classifications/{classification_id}` | 删除分类 | `AccountClassificationsWriteService.delete_classification` | `delete` | ✅ | 系统分类不可删；使用中返回 409 |
| GET | `/api/v1/accounts/classifications/rules` | 规则列表 | `AccountClassificationsReadService.list_rules` | `view` | - | 返回 `data.rules_by_db_type`（按 db_type 分组） |
| POST | `/api/v1/accounts/classifications/rules` | 创建规则 | `AccountClassificationsWriteService.create_rule` | `create` | ✅ | body：`rule_name/classification_id/db_type/operator/rule_expression/is_active` |
| GET | `/api/v1/accounts/classifications/rules/filter` | 筛选规则 | `AccountClassificationsReadService.filter_rules` | `view` | - | query：`classification_id` / `db_type` |
| POST | `/api/v1/accounts/classifications/rules/actions/validate-expression` | 校验规则表达式 | `AccountClassificationExpressionValidationService.parse_and_validate` | `view` | ✅ | 仅接受 DSL v4 表达式；支持传对象或 JSON 字符串 |
| GET | `/api/v1/accounts/classifications/rules/{rule_id}` | 规则详情 | `ClassificationRule.query.get_or_404`<br>`_serialize_rule` | `view` | - | `data.rule.rule_expression` 会解析为对象 |
| PUT | `/api/v1/accounts/classifications/rules/{rule_id}` | 更新规则 | `AccountClassificationsWriteService.update_rule` | `update` | ✅ | **需要完整字段**（同创建） |
| DELETE | `/api/v1/accounts/classifications/rules/{rule_id}` | 删除规则 | `AccountClassificationsWriteService.delete_rule` | `delete` | ✅ | - |
| GET | `/api/v1/accounts/classifications/assignments` | 分配列表 | `AccountClassificationsReadService.list_assignments` | `view` | - | `data.assignments[]` |
| DELETE | `/api/v1/accounts/classifications/assignments/{assignment_id}` | 移除分配 | `AccountClassificationsWriteService.deactivate_assignment` | `delete` | ✅ | 仅停用 `is_active` |
| GET | `/api/v1/accounts/classifications/permissions/{db_type}` | 权限选项 | `AccountClassificationsReadService.get_permissions` | `view` | - | 返回权限配置（Raw） |
| POST | `/api/v1/accounts/classifications/actions/auto-classify` | 自动分类 | `AutoClassifyService.auto_classify` | `update` | ✅ | body：`instance_id?` |

## Accounts（Ledgers & Statistics）

### `GET /api/v1/accounts/ledgers`

查询参数（均为可选）：

| Name              | Type     | Default    | Notes                                                         |
| ----------------- | -------- | ---------- | ------------------------------------------------------------- |
| `page`            | int      | 1          | 最小 1                                                          |
| `limit`           | int      | 20         | 最小 1，最大 200                                                   |
| `search`          | string   | `""`       | 模糊匹配：`username/instance_name/instance_host`                   |
| `instance_id`     | int      | -          | 按实例过滤                                                         |
| `db_type`         | string   | -          | `all`/空 => 不过滤（建议使用 `mysql/postgresql/oracle/sqlserver`）      |
| `include_deleted` | string   | -          | 仅当值为 `true` 时包含已删除账号                                          |
| `is_locked`       | string   | -          | `true/false`；其它值视为不过滤                                         |
| `is_superuser`    | string   | -          | `true/false`；其它值视为不过滤                                         |
| `tags`            | string[] | -          | 重复 key：`?tags=prod&tags=staging`                              |
| `classification`  | string   | -          | `all`/空 => 不过滤；建议传分类 ID（非数字会被忽略）                              |
| `sort`            | string   | `username` | 可选：`username/db_type/is_locked/is_superuser`；其它值回退 `username` |
| `order`           | string   | `asc`      | 仅当值为 `desc` 才会降序；其它值按升序                                       |
| `plugin`          | string   | `""`       | 当前未参与台账查询（保留字段）                                               |

成功响应：

- `data.items[]`：字段见 `ACCOUNT_LEDGER_ITEM_FIELDS`（`app/api/v1/restx_models/accounts.py`）
- `data.total/page/pages/limit`

### `GET /api/v1/accounts/ledgers/exports`

- 查询参数同 `GET /api/v1/accounts/ledgers`
- 成功：返回 `text/csv; charset=utf-8`，并包含 `Content-Disposition: attachment; filename=...`

### `GET /api/v1/accounts/ledgers/{account_id}/permissions`

- `account_id`：对应 `InstanceAccount.id`（即台账列表里的 `item.id`）
- 成功：`data.permissions.snapshot` 为权限快照（v4）

### `GET /api/v1/accounts/ledgers/{account_id}/change-history`

- 默认返回最近 50 条变更日志（按 `change_time desc`）
- `data.history[].change_time` 为格式化后的时间字符串；缺失时为 `"未知"`

### `GET /api/v1/accounts/statistics*`

- `GET /api/v1/accounts/statistics`：返回 `data.stats`（详见 `ACCOUNT_STATISTICS_FIELDS`）
- `GET /api/v1/accounts/statistics/summary`：query `instance_id?` / `db_type?`，返回汇总计数
- `GET /api/v1/accounts/statistics/db-types`：返回 `{db_type: {total/active/normal/locked/deleted}}`
- `GET /api/v1/accounts/statistics/classifications`：返回 `{classification_name: {account_count/color/display_name}}`
- `GET /api/v1/accounts/statistics/rules`：query `rule_ids=1,2,3`（可选；任一 token 非整数会直接报 400）；成功：`data.rule_stats[]: {rule_id, matched_accounts_count}`

## Accounts Classifications

### `GET /api/v1/accounts/classifications/colors`

- 成功：`data.colors` + `data.choices`

### `GET /api/v1/accounts/classifications`

- 成功：`data.classifications[]`（字段见 `ACCOUNT_CLASSIFICATION_LIST_ITEM_FIELDS`）

### `POST /api/v1/accounts/classifications`

请求体（JSON）：

- `name: string`（必填）
- `description: string`（可选）
- `risk_level: string`（可选，需为受支持的选项值）
- `color: string`（可选，颜色 key，需为 `ThemeColors` 支持值）
- `icon_name: string`（可选，需为受支持的选项值）
- `priority: int`（可选，范围 0-100）

成功响应：`data.classification`

### `PUT /api/v1/accounts/classifications/{classification_id}`

- 支持部分字段更新：未传字段会保留原值（但如传入非法值会校验失败）

### `DELETE /api/v1/accounts/classifications/{classification_id}`

> [!warning]
> 删除前会做阻断检查：
> - 系统分类（`is_system == true`）不能删除
> - 分类仍被规则/账户使用时，返回冲突错误

### `GET /api/v1/accounts/classifications/rules`

- 成功：`data.rules_by_db_type`（按 `db_type` 分组的规则列表）

### `POST /api/v1/accounts/classifications/rules`

请求体（JSON，创建/更新规则共用同一结构，缺字段会报错）：

- `rule_name: string`
- `classification_id: int`
- `db_type: string`（会做 normalize）
- `operator: string`（需为受支持的选项值）
- `rule_expression: object|string`（可选；字符串时会按 JSON 解析；最终必须是对象）
- `is_active: boolean`（可选，默认 true）

成功响应：`data.rule_id`

### `POST /api/v1/accounts/classifications/rules/actions/validate-expression`

请求体（JSON）：

- `rule_expression: object|string`（必填）

行为：

- 字符串会先尝试 JSON 解析
- 仅支持 DSL v4（否则返回 `DSL_V4_REQUIRED`）
- 通过时返回 `data.rule_expression`（解析后的对象）

### `GET/PUT/DELETE /api/v1/accounts/classifications/rules/{rule_id}`

- `GET`：返回 `data.rule`（`rule_expression` 会解析为对象）
- `PUT`：更新规则（需要完整字段，同创建）
- `DELETE`：删除规则

### `GET /api/v1/accounts/classifications/assignments`

- 成功：`data.assignments[]`

### `DELETE /api/v1/accounts/classifications/assignments/{assignment_id}`

- 仅停用分配（`is_active = false`），不做物理删除

### `GET /api/v1/accounts/classifications/permissions/{db_type}`

- 返回权限配置：`data.permissions`（Raw）

### `POST /api/v1/accounts/classifications/actions/auto-classify`

请求体（JSON，可选）：

- `instance_id`：为空表示全量

成功响应：`data.classified_accounts/total_classifications_added/failed_count/message`

> [!warning]
> 该接口失败时会抛出 `AutoClassifyError`（非 `AppError`），当前 HTTP 状态码默认会落到 500（尽管 OpenAPI 标注了 400）。

## 关键约束与常见错误码

- 401：未登录
- 403：
  - 权限不足（`PERMISSION_DENIED` 等）
  - CSRF 缺失/无效：`CSRF_MISSING` / `CSRF_INVALID`
- 409：
  - `SNAPSHOT_MISSING`：权限快照缺失或 `version != 4`
  - `CLASSIFICATION_IN_USE`：分类仍有关联规则/账户（`extra.rule_count/assignment_count`）
- 400（常见）：
  - `NAME_EXISTS`：分类名/规则名重复
  - `EXPRESSION_DUPLICATED`：规则表达式重复（同分类下）
  - `DSL_V4_REQUIRED` / `INVALID_DSL_EXPRESSION`：规则表达式校验失败
