# API 命名与路径规范 (REST Resource Naming)

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2025-12-27
> 更新: 2025-12-27
> 范围: 后端 JSON API, 尤其是 /api/v1/**
> 关联:
> - docs/changes/refactor/004-flask-restx-openapi-migration-plan.md
> - docs/changes/refactor/004-flask-restx-openapi-migration-progress.md
> - https://apifox.com/apiskills/rest-resource-naming-guidelines/

## 1. 目的

- 统一 API 资源命名与路径结构, 让调用方在不看文档时也能推断语义.
- 降低迁移期新旧 API 并存的认知与切换成本.
- 为 OpenAPI 生成, 契约测试, 以及后续版本演进提供稳定约束.

## 2. 适用范围

- MUST: 本规范适用于所有 /api/v1/** JSON API.
- SHOULD: 新增 /api/v2/** 时沿用本规范, 仅在版本层面演进.
- MAY: 旧的 */api/* 路由在迁移期可保留历史路径, 但新入口必须提供 /api/v1/** 版本.

## 3. 规则

### 3.1 Base path 与版本

- MUST: 使用 /api/v1 作为统一前缀.
- MUST NOT: 在 /api/v1 路径中再次出现 /api 段 (例如 /api/v1/instances/api/instances).
- MUST: 不使用尾部 "/" (例如 /api/v1/credentials/, 禁止).
- MUST NOT: 路径中包含文件扩展名 (例如 .json, .xml).

### 3.2 资源命名 (路径段)

- MUST: 路径表示资源 (resource) 或资源集合 (collection), 使用名词, 不使用动词.
- MUST: 集合使用复数名词, 单个资源使用 {resource_id}.
- MUST: 路径段全小写.
- MUST: 多单词路径段使用 kebab-case (连字符), 例如 database-types.
- MUST NOT: 路径段使用 snake_case 或 camelCase.
- MUST: 路径参数名使用 snake_case, 并尽量带语义前缀, 例如 <int:credential_id>, <int:instance_id>.

### 3.3 HTTP method 语义

- SHOULD: CRUD 语义优先使用标准 method:
  - GET /resources
  - POST /resources
  - GET /resources/{id}
  - PUT /resources/{id}
  - DELETE /resources/{id}
- MUST NOT: 将 CRUD 动词写入 URI (例如 /create, /update, /delete, /list).

### 3.4 子资源与层级

- MUST: 仅在 "强从属关系" 时使用层级路径 (父资源 id 是子资源语义的一部分).
- SHOULD: 仅用于过滤或视图的维度, 优先使用 query 参数而不是新增层级.
- SHOULD: 层级深度保持克制, 通常不超过 2-3 层.

### 3.5 非 CRUD 动作 (actions)

当操作更像动作而非资源状态的 CRUD (例如 restore, sync, rotate-password):

- SHOULD: 使用 actions 约定:
  - POST /api/v1/<resources>/{id}/actions/<action-name>
  - POST /api/v1/<resources>/actions/<action-name> (批量或全局动作)
- MUST: <action-name> 使用 kebab-case, 使用动词短语, 语义清晰.
- MUST: 返回结构仍遵循统一 envelope (见 api-response-envelope.md).

迁移期兼容:

- MAY: 为兼容历史调用, 临时保留 POST /<resources>/{id}/delete 这类路径.
- MUST: 这类非标准路径必须:
  - 在 OpenAPI 中明确说明替代方案 (例如 DELETE /<resources>/{id} 或 actions 形式).
  - 在迁移进度文档中记录并给出下线计划.

### 3.6 选项类与字典类资源

- SHOULD: "options" 类资源使用名词子集合:
  - GET /api/v1/tags/options
  - GET /api/v1/tags/categories
- MUST NOT: 使用 list, get, fetch 等动词.

### 3.7 Query 参数命名 (canonical: snake_case)

- MUST: query 参数使用 snake_case.
- MUST: 分页参数统一为 page, limit.
- SHOULD: 排序参数统一为 sort, order (asc|desc).
- SHOULD: 搜索参数统一为 search.
- SHOULD: 多值参数使用重复 key, 例如 tags=prod&tags=core.
- MUST NOT: 在新 API v1 中引入 camelCase 参数作为 canonical (迁移期如需兼容, 仅作为 alias).

## 4. 正反例

### 4.1 Good

- GET /api/v1/credentials?page=1&limit=20&sort=created_at&order=desc
- POST /api/v1/credentials
- GET /api/v1/credentials/{credential_id}
- PUT /api/v1/credentials/{credential_id}
- DELETE /api/v1/credentials/{credential_id}
- GET /api/v1/tags/options
- POST /api/v1/instances/{instance_id}/actions/restore

### 4.2 Bad

- GET /api/v1/getCredentialsList
- POST /api/v1/credentials/create
- GET /api/v1/credential
- GET /api/v1/credentials/
- GET /api/v1/credentials?pageSize=20
- GET /api/v1/instances/api/instances

## 5. 门禁/检查方式

- MUST: 新增或修改 /api/v1 路由时:
  - 生成并校验 OpenAPI: uv run python scripts/dev/openapi/export_openapi.py --check
- SHOULD: 每个新增 endpoint 至少提供最小契约测试 (200 + 4xx): pytest -m unit
- SHOULD: PR review checklist:
  - path 段是否全小写, kebab-case, 无尾斜杠, 无扩展名
  - 是否使用复数集合名
  - 是否把 CRUD 动词写进 URI
  - query 参数是否 snake_case, 是否使用 page/limit/sort/order/search

## 6. 变更历史

| Date | Change | Author |
| --- | --- | --- |
| 2025-12-27 | Initial version for 004 RESTX/OpenAPI migration. | WhaleFall Team |
