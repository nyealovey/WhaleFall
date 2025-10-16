> 注意：本文件已被《统一改造执行计划》整合与编排。执行请以 `docs/refactoring/unified_refactoring_plan.md` 为准；本文件保留作专题说明与背景参考。

# 请求校验与参数统一方案

目标
- 保留并统一两类校验入口：`app/utils/data_validator.py`（严格领域校验）与 `app/utils/validation.py`（通用输入校验）。
- 使用 `app/utils/decorators.py` 中的 `validate_json(required_fields=[...])` 作为 JSON 写接口的必填字段检查入口。
- 统一查询参数命名模式：`q`、`sort_by`、`order`、`page`、`per_page`。

现状与差异（审计结论）
- 装饰器：`validate_json` 已实现，返回形如 `{"success": False, "message": "...", "code": "..."}` 的 JSON 响应；`login_required_json` 存在但在路由中未使用。
- 校验器：路由中已广泛使用 `DataValidator`（如 `instances.py` 的创建/编辑/批量接口），`InputValidator` 多为通用方法，目前在路由中直接使用较少；`security.py` 的 `sanitize_form_data`、`validate_required_fields` 也被用于表单场景。
- 错误返回：路由常见为内联 `jsonify({"error": "..."})`，全局错误处理器 `error_handler.py` 会将异常统一为 `{"error": message, "status_code": code, "timestamp": ...}`；`APIResponse` 工具存在但在路由中并不主用。
- 查询参数：多数路由已统一使用 `page`/`per_page`（默认 10 或 20）；`logs.py` 使用 `q`、`sort_by`、`order`，其命名契合统一方案。
- 扩展装饰器：`validate_json_types`、`validate_query` 未实现，当前仅作为规划项。

统一参数命名
- 搜索关键字：`q`（查询关键字）、`sort_by`、`order`（asc/desc）、`page`、`per_page`。
- 路径参数统一命名：`<int:instance_id>`, `<int:credential_id>`, `<int:account_id>`。
- 默认值建议：`page=1`，`per_page` 建议默认 `20`、最大 `100`（现状存在 `10/20/50` 的差异，迁移期保持兼容）。

统一校验与返回（建议与兼容策略）
- JSON 写接口入口统一使用 `@validate_json(required_fields=[...])`：
  - 当 `Content-Type` 为 `application/json` 时启用；检查 JSON 体存在与必填字段。
  - 失败返回当前实现的 JSON 结构：`{"success": False, "message": "...", "code": "..."}`（短期兼容）。
  - 中长期目标：在校验失败时抛出 `abort(400)` 或业务异常，交由全局错误处理器统一为 `{"error": message, "status_code": 400, "timestamp": ...}`。
- 领域校验优先使用 `DataValidator`，通用类型/范围/布尔转换可使用 `InputValidator`：
  - 布尔转换：`InputValidator.validate_boolean(value)`。
  - 整数范围：`InputValidator.validate_integer(value, min_val=..., max_val=...)`。
  - 时间解析：`app/utils/time_utils.py` 的 `time_utils.to_utc(...)` 等。

代码示例（对齐现状，并给出演进方向）
```python
from flask import request, jsonify
from app.utils.decorators import validate_json
from app.utils.data_validator import DataValidator

@validate_json(required_fields=["name", "db_type", "host", "port"])
def create_instance_api():
    # 进入时保证 JSON 体与必填字段存在
    data = request.get_json() or {}

    # 严格领域校验（现状做法）
    is_valid, error_msg = DataValidator.validate_instance_data(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # TODO（演进）：统一抛出错误，交由全局错误处理器返回一致结构
    # from flask import abort
    # if not is_valid:
    #     abort(400, description=error_msg)

    # 通过后执行业务逻辑 ...
    return jsonify({"message": "实例创建成功"}), 201
```

查询参数校验示例（上限兼容与统一建议）
```python
from flask import request

def list_logs_api():
    # 已有路由示例：logs.py
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)  # 现状为 50
    q = request.args.get("q", "").strip()
    sort_by = request.args.get("sort_by", "timestamp")
    order = request.args.get("order", "desc")

    # 建议：统一 per_page 上限（如 100），保留现状默认值，迁移期逐步收敛
    per_page = min(per_page, 100)
    # ... 继续执行业务逻辑
```

校验装饰器契约（现状与规划）
- 现状：`@validate_json(required_fields=[...])` 检查 JSON 体与必填字段，失败返回 `{"success": False, "message": "...", "code": "..."}`。
- 规划：
  - `@validate_json_types(types={...})`：按字段类型校验（未实现）。
  - `@validate_query(spec={...})`：查询参数契约式校验（未实现）。
  - 统一失败处理：抛错交由全局错误处理器输出统一结构（迁移期兼容）。

data_validator 与 validation 使用建议
- 严格领域数据走 `DataValidator`（如实例的 `name/db_type/host/port`）。
- 通用输入走 `InputValidator`（字符串、整数、布尔、邮箱、URL 等）。
- 表单场景可配合 `security.sanitize_form_data` 与 `validate_required_fields`。

错误返回统一（目标态）
- 路由层不直接构造错误 JSON，统一通过抛错交由全局错误处理器：`{"error": message, "status_code": code, "timestamp": ...}`。
- 现状兼容：保留内联 `jsonify({"error": "..."})` 的返回，逐步迁移。

迁移步骤
1) 对 JSON 写接口补齐 `@validate_json` 装饰器（存在 JSON 请求体时）。
2) 将分散在路由中的类型/范围校验迁移到 `DataValidator` / `InputValidator`。
3) 统一查询参数命名与默认值（`page/per_page/q/sort_by/order`），`per_page` 上限统一为 `100`。
4) 新增/改造错误处理路径：校验失败抛错交由全局错误处理器（逐步迁移）。

验收标准
- 随机抽取 5 个写接口：缺少必填字段时经 `@validate_json` 拦截；领域校验失败统一返回 400。
- 随机抽取 5 个列表接口：`page/per_page/q/sort_by/order` 命名一致；`per_page` 上限生效且默认值在迁移计划内。
- 统一错误路径：至少 3 个接口完成从内联 JSON 到全局错误处理器的迁移（返回结构一致）。

风险与回退
- 风险：前端依赖旧参数默认值/错误结构；需提供迁移说明与双写兼容期。
- 回退：保持内联 JSON 返回与装饰器当前行为，逐步切换到全局错误处理器；新增兼容层（接受旧参数别名、记录降级日志）。

涉及代码位置
- `app/utils/decorators.py`：`validate_json`、权限相关装饰器。
- `app/utils/data_validator.py`、`app/utils/validation.py`：领域校验与通用校验。
- `app/utils/security.py`：表单清理与必填校验。
- `app/utils/error_handler.py`：统一错误响应结构与日志。
- `app/routes/*.py`：校验与参数统一的落地位置（例如 `routes/instances.py`、`routes/logs.py`）。