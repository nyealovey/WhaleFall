# Module: `app/infra`（logging/route_safety/error_mapping/flask_typing/database_batch_manager）

## Simplification Analysis

### Core Purpose

- `app/infra/route_safety.py`：统一视图/HTTP 边界的事务提交与异常封装（`safe_route_call`），并提供统一日志字段封装（`log_with_context/log_fallback`）
- `app/infra/error_mapping.py`：将 core 异常映射到 HTTP 状态码（仅在 HTTP 边界使用）
- `app/infra/flask_typing.py`：Flask/扩展运行期属性的 typing helpers（Infra 层专用，避免 core 依赖 Flask）
- `app/infra/logging/queue_worker.py`：结构化日志异步批量持久化（后台线程 + 批量写 DB）
- `app/infra/database_batch_manager.py`：批量 DB 操作 helper（目前仅单测覆盖，用于验证“允许部分成功”的批处理语义）

### Unnecessary Complexity Found

- `app/infra/database_batch_manager.py:249`：`rollback()` 原实现用 try/except 包裹 `list.clear()` 这类几乎不可能失败的操作，并在异常时“吞掉继续”，属于无依据的防御性分支/兜底逻辑（与仓库硬约束冲突）。

### Code to Remove

- `app/infra/database_batch_manager.py:249`（已改写）- 移除 `rollback()` 的 try/except 兜底分支，仅保留必要的 warning + clear
- Estimated LOC reduction: ~13 LOC（净删；去掉无依据兜底逻辑）

### Simplification Recommendations

1. Infra 层的“边界工具”只承担边界职责，不做额外兜底
   - Current: 在不可能失败的代码上添加 try/except + 吞异常
   - Proposed: 删除无依据兜底；异常应当自然暴露给测试/调用方
   - Impact: 分支更少、更符合硬约束；也避免隐藏真实 bug

### YAGNI Violations

- 对 `list.clear()`/简单分支增加 try/except 的“习惯性兜底”

### Final Assessment

Total potential LOC reduction: ~13 LOC（已落地）
Complexity score: Low
Recommended action: `route_safety/error_mapping/queue_worker` 已较为聚焦；后续优化应优先从更高耦合的业务模块入手

