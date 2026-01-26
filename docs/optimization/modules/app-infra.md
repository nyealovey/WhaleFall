# Module: `app/infra`（logging/route_safety/error_mapping/flask_typing）

## Simplification Analysis

### Core Purpose

- `app/infra/route_safety.py`：统一视图/HTTP 边界的事务提交与异常封装（`safe_route_call`），并提供统一日志字段封装（`log_with_context/log_fallback`）
- `app/infra/error_mapping.py`：将 core 异常映射到 HTTP 状态码（仅在 HTTP 边界使用）
- `app/infra/flask_typing.py`：Flask/扩展运行期属性的 typing helpers（Infra 层专用，避免 core 依赖 Flask）
- `app/infra/logging/queue_worker.py`：结构化日志异步批量持久化（后台线程 + 批量写 DB）
- `app/infra/database_batch_manager.py`：已删除（仅单测引用，无运行时调用点）

### Unnecessary Complexity Found

- Infra 层应尽量保持“边界工具”职责单一；历史遗留的 `database_batch_manager` 已整体移除，避免为了未来假设引入额外维护面。

### Code to Remove

- `app/infra/database_batch_manager.py`：已删除（净删整块代码与对应单测）

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
