# Module: `app/utils/logging/*` + `app/utils/structlog_config.py`

## Simplification Analysis

### Core Purpose

提供结构化日志的最小可用能力：
- request/user 上下文注入（contextvars + Flask request context）
- 日志事件标准化并写入数据库队列（handler）
- 统一错误 → 可对外响应 payload（enhanced_error_handler）

### Unnecessary Complexity Found

- `app/utils/logging/error_adapter.py:205`：`get_error_suggestions()` 每次调用都临时创建 `suggestions_map`，属于纯重复分配（逻辑不变，但实现有不必要的开销与噪音）。
- `app/utils/structlog_config.py:478`：`enhanced_error_handler()` 里构造 `extra_payload` 采用“先创建空 dict 再 update”模式，属于可直接压缩的一次性样板代码。
- `app/utils/structlog_config.py:570`：`error_handler()` 使用 `ERROR_HANDLER_EXCEPTIONS=(Exception,)` 作为仅一次使用的间接层，降低可读性（行为与 `except Exception` 等价）。
- `app/utils/structlog_config.py:428`：存在未被仓库使用的 logger wrapper（`get_api_logger`），属于对外暴露但无调用方的 YAGNI API 面（已删除；当前该区域直接从 `get_system_logger()` 进入 `get_auth_logger()`）。
- `app/utils/logging/__init__.py:1`：`__all__ = []` 无实际收益（移除即可）。

### Code to Remove

- `app/utils/structlog_config.py:428` - 未使用的 `get_api_logger` wrapper（YAGNI；已删除）
- `app/utils/structlog_config.py:570` - `ERROR_HANDLER_EXCEPTIONS` 间接层（已删除，改为 `except Exception`）
- `app/utils/logging/error_adapter.py:205` - 每次调用重复创建的 `suggestions_map`（已改为模块级常量 + 返回拷贝）
- `app/utils/logging/__init__.py:1` - `__all__ = []`（已删除）
- Estimated LOC reduction: ~16 LOC（本模块净删为主；不改字段/返回结构）

### Simplification Recommendations

1. 将“纯数据映射”提升为模块级常量，并保持返回值为新 list
   - Current: 每次调用重新构造 dict/list
   - Proposed: 常量化存储（tuple）+ `list(...)` 返回，保持“调用方可修改但不影响后续调用”的语义
   - Impact: 降噪 + 轻量性能收益（无行为变化）

2. 移除一次性间接层与未使用 wrapper
   - Current: 常量包装 `Exception`、未使用的 `get_api_logger`
   - Proposed: 直接写 `except Exception`；删除无调用方 wrapper
   - Impact: API 面收敛，减少维护点（无行为变化）

### YAGNI Violations

- `get_api_logger`：无调用方/无测试覆盖的“对外入口”，只增加可被依赖的面。

### Final Assessment

Total potential LOC reduction: ~16 LOC（已落地）
Complexity score: Low → Lower
Recommended action: 已完成本模块的低风险极简化；后续如需更大幅度变更需先补充“日志输出口径/字段”契约测试

