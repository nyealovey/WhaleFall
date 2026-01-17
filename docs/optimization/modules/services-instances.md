# services/instances + routes/instances + templates/instances

## Core Purpose

- 提供实例管理相关的页面路由（列表/表单/详情/统计）与模板渲染。
- 提供实例相关的读写服务，供 API 与表单 View 复用（创建/更新/软删除/恢复、批量操作、列表/统计/详情读模型等）。

## Unnecessary Complexity Found

- 单次使用的“页面 Service + Context dataclass”抽象（routes 只是把字段拆开再喂给模板）：
  - `app/services/instances/instance_list_page_service.py:25` `InstanceListPageContext` + `InstanceListPageService` 仅被 `app/routes/instances/manage.py:13` 使用。
  - `app/services/instances/instance_detail_page_service.py:23` `InstanceDetailPageContext` + `InstanceDetailPageService` 仅被 `app/routes/instances/detail.py:13` 使用。
  - 这类抽象没有带来复用/扩展点，反而增加文件数与跳转成本。

- `app/routes/instances/manage.py:109-118`: `_load_related_blueprints()` 同时导入 `detail` 与 `statistics`。
  - `detail` 已由 `app/__init__.py:328` 通过 `blueprint_specs` 显式导入并注册；在此处再导入属于重复。

- `app/services/instances/instance_write_service.py:64-72`: `create()` 将 `params` 字段重复赋给局部变量，并对 `tag_names` 做冗余 `str()` 转换。
- `app/services/instances/instance_write_service.py:202-214`: `_resolve_create_credential_id()` 对 `credential_id` 做重复类型转换；该字段已由 `InstanceCreatePayload` schema 解析为 `int | None`。

## Code to Remove

- `app/services/instances/instance_list_page_service.py:1`：删除单次使用的列表页 PageService/Context，并将逻辑内联到 `app/routes/instances/manage.py:42`（可删 LOC 估算：~88）。
- `app/services/instances/instance_detail_page_service.py:1`：删除单次使用的详情页 PageService/Context，并将逻辑内联到 `app/routes/instances/detail.py:39`（可删 LOC 估算：~66）。
- `app/routes/instances/manage.py:112-115`：移除对 `detail` 的重复导入（保留对 `statistics` 的导入以注册路由）（可删 LOC 估算：~1-2）。
- `app/services/instances/instance_write_service.py:64-72, 202-209, 214`：删除冗余局部变量与重复类型转换，保留“凭据存在性校验”的必要逻辑（可删 LOC 估算：~10+）。

## Simplification Recommendations

1. 内联单次使用的 PageService
   - Current: routes → PageService → Context → routes 再逐字段拆开传模板。
   - Proposed: routes 直接组织必要的 repository/service 调用，并将渲染参数作为局部变量或 dict 传给模板。
   - Impact: 减少文件与 dataclass 层，降低维护成本。

2. `InstanceWriteService.create()` 去冗余
   - Current: 重复局部变量赋值 + schema 已保证类型后再次转换。
   - Proposed: 直接使用 `params` 字段，并将 `_resolve_create_credential_id()` 收敛为 `int | None -> int | None`（只做存在性校验）。
   - Impact: 逻辑更直观，减少无意义分支与异常路径。

## YAGNI Violations

- `app/services/instances/instance_list_page_service.py` / `app/services/instances/instance_detail_page_service.py`：为单次调用引入 PageContext/Service 层。

## Final Assessment

- 可删 LOC 估算：~165+
- Complexity: Medium -> Low
- Recommended action: Proceed（删单次抽象、保留现有对外接口与页面行为）。

