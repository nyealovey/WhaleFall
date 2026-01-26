# 003 缓存策略优化进度（Progress）

关联方案: [003-cache-strategy-optimization-plan.md](003-cache-strategy-optimization-plan.md)

> 状态: Active
> 负责人: @shiyijiufei
> 创建: 2026-01-25
> 最后更新: 2026-01-25
> 范围: Options 缓存（短 TTL）、分类缓存写放大治理、key/TTL 规范化与可观测性

---

## 当前状态(摘要)

- 已完成: 引入 `CACHE_OPTIONS_TTL`，新增 `OptionsCache` 并接入 `FilterOptionsService`，unit/contract tests 通过。
- 已完成: 分类规则缓存不再写入 `classification_rules:{db_type}`；分类缓存统计改为从 `classification_rules:all` 计算分组。
- 待处理(可选): Dashboard TTL 配置化；清理/标注 `Settings` 中未被消费的 cache 配置项。

## Checklist

### Phase 0：补齐“缓存策略文档 + 可观测口径”

- [x] 输出并维护方案文档: `docs/changes/refactor/003-cache-strategy-optimization-plan.md`
- [x] 为 Options 缓存引入统一 TTL 配置项 `CACHE_OPTIONS_TTL`

### Phase 1：引入 OptionsCache（FilterOptions 缓存化）

- [x] `Settings` 增加 `cache_options_ttl_seconds`（alias: `CACHE_OPTIONS_TTL`）并写入 `app.config`
- [x] 新增 `app/services/common/options_cache.py`（固定 key + 短 TTL + registry 获取）
- [x] `FilterOptionsService` 读路径接入缓存（命中判断使用 `cached is not None`，空列表也缓存）
- [x] 单测覆盖：`tests/unit/test_settings_cache_options_ttl.py`、`tests/unit/services/test_filter_options_service_cache.py`
- [x] 契约不回归：`tests/unit/routes/test_api_v1_common_options_contract.py`

### Phase 2：精简分类缓存写入（减少写放大）

- [x] 删除自动分类过程中对 `classification_rules:{db_type}` 的写入
- [x] `get_classification_cache_stats()` 改为仅读取 `classification_rules:all` 并计算分组计数
- [x] `db_type` 定向清理同步清理 `classification_rules:all`（保持对外语义可用）
- [x] 单测更新：`tests/unit/services/test_cache_fallback_observability.py`
- [x] 契约不回归：`tests/unit/routes/test_api_v1_cache_contract.py`

### Phase 3：TTL 配置化与 Settings 清理（可选）

- [ ] Dashboard TTL 配置化（避免散落硬编码）
- [ ] 清理/标注未被消费的 `CACHE_*` 配置项（降低误导与心智负担）
- [x] 文档同步：Obsidian/reference 与 optimization 文档去除旧 CacheService 引用

## 变更记录

- 2026-01-25: 创建 plan/progress 文档，落地 OptionsCache + 分类缓存写放大治理，补齐单测与契约验证。
