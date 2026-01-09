# Routes 路由层编写规范

> **状态**: Active  
> **创建**: 2026-01-09  
> **负责人**: WhaleFall Team  
> **范围**: `app/routes/` 目录下所有路由的编写规范

---

## 核心原则

**Routes = 请求处理 + 参数解析 + 调用 Service + 返回响应**

```python
# ✅ Routes 职责
- 接收 HTTP 请求
- 解析和校验参数
- 调用 Service 处理业务
- 返回统一格式响应

# ❌ Routes 禁止
- 直接查询数据库（Model.query / db.session）
- 直接调用 Repository
- 包含业务逻辑
- 复杂数据处理
```

---

## 目录结构

```
routes/
├── __init__.py           # 蓝图注册
├── main.py               # 主页路由
├── auth.py               # 认证路由
├── dashboard.py          # 仪表板
├── credentials.py        # 凭据管理
├── users.py              # 用户管理
├── instances/            # 实例管理（目录）
│   ├── __init__.py
│   ├── manage.py         # 列表、创建、编辑
│   ├── detail.py         # 详情页
│   ├── statistics.py     # 统计
│   └── batch.py          # 批量操作
├── accounts/             # 账户管理
│   ├── __init__.py
│   ├── ledgers.py
│   ├── classifications.py
│   └── statistics.py
└── capacity/             # 容量统计
    ├── __init__.py
    ├── instances.py
    └── databases.py
```

---

## 路由编写模板

### 页面路由（渲染模板）

```python
"""实例管理路由."""

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.services.instances.instance_list_page_service import InstanceListPageService
from app.utils.decorators import view_required
from app.utils.route_safety import safe_route_call

instances_bp = Blueprint("instances", __name__)
_page_service = InstanceListPageService()


@instances_bp.route("/")
@login_required
@view_required
def index() -> str:
    """实例列表页面."""
    search = (request.args.get("search") or "").strip()
    db_type = (request.args.get("db_type") or "").strip()

    def _render() -> str:
        context = _page_service.build_context(
            search=search,
            db_type=db_type,
        )
        return render_template("instances/list.html", **context.__dict__)

    return safe_route_call(
        _render,
        module="instances",
        action="index",
        public_error="加载页面失败",
        context={"search": search, "db_type": db_type},
    )
```

---

## safe_route_call 使用规范

所有路由必须使用 `safe_route_call` 封装：

```python
from app.utils.route_safety import safe_route_call

@blueprint.route("/api/example")
def example_view() -> Response:
    def _execute() -> Response:
        # 实际逻辑
        return jsonify_unified_success(data=payload)

    return safe_route_call(
        _execute,
        module="example",          # 模块名
        action="example_view",     # 动作名
        public_error="操作失败",    # 用户可见错误消息
        context={"key": "value"},  # 日志上下文
        expected_exceptions=(ValidationError,),  # 预期的业务异常
    )
```

---

## 响应格式规范

### 成功响应

```python
from app.utils.response_utils import jsonify_unified_success

return jsonify_unified_success(
    data={"id": instance.id, "name": instance.name},
    message="创建成功",
)

# 输出
{
    "success": true,
    "data": {"id": 1, "name": "prod-mysql"},
    "message": "创建成功"
}
```

### 错误响应

```python
from app.utils.response_utils import jsonify_unified_error

return jsonify_unified_error(
    error="validation_error",
    message="参数校验失败",
)

# 输出
{
    "success": false,
    "error": "validation_error",
    "message": "参数校验失败"
}
```

---

## 参数解析规范

### 简单参数

```python
# 查询参数
search = (request.args.get("search") or "").strip()
page = request.args.get("page", type=int, default=1)
include_deleted = request.args.get("include_deleted", "").lower() == "true"

# 列表参数
tags = [t.strip() for t in request.args.getlist("tags") if t.strip()]
```

### 复杂参数（使用 TypedDict）

```python
from app.types.instances import InstanceListFilters

def _parse_filters() -> InstanceListFilters:
    return InstanceListFilters(
        page=request.args.get("page", type=int, default=1),
        limit=request.args.get("limit", type=int, default=20),
        search=(request.args.get("search") or "").strip(),
        db_type=(request.args.get("db_type") or "").strip(),
    )
```

---

## 依赖规则

| 允许依赖 | 说明 |
|---------|------|
| `app.services.*` | 业务服务 |
| `app.utils.*` | 工具函数 |
| `app.types.*` | 类型定义 |
| `app.constants.*` | 常量 |
| `app.views.*` | 视图类 |
| `app.forms.*` | 表单定义 |

| 禁止依赖 | 说明 |
|---------|------|
| `app.models.*` | 数据模型（禁止直接查询） |
| `app.repositories.*` | 仓储（应通过 Service） |
| `db.session` | 数据库会话 |

---

## 装饰器顺序

```python
@blueprint.route("/path")      # 1. 路由
@login_required                # 2. 认证
@view_required                 # 3. 权限
@require_csrf                  # 4. CSRF（POST 路由）
def route_handler():
    ...
```

---

## 蓝图命名规范

| 蓝图名 | URL 前缀 | 示例 |
|--------|----------|------|
| `instances` | `/instances` | `/instances/`, `/instances/create` |
| `instances_detail` | `/instances` | `/instances/<id>` |
| `accounts_ledgers` | `/accounts` | `/accounts/ledgers` |
| `capacity_databases` | `/capacity` | `/capacity/databases` |

---

## 代码规模限制

| 指标 | 上限 | 超出处理 |
|------|------|----------|
| 单文件行数 | 200 行 | 拆分为多个文件 |
| 单路由函数行数 | 30 行 | 逻辑移到 Service |
| 单蓝图路由数 | 10 个 | 拆分为子蓝图 |

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-01-09 | v1.0 | 初始版本 |
