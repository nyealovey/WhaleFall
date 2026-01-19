# Module: `app/utils/http`（decorators/request_payload/response_utils/proxy_fix_middleware/pagination）

## Simplification Analysis

### Core Purpose

- Web/API 的权限/CSRF 装饰器（`app/utils/decorators.py`）
- 请求 payload 解析与基础规范化（`app/utils/request_payload.py`）
- API 响应封套（`app/utils/response_utils.py`）
- 代理头解析中间件（`app/utils/proxy_fix_middleware.py`）
- 分页参数解析（`app/utils/pagination_utils.py`）

### Unnecessary Complexity Found

- `app/utils/decorators.py:389`：`view_required/create_required/update_required/delete_required` 通过 overload + “惰性装饰器/自定义 permission”实现了多种调用方式，但仓库实际只使用最简单形态（`@view_required` 或 `create_required(func)`）。该“可扩展调用方式”属于 YAGNI，增加了大量样板代码与阅读成本。
- `app/utils/decorators.py:372`：`has_permission()` 每次调用都构造角色权限映射（dict/set），属于重复分配；可提升为模块级常量（不改变权限口径）。
- `app/utils/decorators.py:534`：未被仓库引用的 `scheduler_manage_required` 属于无调用方 API 面（YAGNI）。
- `app/utils/response_utils.py:101`：未被仓库引用的 `jsonify_unified_error`（且 doc 口径与实现不一致）属于无调用方接口（YAGNI），移除更清晰。

### Code to Remove

- `app/utils/decorators.py:389`（已删除）- CRUD wrapper 的 overload/可选调用方式（净删大量样板）
- `app/utils/decorators.py:372`（已改写）- 将权限映射改为模块级常量 `_ROLE_PERMISSIONS`
- `app/utils/decorators.py:401`（已删除）- `scheduler_manage_required`
- `app/utils/response_utils.py:101`（已删除）- 未使用的 `jsonify_unified_error`
- `CLAUDE.md:105`（已更新）- 文档口径改为 `jsonify_unified_error_message(...)`
- Estimated LOC reduction: ~161 LOC（`decorators.py` 净删 ~146 + `response_utils.py` 净删 15）

### Simplification Recommendations

1. 删除“多形态调用方式”的样板，保留仓库实际使用的最小接口
   - Current: overload + func/None 双形态 + 可选 permission 参数
   - Proposed: `view_required/create_required/update_required/delete_required` 直接薄封装 `permission_required("...")`
   - Impact: 大幅减少代码体积与心智负担；不改变现有路由使用方式

2. 将静态映射常量化，避免重复分配
   - Current: `has_permission()` 内部重复创建 dict/set
   - Proposed: `_ROLE_PERMISSIONS` 常量 + `frozenset`（只读）
   - Impact: 降噪；轻量性能收益；不改变权限判断口径

### YAGNI Violations

- CRUD wrapper 的“自定义 permission/惰性装饰器模式”：当前仓库无用例，且 `permission_required()` 已覆盖自定义需求。
- `scheduler_manage_required`、`jsonify_unified_error`：无调用方的对外暴露接口。

### Final Assessment

Total potential LOC reduction: ~161 LOC（已落地）
Complexity score: Medium → Low
Recommended action: 已完成最小必要形态收敛；后续如出现新调用方式需求，优先直接使用 `permission_required()` 而非再次扩展 CRUD wrapper

