# services/accounts + routes/accounts + templates/accounts

## Core Purpose

- 提供账户相关页面：账户台账、账户统计、账户分类管理（routes + templates）。
- 提供账户分类管理的读写服务（rules/classifications/assignments/permissions 等），供 API 与表单/页面复用。

## Unnecessary Complexity Found

- （已落地）`app/routes/accounts/ledgers.py:21-27`: 账户台账页面仅需 `search/tags/classification/db_type` 的初始值。
  - 原先存在 `_parse_account_filters()` 解析 page/limit/instance_id/include_deleted/is_locked/is_superuser/plugin 等“页面未用到”的参数，属于过度解析；现已删除并内联为最小解析。

- （已落地）`app/services/accounts/account_classifications_read_service.py:34-36, 38-74`: 多处重复 try/except（log + raise SystemError）样板。
  - 同一模块同一口径的异常转换重复出现，可用一个小 helper 统一，减少噪音。

- （已落地）`app/routes/accounts/statistics.py:29-65`: 中间 dict 组装仅为转发参数，可直接在主流程渲染。

## Code to Remove

- （已删除）`app/routes/accounts/ledgers.py`: 删除 `_parse_account_filters()` / `_normalize_tags()` 与页面层 `AccountFilters` 依赖，改为在 `list_accounts()` 内仅解析页面实际使用的参数（可删 LOC 估算：~45）。
- （已删除）`app/services/accounts/account_classifications_read_service.py`: 引入最小 helper `_raise_system_error()` 并复用 `get_classification_by_id()/get_rule_by_id()`，删除重复 try/except 样板（可删 LOC 估算：~20+）。
- （已删除）`app/routes/accounts/statistics.py`: 删除仅转发用 helper/dict（可删 LOC 估算：~10）。

## Simplification Recommendations

1. 账户台账页面：只解析页面需要的 query
   - Current: 构造 `AccountFilters` 但页面只用其中少数字段。
   - Proposed: 保留 `db_type/search/classification/tags`，其余交由前端/调用方按需使用。
   - Impact: 页面路由更直观，减少“看起来在做分页但实际上没用”的误导。

2. 账户分类 read service：统一异常包装
   - Current: 多处 `try/except Exception -> log_error -> raise SystemError`。
   - Proposed: 统一在一个 helper 中，调用点只保留一行。
   - Impact: 降低重复噪音，便于后续维护。

## YAGNI Violations

- （已修复）`app/routes/accounts/ledgers.py`: 为页面渲染预先解析大量可能用不到的筛选字段。

## Final Assessment

- 可删 LOC 估算：~75+
- Complexity: Medium -> Low
- Recommended action: Done（以删冗余解析与重复样板为主，不动对外接口）。
