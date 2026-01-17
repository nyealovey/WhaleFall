# services/cache + services/cache_service.py

## Core Purpose

- CacheService：封装 Flask-Caching 的统一接口，提供缓存读写、失效与健康检查。
- CacheActionsService：承接 cache namespace 的“动作编排”(stats/clear-user/clear-instance/clear-all/clear-classification/分类缓存统计)。

## Unnecessary Complexity Found

- （已落地）`app/services/cache_service.py:240-268`：
  - `get_classification_rules_cache()` 的返回类型标注为 `list[...]`，但实际写入 payload 是 dict（包含 `rules/cached_at/count`）。
  - 该类型漂移会迫使上层写更多 `cast/兼容逻辑`，并掩盖缓存 schema。

## Code to Remove

- `app/services/cache_service.py:240-268`：修正返回类型与实现，使其只在 payload 为 dict 时返回（可删/可减复杂度 LOC 估算：~5-10，主要是减少误导与后续 cast/兼容分支压力）。

## Simplification Recommendations

1. 缓存 schema 以写入端为准，读端类型应与写入一致
   - Current: 返回类型与真实 payload 不一致，阅读成本高。
   - Proposed: 读方法明确返回 dict payload；上层只需解析 `rules` 字段。
   - Impact: 降低类型噪音与错误使用概率。

## YAGNI Violations

- 缓存 schema 不明确导致的“为了兼容而兼容”的类型/分支（由错误类型标注触发）。

## Final Assessment

- 可删/可减复杂度估算：~5-10（已落地）
- Complexity: Medium -> Lower（主要体现在 schema 更明确，减少上层 cast/兼容噪音）
- Recommended action: Proceed（后续若要进一步极简，优先围绕“清缓存能力是否真实可实现”收敛口径，但这会涉及对外语义，需谨慎评估）。

