---
title: API v1 层编写规范
aliases:
  - api-layer-standards
  - api-v1-layer-standards
tags:
  - standards
  - standards/backend
  - standards/backend/layer
status: active
created: 2026-01-09
updated: 2026-01-09
owner: WhaleFall Team
scope: "`app/api/v1/**` 下所有 REST API 端点与模型"
related:
  - "[[standards/backend/api-response-envelope]]"
  - "[[standards/backend/api-naming-standards]]"
  - "[[standards/backend/request-payload-and-schema-validation]]"
  - "[[standards/backend/error-message-schema-unification]]"
  - "[[standards/backend/sensitive-data-handling]]"
  - "[[standards/backend/layer/services-layer-standards]]"
---

# API v1 层编写规范

> [!note] 说明
> API 层负责 HTTP 协议入口与 OpenAPI 文档生成, 业务编排应下沉到 Service, 数据访问应下沉到 Repository.

## 目的

- 明确 API 层职责边界, 避免端点中混入业务逻辑或数据库访问.
- 统一参数解析/校验, OpenAPI 文档, 响应封套, 错误兜底, 降低口径漂移.
- 保持端点代码可读可测, 让复杂逻辑集中在 `app/services/**`.

## 适用范围

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

- MUST: 成功/失败封套遵循 [[standards/backend/api-response-envelope|API 响应封套(JSON Envelope)]].
- MUST: 错误消息字段遵循 [[standards/backend/error-message-schema-unification|错误消息字段统一]].
- MUST: 成功响应使用封套模型(`make_success_envelope_model(...)`)并通过 `@ns.marshal_with(...)` 返回.
- MUST NOT: 手写错误 JSON, 或在端点内私自新增/重命名封套字段.

### 4) 统一兜底(safe_route_call)

- MUST: 所有 `Resource` 方法通过 `safe_route_call(...)` 包裹实际执行函数.
- MUST: `safe_route_call` 入参至少包含 `module`, `action`, `public_error`.
- SHOULD: 在 `context` 中带上关键参数, 但必须遵循 [[standards/backend/sensitive-data-handling|敏感数据处理]] 约束.
- MUST NOT: 在端点内 `try/except Exception` 后吞异常继续返回成功.

### 5) 依赖规则

允许依赖:

- MUST: `app.services.*`
- MAY: `app.types.*`, `app.constants.*`, `app.utils.*`

需要评估:

- MAY: `app.repositories.*` (仅限简单只读查询, 且必须在评审中说明为什么不下沉到 Service)

禁止依赖:

- MUST NOT: `app.models.*` 的查询接口(例如 `Model.query`)
- MUST NOT: `app` 的数据库会话(例如 `db.session`)
- MUST NOT: `app.routes.*` (避免与页面路由层交叉依赖)

### 6) 目录结构(推荐)

```text
app/api/v1/
├── __init__.py
├── api.py
├── models/
│   ├── __init__.py
│   ├── common.py
│   └── fields/
│       ├── instances.py
│       └── accounts.py
└── namespaces/
    ├── __init__.py
    ├── instances.py
    ├── accounts.py
    └── ...
```

### 7) 命名规范

- MUST: 端点路径与资源命名遵循 [[standards/backend/api-naming-standards|API 命名与路径规范]].
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

### 8) 代码规模限制

- SHOULD: 单文件 <= 500 行, 超出则拆分为多个 `Namespace` 文件或提取 `models/fields`.
- SHOULD: 单个 `Resource` 类的方法数 <= 5.

## 正反例

### 正例: Namespace 模板

```python
"""实例 API."""

from flask_restx import Namespace, Resource, fields, reqparse

from app.api.v1.models.common import make_success_envelope_model
from app.services.instances.instance_list_service import InstanceListService
from app.utils.route_safety import safe_route_call

ns = Namespace("instances", description="实例管理")

parser = reqparse.RequestParser()
parser.add_argument("page", type=int, default=1, location="args")
parser.add_argument("limit", type=int, default=20, location="args")
parser.add_argument("search", type=str, location="args")

InstanceModel = ns.model(
    "Instance",
    {
        "id": fields.Integer(description="实例 ID"),
        "name": fields.String(description="实例名称"),
        "db_type": fields.String(description="数据库类型"),
    },
)

InstanceListData = ns.model(
    "InstanceListData",
    {
        "items": fields.List(fields.Nested(InstanceModel)),
        "total": fields.Integer(),
    },
)

InstanceListResponse = make_success_envelope_model(
    ns,
    "InstanceListResponse",
    InstanceListData,
)

_list_service = InstanceListService()


@ns.route("/")
class InstancesResource(Resource):
    """实例列表资源."""

    @ns.doc("list_instances")
    @ns.expect(parser)
    @ns.marshal_with(InstanceListResponse)
    def get(self):
        """获取实例列表."""
        args = parser.parse_args()

        def _execute():
            result = _list_service.list_instances(args)
            return {"success": True, "data": result, "message": "实例列表获取成功"}

        return safe_route_call(
            _execute,
            module="instances_api",
            action="list",
            public_error="获取实例列表失败",
            context={"page": args.get("page"), "limit": args.get("limit")},
        )
```

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
rg -n "Model\\.query|db\\.session" app/api/v1
rg -n "from app\\.services\\." app/api/v1/namespaces
```

## 变更历史

- 2026-01-09: 迁移为 Obsidian note(YAML frontmatter + wikilinks), 并按 [[standards/doc/documentation-standards|文档结构与编写规范]] 补齐标准章节.
