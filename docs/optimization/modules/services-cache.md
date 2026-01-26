# services/cache + utils/cache_utils.py

## Core Purpose

- CacheManager：封装 Flask-Caching 的统一接口（`get/set/delete/stats` + 容错 + 日志）。
- CacheActionsService：承接 cache namespace 的“动作编排”(stats/clear-user/clear-instance/clear-all/clear-classification/分类缓存统计)。
- OptionsCache：下拉/筛选项短 TTL 缓存访问器（固定 key + 最终一致）。
- ClassificationCache：分类规则缓存访问器（固定 key + TTL + 显式失效）。

## Unnecessary Complexity Found

- （已落地）`CacheService` 子系统已删除，缓存入口收敛为 `CacheManagerRegistry`（避免两套抽象并存）。

## Code to Remove

- 无（已完成移除 `CacheService`，并将分类缓存/健康检查/缓存管理动作迁移到 `CacheManager`/现有 health service）。

## Simplification Recommendations

1. 固定 key + 短 TTL 优先
   - options 类数据（实例/数据库/标签/分类等）读多写少，使用固定 key + 短 TTL 达成最终一致，避免复杂失效链路。
2. 避免写放大
   - 分类规则缓存不再为“统计展示”额外写入 `classification_rules:{db_type}`，统计从 `classification_rules:all` 计算分组即可。
3. 不引入 scan/keys
   - 仅允许对固定 key 执行 delete；禁止在业务路径引入 Redis `SCAN/KEYS`。

## YAGNI Violations

- 为了“看起来可清理”而保留无法精确实现的模式删除（scan/keys）属于典型 YAGNI 与风险点。

## Final Assessment

- Complexity: Medium -> Lower（单一抽象 + 固定 key + 短 TTL，降低失效复杂度与写放大）
- Recommended action: Proceed（继续以 OptionsCache/ClassificationCache 这类“业务缓存访问器”承载 key/TTL 约定，避免散落在 service/routes）。
