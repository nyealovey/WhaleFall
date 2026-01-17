# services/common（filter_options_service）

## Core Purpose

- 提供多页面复用的下拉选项：标签/分类/实例/数据库。
- 提供 Common API 的 options 输出：
  - `/api/v1/instances/options`
  - `/api/v1/databases/options`
  - 数据库类型 options

## Unnecessary Complexity Found

- （已落地）`app/services/common/filter_options_service.py:69-107`：Repository 已返回稳定 ORM 模型，但 Service 使用 `cast/getattr + _coalesce_*` 做“字段可能不存在”的防御性取值样板。
  - 这会遮蔽真正的数据结构，并引入重复的类型/默认值噪音。

- （已落地）`app/services/common/filter_options_service.py:83-107`：`filters.limit/offset` 与 `total_count` 本身就是 `int`，再 `int(...)` 属于冗余转换。

## Code to Remove

- `app/services/common/filter_options_service.py:69-107`：移除 `cast/getattr/_coalesce_*` 样板，直接基于 ORM 字段构造 DTO（可删 LOC 估算：~30-40）。

## Simplification Recommendations

1. DTO 映射：直接使用 ORM 字段
   - Current: 样板化的 `getattr(..., default)` 让读者误以为字段随时缺失。
   - Proposed: Repository 的返回类型即契约，Service 只做数据映射与轻量格式化（如 `isoformat()`）。
   - Impact: 逻辑更直观，减少分支与默认值噪音。

## YAGNI Violations

- 为“字段可能不存在/类型可能不对”预留的 `_coalesce_* + getattr` 兜底（缺少明确运行时证据；Repository 返回为 ORM 模型）。

## Final Assessment

- 可删 LOC 估算：~30-40（已落地）
- Complexity: Low -> Lower
- Recommended action: Done（以删除防御性取值样板为主，不动对外接口）。

