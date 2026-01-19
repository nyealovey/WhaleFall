# partition-admin（api/v1/namespaces/partition.py + routes/partition.py + templates/admin/partitions）

## Core Purpose

- 提供分区管理页面（管理中心）与对应 API：
  - 查询：info/status/list/statistics/core-metrics
  - 动作：创建分区、清理旧分区（均需 CSRF + admin 权限）

## Unnecessary Complexity Found

- （已落地）`app/api/v1/namespaces/partition.py:288` / `app/api/v1/namespaces/partition.py:337`：`request.get_json(silent=True)` 后已保证 `raw` 为 dict，却仍在读取字段时重复 `isinstance(raw, dict)` 判定与 `object` 标注，属于冗余噪音。

## Code to Remove

- `app/api/v1/namespaces/partition.py:288` / `app/api/v1/namespaces/partition.py:337`：移除重复的 `isinstance(raw, dict)` 分支（可删 LOC 估算：~2）。

## Simplification Recommendations

1. API 层 payload 解析保持“最小、直观、无额外兜底”
   - 统一使用 `raw: dict[str, object] = ... if isinstance(..., dict) else {}` 的写法；
   - 业务校验交给 Service/schema（这里已有 `PartitionManagementService().*_from_payload` + `ValidationError`）。

## YAGNI Violations

- 为“raw 可能不是 dict”而重复检查（已经在赋值时完成收敛）。

## Final Assessment

- 可删 LOC 估算：~2（已落地）
- Complexity: Low -> Lower
- Recommended action: Done（仅降噪，不改 API 行为/响应结构）。

