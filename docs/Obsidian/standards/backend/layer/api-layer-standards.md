---
title: API 层编写规范
aliases:
  - api-layer-standards
  - api-v1-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-09
updated: 2026-01-13
owner: WhaleFall Team
scope: "`app/api/**` 下所有 REST API 端点、模型与注册入口"
related:
  - "[[standards/backend/layer/README|后端分层标准]]"
  - "[[standards/backend/layer/routes-layer-standards]]"
  - "[[standards/backend/request-payload-and-schema-validation]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/layer/services-layer-standards]]"
---

# API 层编写规范

> [!note] 说明
> API 层负责 HTTP 协议入口与 OpenAPI 文档生成, 业务编排应下沉到 Service, 数据访问应下沉到 Repository.

## 目的

- 明确 API 层职责边界, 避免端点中混入业务逻辑或数据库访问.
- 统一参数解析/校验, OpenAPI 文档, 响应封套, 错误兜底, 降低口径漂移.
- 保持端点代码可读可测, 让复杂逻辑集中在 `app/services/**`.

## 适用范围

- `app/api/__init__.py`: API blueprint 注册入口(例如 v1 blueprint).
- `app/api/v1/namespaces/**`: Flask-RESTX `Namespace` 与 `Resource`.
- `app/api/v1/models/**`: RESTX `Model`/`fields` 定义(用于 marshal 与 OpenAPI).
- `app/api/v1/__init__.py`, `app/api/v1/api.py` 等基础设施代码.

## 规则(MUST/SHOULD/MAY)

### 1) 职责边界

- MUST: API 层只做端点定义, 参数解析/校验, 调用 `app.services.*`, 返回统一封套响应.
- MUST NOT: 在 API 层实现复杂业务逻辑(聚合, 批处理, 冲突判定, 权限规则等).
- MUST NOT: 在 API 层直接访问数据库, 包括但不限于 `Model.query`, `db.session`, 原生 SQL.
- SHOULD: 端点方法保持 "薄"(单方法 <= 30 行), 复杂步骤拆到 Service.

### 2) 参数解析与校验

- MUST: Query 参数使用 `reqparse.RequestParser` 并配合 `@ns.expect(parser)`.
- MUST: JSON body 使用 `ns.model(...)` 并配合 `@ns.expect(model)` 生成稳定 OpenAPI schema.
- SHOULD: 业务级校验与数据规范化在 Service 内完成, 参考 [[standards/backend/request-payload-and-schema-validation]].
- MUST NOT: 把 RESTX 的 `ns.model` 当作唯一校验来源(它更偏文档与序列化).

### 3) 响应封套与错误口径

- MUST: 对外 JSON 响应使用统一封套, 字段与示例见下文 [[#响应封套(JSON Envelope)]].
- MUST: 错误消息字段遵循 [[standards/backend/error-message-schema-unification|错误消息字段统一]].
- MUST: API v1 success 响应使用 `BaseResource.success(...)`(底层 `unified_success_response(...)`).
- MUST: Routes(JSON) success 响应使用 `jsonify_unified_success(...)`.
- MUST: 错误响应由统一错误处理器输出(例如 RestX `Api.handle_error`, 或 `BaseResource.error_message(...)`), 业务代码禁止手写错误 JSON.
- SHOULD: OpenAPI 文档中通过 `make_success_envelope_model(...)`/`get_error_envelope_model(...)` 声明封套模型.

#### 响应封套(JSON Envelope)

> [!summary] TL;DR
> - 成功: `success=true`, `error=false`, 包含 `message`, `timestamp`, 可选 `data`, 可选 `meta`.
> - 失败: `success=false`, `error=true`, 包含 `error_id`, `message_code`, `message`, `timestamp`, `recoverable`, `suggestions`, `context`.

##### 目的

- 统一 API 成功/失败的顶层结构, 避免页面与脚本各自拼装响应导致口径漂移.
- 让前端用稳定方式读取 `response.success/response.message/response.data`, 并把错误信息结构化沉淀到日志中心.

##### 适用范围

- Routes 层返回 JSON 的接口(含列表/详情/批量操作).
- API(`app/api/**`) 的所有 REST API 端点.
- 任务或脚本需要返回 "可被 UI/调用方直接消费" 的 JSON 载荷时.

##### 规则(MUST/SHOULD/MAY)

###### 1) 统一封套(强约束)

- MUST: 成功响应使用 `app/utils/response_utils.py` 的 `unified_success_response(...)` / `jsonify_unified_success(...)`.
  - API v1 推荐使用 `BaseResource.success(...)` 统一生成封套.
  - Routes(JSON) 推荐使用 `jsonify_unified_success(...)` 返回 Flask Response.
- MUST: 错误响应由统一错误处理器统一生成(例如 `unified_error_response(...)`), 业务代码禁止手写错误 JSON.
- MUST NOT: 在业务逻辑内随意拼 `{success: true/false, ...}` 或改写错误字段结构.

###### 2) 成功响应字段(固定口径)

- MUST: `success: true`
- MUST: `error: false`
- MUST: `message: string`(可展示的成功摘要)
- MUST: `timestamp: string`(ISO8601)
- MAY: `data: object | list | string | number | boolean | null`
- MAY: `meta: object`

###### 3) 失败响应字段(固定口径)

> [!note]
> 失败响应由 `enhanced_error_handler` 输出, 并通过 `unified_error_response(...)` 映射为封套.

- MUST: `success: false`
- MUST: `error: true`
- MUST: `error_id: string`
- MUST: `category: string`
- MUST: `severity: string`
- MUST: `message_code: string`
- MUST: `message: string`(可展示的失败摘要)
- MUST: `timestamp: string`(ISO8601)
- MUST: `recoverable: boolean`
- MUST: `suggestions: list`
- MUST: `context: object`
- MAY: `extra: object`(仅允许放非敏感的诊断字段)

###### 4) `data` 的结构约束(面向列表页)

- MUST: 列表接口把 `items/total` 放在 `data` 内(推荐: `data.items` 为数组, `data.total` 为整数).
- MAY: 列表接口可在 `data` 内追加 `stats/filters/page/limit` 等字段, 但不得污染顶层封套字段.

###### 5) 错误消息与兼容约束

- MUST: 错误消息口径遵循 [[standards/backend/error-message-schema-unification|错误消息字段统一]], 禁止在任何层新增 `error/message` 互兜底链.
- SHOULD: 当返回结构发生演进时, 优先通过新增字段向前兼容, 避免重命名/挪字段导致调用方写兼容分支.

##### 正反例

成功响应示例:

```json
{
  "success": true,
  "error": false,
  "message": "任务列表获取成功",
  "timestamp": "2025-12-25T09:00:00+08:00",
  "data": {
    "items": [],
    "total": 0
  }
}
```

失败响应示例:

```json
{
  "success": false,
  "error": true,
  "error_id": "a1b2c3d4",
  "category": "system",
  "severity": "medium",
  "message_code": "INVALID_REQUEST",
  "message": "请求参数无效",
  "timestamp": "2025-12-25T09:00:00+08:00",
  "recoverable": true,
  "suggestions": ["请检查输入参数", "必要时联系管理员"],
  "context": {}
}
```

反例: 手写错误封套:

```python
return jsonify({"success": False, "msg": "failed"}), 400
```

### 4) 统一兜底(safe_route_call)

- MUST: 所有 `Resource` 方法通过 `safe_route_call(...)` 包裹实际执行函数.
- MUST: `safe_route_call` 入参至少包含 `module`, `action`, `public_error`.
- SHOULD: 在 `context` 中带上关键参数, 但必须遵循 [[standards/backend/sensitive-data-handling|敏感数据处理]] 约束.
- MUST NOT: 在端点内 `try/except Exception` 后吞异常继续返回成功.

### 5) 依赖规则

允许依赖:

- MUST: `app.services.*`
- MAY: `app.core.types.*`, `app.core.constants.*`, `app.core.exceptions`, `app.utils.*`

禁止依赖:

- MUST NOT: `app.repositories.*` (应通过 Service, 即使只读也不例外)
- MUST NOT: `app.models.*` 的查询接口(例如 `Model.query`)
- MUST NOT: `app` 的数据库会话(例如 `db.session`)
- MUST NOT: `app.routes.*` (避免与页面路由层交叉依赖)

### 6) 目录结构(推荐)

```text
app/api/
├── __init__.py
└── v1/
    ├── __init__.py
    ├── api.py
    ├── models/
    │   ├── __init__.py
    │   └── envelope.py
    ├── namespaces/
        ├── __init__.py
        ├── instances.py
        ├── accounts.py
        └── ...
    ├── resources/
    │   ├── __init__.py
    │   ├── base.py
    │   └── decorators.py
    └── restx_models/
        ├── __init__.py
        ├── instances.py
        └── ...
```

### 7) 命名规范

- MUST: 端点路径与资源命名遵循下文 [[#API 命名与路径规范(REST Resource Naming)]].
- SHOULD: `Resource` 类名与资源语义一致, 同一文件按 "list/create" 与 "detail/update/delete" 分组.

端点示例:

| HTTP 方法 | 用途 | 端点示例 |
|---|---|---|
| GET | 列表 | `/instances` |
| GET | 详情 | `/instances/<id>` |
| POST | 创建 | `/instances` |
| PUT | 全量更新 | `/instances/<id>` |
| PATCH | 部分更新 | `/instances/<id>` |
| DELETE | 删除 | `/instances/<id>` |

#### API 命名与路径规范(REST Resource Naming)

##### 目的

- 统一 API 资源命名与路径结构, 让调用方在不看文档时也能推断语义.
- 降低迁移期新旧 API 并存的认知与切换成本.
- 为 OpenAPI 生成, 契约测试, 以及后续版本演进提供稳定约束.

##### 适用范围

- MUST: 本规范适用于所有 `/api/v1/**` JSON API.
- SHOULD: 新增 `/api/v2/**` 时沿用本规范, 仅在版本层面演进.
- MAY: 旧的 `*/api/*` 路由在迁移期可保留历史路径, 但新入口必须提供 `/api/v1/**` 版本.

##### 规则

###### 1) Base path 与版本

- MUST: 使用 `/api/v1` 作为统一前缀.
- MUST NOT: 在 `/api/v1` 路径中再次出现 `/api` 段(例如 `/api/v1/instances/api/instances`).
- MUST: 不使用尾部 `/`(例如 `/api/v1/credentials/`, 禁止).
- MUST NOT: 路径中包含文件扩展名(例如 `.json`, `.xml`).

###### 2) 资源命名(路径段)

- MUST: 路径表示资源(resource)或资源集合(collection), 使用名词, 不使用动词.
- MUST: 集合使用复数名词, 单个资源使用 `{resource_id}`.
- MUST: 路径段全小写.
- MUST: 多单词路径段使用 kebab-case(连字符), 例如 `database-types`.
- MUST NOT: 路径段使用 snake_case 或 camelCase.
- MUST: 路径参数名使用 snake_case, 并尽量带语义前缀, 例如 `<int:credential_id>`, `<int:instance_id>`.

###### 3) HTTP method 语义

- SHOULD: CRUD 语义优先使用标准 method:
  - GET `/resources`
  - POST `/resources`
  - GET `/resources/{id}`
  - PUT `/resources/{id}`
  - DELETE `/resources/{id}`
- MUST NOT: 将 CRUD 动词写入 URI(例如 `/create`, `/update`, `/delete`, `/list`).

###### 4) 子资源与层级

- MUST: 仅在 "强从属关系" 时使用层级路径(父资源 id 是子资源语义的一部分).
- SHOULD: 仅用于过滤或视图的维度, 优先使用 query 参数而不是新增层级.
- SHOULD: 层级深度保持克制, 通常不超过 2-3 层.

###### 5) 非 CRUD 动作(actions)

当操作更像动作而非资源状态的 CRUD(例如 restore, sync, rotate-password):

- SHOULD: 使用 actions 约定:
  - POST `/api/v1/<resources>/{id}/actions/<action-name>`
  - POST `/api/v1/<resources>/actions/<action-name>`(批量或全局动作)
- MUST: `<action-name>` 使用 kebab-case, 使用动词短语, 语义清晰.
- MUST: 返回结构仍遵循统一 envelope, 见 [[#响应封套(JSON Envelope)]].

迁移期兼容:

- MAY: 为兼容历史调用, 临时保留 `POST /<resources>/{id}/delete` 这类路径.
- MUST: 这类非标准路径必须:
  - 在 OpenAPI 中明确说明替代方案(例如 `DELETE /<resources>/{id}` 或 actions 形式).
  - 在迁移进度文档中记录并给出下线计划.

###### 6) 选项类与字典类资源

- SHOULD: "options" 类资源使用名词子集合:
  - GET `/api/v1/tags/options`
  - GET `/api/v1/tags/categories`
- MUST NOT: 使用 list, get, fetch 等动词.

###### 7) Query 参数命名(canonical: snake_case)

- MUST: query 参数使用 snake_case.
- MUST: 分页参数统一为 `page`, `limit`.
- SHOULD: 排序参数统一为 `sort`, `order`(`asc`/`desc`).
- SHOULD: 搜索参数统一为 `search`.
- SHOULD: 多值参数使用重复 key, 例如 `tags=prod&tags=core`.
- MUST NOT: 在新 API v1 中引入 camelCase 参数作为 canonical(迁移期如需兼容, 仅作为 alias).

##### 正反例

Good:

- GET `/api/v1/credentials?page=1&limit=20&sort=created_at&order=desc`
- POST `/api/v1/credentials`
- GET `/api/v1/credentials/{credential_id}`
- PUT `/api/v1/credentials/{credential_id}`
- DELETE `/api/v1/credentials/{credential_id}`
- GET `/api/v1/tags/options`
- POST `/api/v1/instances/{instance_id}/actions/restore`

Bad:

- GET `/api/v1/getCredentialsList`
- POST `/api/v1/credentials/create`
- GET `/api/v1/credential`
- GET `/api/v1/credentials/`
- GET `/api/v1/credentials?pageSize=20`
- GET `/api/v1/instances/api/instances`

##### 门禁/检查方式

- MUST: 新增或修改 `/api/v1` 路由时:
  - 生成并校验 OpenAPI: `uv run python scripts/dev/openapi/export_openapi.py --check`
- SHOULD: 每个新增 endpoint 至少提供最小契约测试(200 + 4xx): `uv run pytest -m unit`
- SHOULD: PR review checklist:
  - path 段是否全小写, kebab-case, 无尾斜杠, 无扩展名
  - 是否使用复数集合名
  - 是否把 CRUD 动词写进 URI
  - query 参数是否 snake_case, 是否使用 `page`/`limit`/`sort`/`order`/`search`

### 8) 代码规模限制

- SHOULD: 单文件 <= 500 行, 超出则拆分为多个 `Namespace` 文件或提取 `models/fields`.
- SHOULD: 单个 `Resource` 类的方法数 <= 5.

## 正反例

### 正例: Namespace 模板

- 判定点:
  - `Namespace` 只承载路由注册, parser 定义, response model(envelope)定义.
  - `Resource` 方法保持薄, 业务编排下沉到 `app.services.*`.
  - 所有执行通过 `safe_call`/`safe_route_call` 统一兜底, 并传入最小 `context` 便于排障.
- 长示例见: [[reference/examples/backend-layer-examples#Namespace 模板|API Layer Namespace 模板(长示例)]]

### 反例: 端点内直接查库

```python
@ns.route("/bad")
class BadResource(Resource):
    def get(self):
        # 反例: API 层不允许直接使用 Model.query 或 db.session
        items = Instance.query.all()
        return {"success": True, "data": items}
```

## 门禁/检查方式

- 评审检查:
  - 是否所有 `Resource` 方法都通过 `safe_route_call` 统一兜底?
  - 是否出现 `Model.query`/`db.session`/原生 SQL?
  - 是否遵循统一封套与错误字段标准?
- 自查命令(示例):

```bash
rg -n "Model\\.query|db\\.session" app/api
rg -n "from app\\.services\\." app/api
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
