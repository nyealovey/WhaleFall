# API v1 层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/api/v1/` 目录下所有 API 端点的编写规范

---

## 核心原则

**API = RESTful 端点 + 调用 Service + 统一响应格式**

```python
# ✅ API 职责
- 定义 RESTful 端点
- 参数校验（使用 Flask-RESTX）
- 调用 Service 处理业务
- 返回统一 JSON 响应
- 生成 OpenAPI 文档

# ❌ API 禁止
- 直接查询 Model（Model.query）
- 直接调用 Repository（应通过 Service）
- 包含复杂业务逻辑
```

---

## 目录结构

```
api/v1/
├── __init__.py               # 创建 Blueprint 和注册 Namespace
├── api.py                    # WhaleFallApi 基类
├── models/                   # 响应模型定义
│   ├── __init__.py
│   ├── common.py             # 通用模型（成功/错误封套）
│   └── fields/               # 字段定义
│       ├── instances.py
│       └── accounts.py
└── namespaces/               # API 端点
    ├── __init__.py
    ├── instances.py
    ├── accounts.py
    ├── credentials.py
    └── ...
```

---

## Namespace 编写模板

```python
"""实例 API."""

from flask_restx import Namespace, Resource, fields

from app.api.v1.models.common import make_success_envelope_model
from app.services.instances.instance_list_service import InstanceListService
from app.utils.route_safety import safe_route_call

ns = Namespace("instances", description="实例管理")

# 响应模型定义
InstanceModel = ns.model("Instance", {
    "id": fields.Integer(description="实例 ID"),
    "name": fields.String(description="实例名称"),
    "db_type": fields.String(description="数据库类型"),
})

InstanceListData = ns.model("InstanceListData", {
    "items": fields.List(fields.Nested(InstanceModel)),
    "total": fields.Integer(),
})

InstanceListResponse = make_success_envelope_model(
    ns, "InstanceListResponse", InstanceListData
)

# 服务实例
_list_service = InstanceListService()


@ns.route("/")
class InstancesResource(Resource):
    """实例列表资源."""

    @ns.doc("list_instances")
    @ns.marshal_with(InstanceListResponse)
    def get(self):
        """获取实例列表."""
        def _execute():
            result = _list_service.list_instances(filters)
            return {"success": True, "data": result}

        return safe_route_call(
            _execute,
            module="instances_api",
            action="list",
            public_error="获取实例列表失败",
        )
```

---

## 响应封套规范

### 成功响应

```python
from app.api.v1.models.common import make_success_envelope_model

# 定义数据模型
DataModel = ns.model("DataModel", {...})

# 生成封套模型
ResponseModel = make_success_envelope_model(ns, "ResponseModel", DataModel)

# 响应格式
{
    "success": true,
    "data": {...},
    "message": "操作成功"
}
```

### 错误响应

```python
{
    "success": false,
    "error": "validation_error",
    "message": "参数校验失败"
}
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| `app.services.*` | 业务服务 ✅ 推荐 |
| `app.utils.*` | 工具函数 |
| `app.types.*` | 类型定义 |
| `app.constants.*` | 常量 |

| 需要评估 | 说明 |
|---------|------|
| `app.repositories.*` | 简单只读查询可接受 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.models.*.query` | 禁止直接查询模型 |
| `db.session` | 禁止直接操作会话 |
| `app.routes.*` | 禁止依赖路由层 |

---

## 参数校验

### 使用 RequestParser

```python
from flask_restx import reqparse

parser = reqparse.RequestParser()
parser.add_argument("page", type=int, default=1, location="args")
parser.add_argument("limit", type=int, default=20, location="args")
parser.add_argument("search", type=str, location="args")


@ns.route("/")
class ListResource(Resource):
    @ns.expect(parser)
    def get(self):
        args = parser.parse_args()
        page = args["page"]
        ...
```

### 使用 Model（POST/PUT）

```python
create_model = ns.model("CreateInstance", {
    "name": fields.String(required=True),
    "db_type": fields.String(required=True),
    "host": fields.String(required=True),
    "port": fields.Integer(required=True),
})


@ns.route("/")
class CreateResource(Resource):
    @ns.expect(create_model)
    def post(self):
        data = ns.payload
        ...
```

---

## 命名规范

### 端点命名

| HTTP 方法 | 用途 | 端点示例 |
|-----------|------|----------|
| GET | 列表 | `/instances` |
| GET | 详情 | `/instances/<id>` |
| POST | 创建 | `/instances` |
| PUT | 全量更新 | `/instances/<id>` |
| PATCH | 部分更新 | `/instances/<id>` |
| DELETE | 删除 | `/instances/<id>` |

### Resource 类命名

```python
# 列表/创建
@ns.route("/")
class InstancesResource(Resource): ...

# 详情/更新/删除
@ns.route("/<int:instance_id>")
class InstanceResource(Resource): ...

# 嵌套资源
@ns.route("/<int:instance_id>/accounts")
class InstanceAccountsResource(Resource): ...
```

---

## 代码规模限制

| 指标 | 上限 | 超出处理 |
|------|------|----------|
| 单文件行数 | 500 行 | 拆分为多个文件 |
| 单 Resource 方法数 | 5 个 | 拆分为多个 Resource |
| 单方法行数 | 30 行 | 逻辑移到 Service |

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
