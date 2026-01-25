---
title: Routes 路由层编写规范
aliases:
  - routes-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
enforcement: gate
created: 2026-01-09
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/routes/**` 下所有 Flask Blueprint 路由"
related:
  - "[[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/layer/services-layer-standards]]"
---

# Routes 路由层编写规范

> [!note] 说明
> Routes 层面向 Web 页面与 JSON 接口. 它负责 HTTP 请求处理与参数解析, 业务编排应下沉到 Service, 数据访问应下沉到 Repository.

## 目的

- 固化 "Routes 只做请求入口" 的职责边界, 防止业务逻辑与数据库访问漂移到路由函数.
- 统一错误兜底与日志上下文, 让失败口径稳定且可观测.
- 统一 JSON 响应封套, 减少页面脚本与后端之间的结构漂移.

## 适用范围

- `app/routes/**` 下所有通过 Flask `Blueprint` 注册的路由函数.
- 包含页面渲染路由与返回 JSON 的路由.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: Routes 只做请求接入, 参数解析/校验, 调用 `app.services.*`, 返回响应(模板或 JSON).
- MUST NOT: 在 Routes 内直接访问数据库, 包括 `Model.query`, `db.session`, 原生 SQL.
- MUST NOT: 在 Routes 内实现复杂业务逻辑(聚合, 批处理, 冲突判定, 权限规则等).
- SHOULD: 路由函数保持 "薄"(单函数 <= 30 行), 复杂逻辑下沉到 Service.

### 2) 统一兜底(safe_route_call)

- MUST: 所有路由函数通过 `safe_route_call(...)` 包裹实际执行逻辑.
- MUST: `safe_route_call` 入参至少包含 `module`, `action`, `public_error`.
- SHOULD: `context` 中放关键参数以便排障, 但必须遵循 [[standards/backend/sensitive-data-handling|敏感数据处理]] 约束.

### 3) JSON 响应格式

- MUST: 返回 JSON 的路由遵循 [[standards/backend/layer/api-layer-standards#响应封套(JSON Envelope)|响应封套(JSON Envelope)]].
- MUST: 成功响应使用 `jsonify_unified_success(...)`.
- MUST: 错误响应由统一错误处理器或 `safe_route_call` 输出, 禁止业务代码手写错误 JSON.
- MUST: 错误消息字段遵循 [[standards/backend/error-message-schema-unification|错误消息字段统一]].

### 4) 参数解析

- SHOULD: 对字符串 query 参数使用 `(request.args.get("k") or "").strip()` 规整输入.
- SHOULD: 当参数变多或复用时, 抽出 `_parse_*` 函数并用 `TypedDict` 描述结构(放在 `app/core/types/**`).
- MUST NOT: 在路由内做复杂的数据转换/清洗(应下沉到 Service 或 utils).

### 5) 依赖规则

允许依赖:

- MUST: `app.services.*`
- MAY: `app.utils.*`, `app.core.types.*`, `app.core.constants.*`, `app.core.exceptions`, `app.views.*`, `app.forms.*`

禁止依赖:

- MUST NOT: `app.models.*` 的查询接口(例如 `Model.query`)
- MUST NOT: `app.repositories.*` (应通过 Service)
- MUST NOT: `db.session`（提交点在 `safe_route_call`；事务语义由 Service 决策，详见 [[standards/backend/write-operation-boundary|写操作事务边界]]）

### 6) 装饰器顺序

- MUST: 装饰器顺序固定如下(从上到下):

```python
@blueprint.route("/path")  # 1) 路由
@login_required            # 2) 认证
@view_required             # 3) 权限
@require_csrf              # 4) CSRF(仅 POST/PUT/PATCH/DELETE)
def route_handler():
    ...
```

### 7) 蓝图与目录组织

- SHOULD: 以业务域拆分子目录与子蓝图(例如 `instances/`, `accounts/`, `capacity/`).
- SHOULD: 单个蓝图路由数超过 10 时拆分子蓝图, 避免巨型文件.

参考结构:

```text
app/routes/
├── __init__.py
├── main.py
├── auth.py
├── instances/
│   ├── __init__.py
│   ├── manage.py
│   ├── detail.py
│   └── batch.py
└── accounts/
    ├── __init__.py
    ├── ledgers.py
    └── statistics.py
```

蓝图命名建议:

| 蓝图名 | URL 前缀 | 示例 |
|---|---|---|
| `instances` | `/instances` | `/instances/`, `/instances/create` |
| `instances_detail` | `/instances` | `/instances/<id>` |
| `accounts_ledgers` | `/accounts` | `/accounts/ledgers` |
| `capacity_databases` | `/capacity` | `/capacity/databases` |

### 8) 代码规模限制

- SHOULD: 单文件 <= 200 行.
- SHOULD: 单路由函数 <= 30 行.
- SHOULD: 单蓝图路由数 <= 10 个.

## 正反例

### 正例: 页面路由(模板渲染)

- 判定点:
  - 路由函数保持薄, 参数读取/模板渲染在路由, 编排下沉到 Service.
  - 统一使用 `safe_route_call` 处理异常与可观测性字段.
- 长示例见: [[reference/examples/backend-layer-examples#页面路由(模板渲染)|Routes 页面路由示例(长示例)]]

### 正例: JSON 路由(统一封套)

- 判定点:
  - JSON 路由统一走 `jsonify_unified_success` 与标准错误字段.
  - 路由层不直接查库, 业务查询下沉到 Service/Repository.
- 长示例见: [[reference/examples/backend-layer-examples#JSON 路由(统一封套)|Routes JSON 路由示例(长示例)]]

### 反例: 路由内直接查库

```python
@instances_bp.route("/bad")
def bad():
    # 反例: Routes 不允许直接访问 Model.query 或 db.session
    items = Instance.query.all()
    return {"items": items}
```

## 门禁/检查方式

- 评审检查:
  - 是否所有路由都使用 `safe_route_call`?
  - 是否出现 `Model.query`/`db.session`/原生 SQL?
  - JSON 路由是否统一使用 `jsonify_unified_success` 且不手写错误 JSON?
- 自查命令(示例):

```bash
rg -n "Model\\.query|db\\.session" app/routes
rg -n "safe_route_call\\(" app/routes
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
- 2026-01-13: 将事务边界描述对齐为“提交点在 safe_route_call；事务语义由 Service 决策”.
