# accounts_sync（services/accounts_sync + tasks/accounts_sync_tasks.py）

## Core Purpose

- 提供账户同步的两阶段流程（清单 inventory + 权限 collection），并支撑：
  - 单实例同步（页面/接口触发）
  - 批量/任务同步（后台任务 + 会话记录）

## Unnecessary Complexity Found

- （已落地）`app/services/accounts_sync/accounts_sync_service.py:19`：
  - 在已启用 `from __future__ import annotations` 的前提下，仍保留 `TYPE_CHECKING ... else ...` 的运行时类型别名注入（`Instance = Any` / `JsonDict = dict[...]` 等）。
  - 该分支不影响业务行为，只增加模块级噪音与维护成本。

- （已落地）`app/services/accounts_sync/accounts_sync_service.py:53`：
  - 失败结果 dict 的结构在多个异常分支中重复拼装（success/message/error/counts），属于重复样板。

- （已落地）`app/tasks/accounts_sync_tasks.py:29`：
  - `ACCOUNT_TASK_EXCEPTIONS` 在函数体内重复定义，并通过参数层层传递到 `_sync_single_instance`。
  - 该异常集合为纯常量，适合提升为模块常量并直接引用。

- （已落地）`app/tasks/accounts_sync_tasks.py:268`：
  - `if "session" in locals() and session:` 属于无收益的防御性写法（`session` 已在外层定义），降低可读性。

## Code to Remove

- `app/services/accounts_sync/accounts_sync_service.py:19`：移除运行时类型别名注入分支（可删/可减复杂度 LOC 估算：~10-25）。
- `app/services/accounts_sync/accounts_sync_service.py:53`：用统一的 `_build_failure_result` 去除重复失败结果样板（可删/可减复杂度 LOC 估算：~20-40）。
- `app/tasks/accounts_sync_tasks.py:29`：将异常集合提升为模块常量并移除参数传递（可删/可减复杂度 LOC 估算：~10-20）。
- `app/tasks/accounts_sync_tasks.py:268`：移除 `locals()` 防御分支（可删/可减复杂度 LOC 估算：~1-3）。

## Simplification Recommendations

1. 彻底移除“为类型检查服务的运行时代码”
   - Current: `TYPE_CHECKING ... else ...` 在运行时注入大量类型别名。
   - Proposed: 仅保留 `TYPE_CHECKING` 导入；运行时代码只保留业务逻辑。

2. 统一失败结果构造
   - Current: 多处复制同一结构的失败 dict。
   - Proposed: `_build_failure_result(message)` 作为唯一入口，避免字段漂移与重复修改。

3. 常量上提，移除无意义参数传递
   - Current: `account_task_exceptions` 在任务函数内定义，再传递到 helper。
   - Proposed: 模块常量 `ACCOUNT_TASK_EXCEPTIONS` + 直接引用。

## YAGNI Violations

- 为“类型存在/运行时注解”而保留的别名注入与分支（在启用 postponed annotations 后缺少必要性）。
- `locals()` 检查这种“看起来更安全”的写法缺少明确运行时用例支撑。

## Final Assessment

- 可删/可减复杂度估算：~41-88（已落地，主要来自删除运行时类型别名注入 + 去重复样板）
- Complexity: High -> Medium
- Recommended action: Proceed（本轮聚焦删样板/删噪音，不改同步业务分支与输出结构）

