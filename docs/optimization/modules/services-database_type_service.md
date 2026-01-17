# services/database_type_service.py（数据库类型配置/表单选项）

## Core Purpose

- 提供数据库类型配置的查询封装（全量/启用/按名称）与表单 options 映射。

## Unnecessary Complexity Found

- （已落地）`app/services/database_type_service.py:1`：该 Service 在仓库内无任何引用（`rg -n "DatabaseTypeService"` 仅命中本文件），属于死代码。
  - 它只是薄封装转发到 Repository/Model（`DatabaseTypeRepository`/`DatabaseTypeConfig`），额外引入一层概念与维护面。

## Code to Remove

- `app/services/database_type_service.py:1`：删除整个文件（可删 LOC 估算：~77）。

## Simplification Recommendations

1. 以 Repository/Model 作为唯一查询入口
   - 若未来需要“表单 options”映射：在实际调用处（route/service）就地构建最小 DTO，避免为了潜在复用提前新增 Service。

## YAGNI Violations

- 为“可能会复用的数据库类型表单 options”预留 `DatabaseTypeService`（缺少实际调用点/测试覆盖）。

## Final Assessment

- 可删 LOC 估算：~77（已落地）
- Complexity: Lower (dead code removed)
- Recommended action: Done（确认无引用后直接删除）。

