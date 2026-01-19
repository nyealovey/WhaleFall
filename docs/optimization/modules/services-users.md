# services/users + routes/users + templates/users

## Core Purpose

- 提供用户管理相关读写服务（list/stats/detail/write），供 API 与表单视图复用。
- 提供用户管理页面入口与用户表单页面渲染。

## Unnecessary Complexity Found

- `app/routes/users.py:31-67`: `index()` 内层 try/except + `log_fallback()` + fallback `render_template()`。
  - 该页面仅组装静态 `role_options` 与 querystring，不依赖 DB/service；属于“无依据兜底”。
  - 同时又被 `safe_route_call()` 包裹，形成重复的异常处理与日志路径。
- `app/services/users/user_write_service.py:122-130`: `_is_target_state_admin()` 仅调用一次且输入为临时 dict，可直接内联为 `role/is_active` 判断。
- `app/services/users/user_write_service.py:58-60`: `create()` 将 `parsed` 字段再赋给局部变量后立即使用，无收益。

## Code to Remove

- `app/routes/users.py:31-67`：删除 `index()` 内层 try/except fallback（可删 LOC 估算：~35）。
- `app/services/users/user_write_service.py:58-60, 122-125`：删除局部变量与一次性 helper，并内联条件（可删 LOC 估算：~6）。
- `app/services/users/user_write_service.py:26-28`：当不再需要 `PayloadMapping` 时，移除 `TYPE_CHECKING` 分支（可删 LOC 估算：~3）。

## Simplification Recommendations

1. `app/routes/users.py:index()`
   - Current: `_execute()` 内部 try/except + `log_fallback()` + fallback `render_template()`，外层再 `safe_route_call()`。
   - Proposed: 仅保留「组装参数 → 渲染模板」的主路径，由 `safe_route_call()` 统一包裹；移除无依据降级分支。
   - Impact: 降低嵌套与分支数，减少维护点。

2. `app/services/users/user_write_service.py:_ensure_last_admin()`
   - Current: 传入 `dict` 并调用一次性 `_is_target_state_admin()`。
   - Proposed: 改为显式参数 `role/is_active`，直接判断目标状态并删除 `_is_target_state_admin()`。
   - Impact: 更直观，减少“键名/类型”心智负担。

## YAGNI Violations

- `app/routes/users.py:31-67`: 该页面无真实失败来源（不依赖 DB/service），仍实现 catch-all fallback，属于“为了可能的错误而写”的代码。

## Final Assessment

- 可删 LOC 估算：~44
- Complexity: Medium -> Low
- Recommended action: Proceed（不改对外接口，仅删减冗余分支与一次性 helper）。

