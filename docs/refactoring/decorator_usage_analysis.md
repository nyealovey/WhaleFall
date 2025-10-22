# 装饰器使用情况概览（2025-10-17）

本文件用于记录当前仓库中权限/验证相关装饰器的真实使用情况，已与最新代码状态同步。

## 1. 装饰器使用统计

| 装饰器 | 使用次数 | 主要位置 | 状态 |
|--------|---------|---------|------|
| `@login_required` | 60+ | 所有受保护路由 | ✅ 核心装饰器 |
| `@admin_required` | 5 | 日志清理、缓存清理等 | ✅ 管理接口必需 |
| `@view_required` | 20+ | 多数查询接口 | ✅ 只读权限装饰器 |
| `@create_required` | 15+ | 实例、标签、凭据等创建接口 | ✅ CRUD 必需 |
| `@update_required` | 18+ | 多数更新接口 | ✅ CRUD 必需 |
| `@delete_required` | 10+ | 删除接口 | ✅ CRUD 必需 |
| `@scheduler_view_required` | 5 | `app/routes/scheduler.py` 查看类接口 | ✅ 调度查看权限 |
| `@scheduler_manage_required` | 7 | `app/routes/scheduler.py` 管理类接口 | ✅ 调度管理权限 |
| `@permission_required` | 0（被包装器使用） | 内部封装 | ✅ 底层依赖 |
| `@login_required_json` | 0 | 已删除 | ❌ 已清理 |
| `@validate_json` | 0 | 已删除 | ❌ 已清理 |
| `@rate_limit` | 0 | 已删除 | ❌ 已清理 |

> 统计命令示例：`rg -n "@login_required" app/routes/`

## 2. 核心装饰器说明

- `@login_required`：封装统一的登录态校验与结构化日志输出。
- `@admin_required`：基于登录校验附加管理员角色检查。
- `@permission_required`：底层权限判断，`view/create/update/delete_required` 均基于它实现。
- `@scheduler_view_required` / `@scheduler_manage_required`：调度器路由的专用权限分层。

## 3. 已移除装饰器（2025-10）

- `@login_required_json`：与 `@login_required` 功能重复。
- `@validate_json`：改为在路由内部执行 JSON/必填字段检测（参见 `examples/validation/standard_api_templates.py`）。
- 统一使用 `app/utils/rate_limiter.py` 中的速率限制装饰器（如 `login_rate_limit`）。

## 4. 建议的请求验证模式

1. **JSON 写接口**  
   `data = request.get_json(silent=True)` → 判断类型与必填字段 → `DataValidator` 做领域校验。

2. **查询接口**  
   使用 `request.args.get("page", 1, type=int)` 等形式完成安全类型转换。

3. **错误处理**  
   尽量抛出 `ValidationError` / `AuthenticationError` / `AuthorizationError` 等自定义异常，由全局异常处理器统一返回响应。

## 5. 后续关注点

- 如需速率限制，请评估 `app/utils/rate_limiter.py` 的装饰器工厂是否满足需求并在路由中使用。
