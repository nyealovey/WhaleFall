# database_sync（services/database_sync）

## Core Purpose

- 为“容量采集/同步”提供统一服务与协调器：
  - 连接管理（ConnectionFactory）
  - 库/表空间清单同步（InventoryManager）
  - 容量采集适配器（BaseCapacityAdapter + 各数据库实现）
  - 表容量采集（table_size_coordinator + table_size_adapters）
  - 落库持久化（CapacityPersistence 等）

## Unnecessary Complexity Found

- （已落地）`app/services/database_sync/adapters/base_adapter.py:1` / `app/services/database_sync/table_size_adapters/base_adapter.py:1`：
  - 已启用 `from __future__ import annotations` 的情况下，仍保留 `TYPE_CHECKING ... else ...` 运行时别名注入（`Instance = Any` / `DatabaseConnection = Any` / `Sequence = Any` 等）。
  - 这些分支不参与业务执行路径，只是为“运行时注解可用”提供兜底，属于纯噪音。

- （已落地）`app/services/database_sync/adapters/*.py`、`app/services/database_sync/table_size_adapters/*.py`：
  - 多处重复的 `TYPE_CHECKING ... else ...` 模板化代码，增加维护面与误导（暗示注解会在运行时求值）。

- （已落地）`app/services/database_sync/*:CONNECTION_EXCEPTIONS`：
  - 异常集合类型标注使用 `BaseException`，但枚举的均为 `Exception` 子类，过宽边界易引入不必要的“BaseException 兼容”样板。

## Code to Remove

- `app/services/database_sync/adapters/*.py`：移除运行时类型别名注入分支（可删/可减复杂度 LOC 估算：~20-50）。
- `app/services/database_sync/table_size_adapters/*.py`：同上（可删/可减复杂度 LOC 估算：~20-50）。
- `app/services/database_sync/{coordinator.py,table_size_coordinator.py,database_sync_service.py}:*`：异常集合类型标注收敛为 `Exception`（可删/可减复杂度 LOC 估算：~0-6）。

## Simplification Recommendations

1. 运行时不要为类型检查“注入别名”
   - Current: `TYPE_CHECKING ... else ...` 让模块级代码变长，且给读者错误暗示。
   - Proposed: 仅保留 `TYPE_CHECKING` 导入；运行时代码只保留业务逻辑。

2. 异常边界与真实语义一致
   - Current: `BaseException` 过宽，会让读者误以为要兼容 KeyboardInterrupt 等。
   - Proposed: 明确 `Exception`，贴合“业务/依赖错误”边界。

## YAGNI Violations

- “为了运行时注解可用”而保留的别名注入与分支（在启用 postponed annotations 后缺少必要性）。

## Final Assessment

- 可删/可减复杂度估算：~40-106（已落地，以删模板化噪音为主）
- Complexity: Medium -> Lower
- Recommended action: Proceed（本轮聚焦删噪音/收敛类型边界，不改容量采集/过滤/落库逻辑）

