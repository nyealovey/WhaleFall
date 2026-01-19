# services/partition + partition_management_service.py

## Core Purpose

- PartitionManagementService：提供分区创建/清理/查询的核心能力（供 routes/tasks 调用）。
- PartitionReadService：为分区管理 API 提供只读快照、列表与 core-metrics 图表数据。

## Unnecessary Complexity Found

- （已落地）`app/services/partition_management_service.py:25-35`：
  - `PARTITION_SERVICE_EXCEPTIONS` 标注为 `BaseException` 的类型元组，但实际枚举的都是 `Exception` 子类。
  - 下游因此出现 `safe_exc = exc if isinstance(exc, Exception) else Exception(...)` 的样板。

## Code to Remove

- `app/services/partition_management_service.py:25-35`：将异常元组收敛为 `Exception` 子类集合（可删 LOC 估算：~4-8，主要来自移除 `safe_exc` 样板与 BaseException 误导）。

## Simplification Recommendations

1. 防御性日志收敛：避免“永远不会触发”的 BaseException 兼容样板
   - Current: 类型标注过宽，引出多余的 `safe_exc` 转换。
   - Proposed: 明确异常集合为 `Exception`，日志直接记录 `exc`。
   - Impact: 降噪、降低读者误判风险（以为会捕获 KeyboardInterrupt 等）。

## YAGNI Violations

- “为了处理 BaseException”而存在的兜底转换样板（但实际未捕获 BaseException 子类）。

## Final Assessment

- 可删 LOC 估算：~4-8（已落地）
- Complexity: Medium -> Lower
- Recommended action: Done（保持对外行为不变，仅收敛异常类型与去除冗余样板）。

