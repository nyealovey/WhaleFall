# services/accounts_permissions（权限快照视图 + 权限事实构建）

## Core Purpose

- 提供稳定的 permission snapshot 读取口径（v4）：缺失/版本不匹配时显式报错，避免静默兜底。
- 将 raw snapshot 派生为 query-friendly 的 permission facts（供统计查询/规则评估输入）。

## Unnecessary Complexity Found

- （已落地）`app/services/accounts_permissions/facts_builder.py:393`：`capabilities` 的去重由 `_add_capability` 保障（同名 capability 只会 append 一次），仍额外 `set(...)` 属于冗余。

## Code to Remove

- `app/services/accounts_permissions/facts_builder.py:393`：移除 `set(...)`（可删 LOC 估算：~1）。

## Simplification Recommendations

1. 保持单向“事实派生”流程清晰
   - `snapshot -> (internal contracts parse/normalize) -> roles/privileges/capabilities -> facts`
   - 不再引入新的抽象层（避免把业务规则藏进通用 helper）。

## YAGNI Violations

- `capabilities` 的重复去重（`set(...)`）缺少必要性：当前 `_add_capability` 已是唯一入口并显式防重复。

## Final Assessment

- 可删 LOC 估算：~1（已落地）
- Complexity: Low -> Lower
- Recommended action: Done（仅移除冗余去重，不动输出结构/契约）。

