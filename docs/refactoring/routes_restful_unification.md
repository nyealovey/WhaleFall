# 路由与 RESTful 规范统一

目标
- 路由风格统一，避免动作动词与资源路径混搭造成混乱。
- 统一 `/api/*` 前缀与 Blueprint 注册一致性。

规范
- 资源路径：`/api/instances`, `/api/instances/<int:instance_id>`。
- 动作：尽量使用 HTTP 方法表达动作；必要时使用子路径：`/api/instances/<id>/test-connection`。
- 路由参数命名统一（见命名文档）。
- 所有 `/api/*` 路由统一走 `APIResponse` 与权限装饰器。

迁移步骤
1) 清单化非 RESTful 的路由（如 `/api/instances/delete`），统一为 `DELETE /api/instances/<id>`。
2) 统一 Blueprint 注册与 URL 前缀，避免不同模块前缀不一致。
3) 校验文档并在前端路由/接口层同步更新。

## 涉及代码位置
- `app/routes/*.py`
- `app/routes/__init__.py`

---

## 资源与路径设计（详细）
- 统一前缀：`/api/*`；页面路由保持非 `/api` 前缀。
- 资源命名使用复数：`/api/instances`, `/api/credentials`, `/api/accounts`, `/api/tags`。
- 详情：`/api/<resource>/<int:id>`；子资源：`/api/instances/<int:id>/credentials`。
- 非幂等动作（少量）：以子路径表达，如 `/api/instances/<int:id>/test-connection`（需限制频率与日志记录）。

## HTTP 方法语义
- `GET /api/instances`：列表；可带 `q/page/per_page/sort_by/order`。
- `GET /api/instances/<id>`：详情。
- `POST /api/instances`：创建；返回 `201` 并携带 `Location`（可选）。
- `PUT /api/instances/<id>`：整体更新（要求字段完整）。
- `PATCH /api/instances/<id>`：部分更新（仅变更字段）。
- `DELETE /api/instances/<id>`：删除；成功 `204` 或 `200`，保持一致性（推荐 `204`）。

## 参数统一与约定
- 列表筛选：`q`（文本模糊），`sort_by`（受限字段）、`order`（`asc/desc`）。
- 分页：`page`（默认1），`per_page`（默认20，最大100）。
- 过滤字段遵循资源模型字段名，避免出现重复语义的别名（如 `keyword` 与 `q`）。

## 返回契约统一
- 所有 `/api/*` 返回走 `APIResponse`；成功：`success=true + data + message`；失败：`success=false + code + message + details`。
- 创建成功返回 `201` 时，`APIResponse.success_response` 的 `status_code` 可设为 `201`，并附加 `Location` 头（配置在响应对象）。

## 版本与演进（可选）
- 若需版本化，使用 `/api/v1/...` 前缀；旧版逐步下线时维持路由映射与兼容层。

## 迁移示例
- 旧：`POST /api/instances/delete?id=1` → 新：`DELETE /api/instances/1`。
- 旧：`POST /api/instances/update`（表单） → 新：`PUT /api/instances/<id>`（JSON）。
- 旧：`GET /api/instances/list_all` → 新：`GET /api/instances?page=1&per_page=20`。

## 代码示例
```python
from app.utils.api_response import APIResponse

def get_instances():
    # 读取统一参数（校验细节在校验文档）
    # service 返回数据按统一契约：列表与分页信息
    data = instance_service.list(q=..., page=..., per_page=..., sort_by=..., order=...)
    return APIResponse.success_response(data=data)

def delete_instance(id: int):
    instance_service.delete(id)
    return APIResponse.success_response(message="删除成功", status_code=204)
```

## 验收标准
- 样本抽取 10 条非 RESTful 路由均已迁移到标准方法与路径。
- 所有列表接口支持统一的分页/排序参数；返回结构一致。
- 创建/删除接口的状态码统一（201/204）并与文档匹配。

## 风险与回退
- 风险：前端依赖旧路径或方法；需提供路由映射与兼容期。
- 回退：保留旧路由的临时兼容层（内部调用新实现），并输出弃用日志，逐步关闭。