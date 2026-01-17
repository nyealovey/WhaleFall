# services/ledgers + repositories/ledgers + templates/(TBD)

## Core Purpose

- 账户台账：提供账户列表/权限详情/变更历史的读模型服务（供 API 与页面复用）。
- 数据库台账：提供数据库台账列表的查询服务与投影（Repository 输出 projection，Service 输出 DTO）。

## Unnecessary Complexity Found

- （已落地）`app/services/ledgers/accounts_ledger_permissions_service.py:29-47`: 大量 `getattr(..., default)` + `cast(...)` 的“防御性取值”样板。
  - repository 返回 `AccountPermission` 且 join 了 Instance（`first_or_404()`），按当前路径不需要反复 `getattr`。

- （已落地）`app/services/ledgers/accounts_ledger_change_history_service.py:32-79`: 对 model 字段大量 `getattr/cast`。
  - `AccountChangeLog`/`AccountPermission` 字段稳定，样板会掩盖核心逻辑（diff 提取/时间格式化）。

- （已落地）`app/services/ledgers/accounts_ledger_list_service.py:30-48`: 对 `instance`/`instance_account` 的可空分支属于过度防御。
  - Repository 使用 inner join（`accounts_ledger_repository.py:_build_account_query()`），按查询语义二者应始终存在。

- （已落地）`app/services/ledgers/database_ledger_service.py:151-177`: `_build_item()` 以 `object` 入参并用 `cast/getattr` 访问字段，但上游实际返回 `DatabaseLedgerRowProjection`。

## Code to Remove

- `app/services/ledgers/accounts_ledger_permissions_service.py`: 移除 `cast/getattr` 样板，改为直接属性访问（可删 LOC 估算：~10-15）。
- `app/services/ledgers/accounts_ledger_change_history_service.py`: 移除 `cast/getattr` 样板（保留明确的 COMPAT 分支与异常日志），直接访问 model 字段（可删 LOC 估算：~10-15）。
- `app/services/ledgers/accounts_ledger_list_service.py`: 移除不必要的可空分支，收敛为更直观的构造（可删 LOC 估算：~8-12）。
- `app/services/ledgers/database_ledger_service.py`: 将 `_build_item()` 入参收敛为 `DatabaseLedgerRowProjection` 并移除 `cast/getattr`（可删 LOC 估算：~10-15）。

## Simplification Recommendations

1. Service 层优先表达“数据映射”，不要用 `getattr` 掩盖真实必需字段
   - Current: 大量 `getattr(..., default)` 让读者误以为字段可能缺失。
   - Proposed: 直接使用 ORM/Projection 字段，缺失就让错误暴露（符合“不吞异常继续”的约束）。

2. Repository 已通过 inner join 保证关系存在时，Service 不再重复做空值兜底
   - Current: `instance is None` / `instance_account is None` 分支几乎不可能触发。
   - Proposed: 直接使用关系对象，减少分支与默认值字符串。

## YAGNI Violations

- `app/services/ledgers/accounts_ledger_permissions_service.py:31-53`: 为“可能不存在的字段”预留大量 default 值分支（缺少明确证据）。

## Final Assessment

- 可删 LOC 估算：~40-55
- Complexity: Medium -> Low
- Recommended action: Done（以删除 `getattr/cast` 样板与不必要空值分支为主，不动对外接口）。
