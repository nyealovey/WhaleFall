# 003 缓存策略优化方案（Plan）

> 状态: Active
> 负责人: @shiyijiufei
> 创建: 2026-01-25
> 更新: 2026-01-25
> 范围: 缓存策略收敛与补齐（Options 缓存、分类缓存精简、TTL/key 规范化与可观测性）
> 关联: `docs/Obsidian/standards/doc/guide/changes.md`, `docs/Obsidian/standards/doc/guide/documentation.md`, `app/utils/cache_utils.py`, `app/services/account_classification/cache.py`, `app/services/common/filter_options_service.py`

---

## 动机与范围

当前后端缓存已完成“单一抽象”收敛：仅保留 `CacheManager`（`app/utils/cache_utils.py`）+ Flask-Caching(redis backend)。

但从代码实际使用来看，仍存在 3 类明显问题：

1) **该缓存的没缓存**：大量下拉/筛选项（实例、标签、分类、数据库等）由 `FilterOptionsService`（`app/services/common/filter_options_service.py`）集中提供，既被 API 端点使用（例如 `/api/v1/instances/options`），也被 Web 路由使用（多个页面服务端渲染时都会查询一次）。这些数据“读多写少”，适合缓存，但目前每次请求都会打 DB。
2) **缓存写放大**：账户分类在每次自动分类时都会写入按 `db_type` 分组的规则缓存（`classification_rules:{db_type}`，见 `app/services/account_classification/orchestrator.py`），但该缓存目前主要用于“缓存统计”而非核心分类逻辑，存在不必要的 Redis 写入与 key 增长风险。
3) **策略不一致/可维护性不足**：
   - Dashboard 缓存 TTL 写死在装饰器调用点（多个 `@dashboard_cache(timeout=...)`），无法通过配置统一调整。
   - Redis key 命名缺少全局 namespace/version，未来若 Redis 复用（限流、其他服务、不同环境共享）容易产生冲突或排查困难。
   - `Settings` 中仍保留部分 cache 相关配置（如 `CACHE_DEFAULT_TTL/CACHE_RULE_EVALUATION_TTL/CACHE_ACCOUNT_TTL`），但当前代码不再消费，增加理解成本。

本方案聚焦“行为不变的结构性优化”：

- 增加并标准化“读多写少”的 Options 缓存（主要目标）。
- 精简分类缓存的写入策略（减少不必要的 Redis 写入/存储）。
- 统一 key/TTL/可观测性（降低后续演进成本）。

## 不变约束（行为/契约/性能门槛）

- API 契约不变：
  - `/api/v1/cache/**`、`/api/v1/health/**` 的响应封套与错误口径保持不变（以 unit contract tests 为准）。
- 安全不变：
  - 不引入“按用户缓存敏感数据”（例如权限、凭据等）。
  - 不引入 Redis `SCAN/KEYS` 作为常规逻辑（避免生产抖动与不可控耗时）。
- 行为不变（面向 UI 用户）：
  - Dropdown/筛选项允许短 TTL（秒级/分钟级）带来的短暂延迟，但必须保证写操作后“最终一致”可达（通过 TTL 或显式失效）。
- 性能门槛：
  - options 类接口与页面渲染路径的 DB 查询次数应可观察下降（至少能在日志/指标里对比）。

## 现状盘点（plan 制定时的落地前现状）

> 备注：当前落地状态请以 progress 为准：`docs/changes/refactor/003-cache-strategy-optimization-progress.md`。

### 1) 已缓存且仍需要的点

- Dashboard 函数级缓存（Redis）：
  - 入口：`app/utils/cache_utils.py` 的 `@dashboard_cache`
  - 使用：`app/services/dashboard/dashboard_overview_service.py`、`app/services/dashboard/dashboard_charts_service.py`
  - TTL：30s~300s（硬编码）
- 账户分类规则缓存（Redis，固定 key）：
  - 实现：`app/services/account_classification/cache.py`
  - keys：`classification_rules:all`、`classification_rules:{db_type}`
  - TTL：读 `app.config["CACHE_RULE_TTL"]`，默认 2h

### 2)（落地前）缺失缓存但读频较高的点（候选）

`FilterOptionsService`（`app/services/common/filter_options_service.py`）包含多类“下拉/筛选”数据：

- `list_active_tag_options()` / `list_tag_categories()` / `list_classification_options()`
- `list_instance_select_options(db_type=...)`
- `list_database_select_options(instance_id=...)`
- API 专用：`get_common_instances_options(db_type=...)`、`get_common_databases_options(filters)`

这些方法被多个 Web 路由与 API 路由调用（可在仓库内 `rg -n "FilterOptionsService\\(" app` 看到），典型特征是“读多写少、数据体量小、形状稳定”。

### 3)（落地前）可能存在“缓存但收益不明显/写放大”的点（候选）

- 分类规则按 `db_type` 缓存（`classification_rules:{db_type}`）：
  - 当前写入位置：`app/services/account_classification/orchestrator.py` 的 `_group_rules_by_db_type()`
  - 当前读取位置：`app/services/cache/cache_actions_service.py` 的 `get_classification_cache_stats()`（用于统计/展示）
  - 核心分类逻辑并不依赖该缓存命中（分类过程已有 `rules_by_db_type` 的内存分组）。

## 目标形态（缓存分层 + 统一策略）

### 1) 统一分层边界（依赖方向/禁止项）

- `app/utils/cache_utils.py`：
  - 只提供“基础设施能力”（CacheManager + decorators），不承载业务 key 约定。
- `app/services/*/cache.py`（业务缓存访问器）：
  - 承载固定 key 约定、TTL 选择、value schema（如 classification rules wrapper）。
  - MUST：通过 `CacheManagerRegistry.get()` 获取缓存能力；MUST NOT：直接 import `app.cache` 或直接操作 redis client。
- `app/services/*_service.py`：
  - 只调用 cache 访问器，不拼 key。
- `app/api/*` / `app/routes/*`：
  - MUST NOT：直接 get/set cache；只调用 service。

### 2) key 命名与版本（建议）

建议引入统一 key 前缀（namespace + version）：

- 形式示例：`whalefall:v1:{domain}:{name}:{...}`
- 目标：避免与限流 key、其他服务 key 冲突；当 value schema 变更时可通过 bump `vN` 避免旧缓存反序列化/形状漂移问题。

## 分阶段计划（每阶段验收口径）

> 本计划预期拆多 PR 推进；落地时需配套 `003-cache-strategy-optimization-progress.md` 记录 Checklist 与进度。

### Phase 0：补齐“缓存策略文档 + 可观测口径”

- 明确：
  - 哪些数据允许缓存（读多写少、非敏感、形状稳定）
  - 哪些数据禁止缓存（用户敏感、写频高且无有效失效）
- 统一日志字段：
  - cache hit/miss、fallback_reason、key 前缀（至少在 debug 可见）

验收：

- `uv run pytest -m unit -q`

### Phase 1：引入 OptionsCache（FilterOptions 缓存化）

新增 `OptionsCache`（建议路径：`app/services/common/options_cache.py`）并将 `FilterOptionsService` 的读路径改为：

1) 先读缓存（固定 key）
2) miss 时读 DB
3) 写入缓存（短 TTL）

建议 key（示例）：

- `whalefall:v1:options:instances:{db_type|all}`
- `whalefall:v1:options:tags:active`
- `whalefall:v1:options:tag-categories:active`
- `whalefall:v1:options:classifications:active`
- `whalefall:v1:options:databases:{instance_id}`

TTL 建议（先保守，后续用观测调整）：

- instances/tags/classifications：60s~300s
- databases（按 instance_id）：30s~60s

失效策略（优先级）：

- 先使用短 TTL 达成最终一致
- 如需要更实时，再在写服务中“显式 delete 固定 key”（必须是可枚举的固定 key，避免 scan/keys）

验收：

- `uv run pytest -m unit -q`
- 手工：打开 2~3 个页面（实例列表、标签管理、账户分类）确认下拉选项仍可用

### Phase 2：精简分类缓存写入（减少写放大）

目标：分类缓存保留“必要命中点”，减少“仅用于统计的写入”。

可选策略（二选一，建议先选 A）：

- A（推荐）：仅保留 `classification_rules:all` 的缓存命中（核心读路径），删除 `classification_rules:{db_type}` 的写入；统计页按 `classification_rules:all` 计算各 `db_type` 数量（读时分组），不再依赖 per-db_type key。
- B：保留 per-db_type key，但仅在“规则变更时”写入（而不是每次分类运行都写）。

验收：

- `uv run pytest -m unit -q`
- 手工：分类统计接口/页面返回结构不变（以 contract tests 为准）

### Phase 3：TTL 配置化与 Settings 清理

目标：

- 将 Dashboard TTL（overview/status/charts）与 OptionsCache TTL 收敛到 `Settings`（`app/settings.py`），避免散落硬编码。
- 清理未被使用的 cache 配置项，或标注为“保留字段”（二选一）：
  - 若短期内无使用计划，建议删除 `CACHE_DEFAULT_TTL/CACHE_RULE_EVALUATION_TTL/CACHE_ACCOUNT_TTL`，避免误导。

验收：

- `make typecheck`
- `uv run pytest -m unit -q`

## 风险与回滚

风险：

- Options 缓存引入后可能出现“短时间不一致”（写后读仍看到旧选项），尤其是标签/实例刚新增时。
- key 前缀/版本引入后，若存在直接依赖旧 key 的外部脚本（理论上不应存在），会出现行为变化。

回滚策略：

- Phase 1/2/3 都应保持“可单独回滚”的最小粒度 PR：
  - 回滚 OptionsCache：将 FilterOptionsService 恢复为直读 DB
  - 回滚分类缓存精简：恢复 per-db_type 写入或恢复旧统计逻辑
  - key 前缀/版本：通过 bump version 也可达到“软回滚”（避免使用旧数据）

## 验证与门禁

- 单元测试门禁：
  - `uv run pytest -m unit -q`
  - Options 相关 contract：`tests/unit/routes/test_api_v1_common_options_contract.py`
  - cache/health contract：`tests/unit/routes/test_api_v1_cache_contract.py`、`tests/unit/routes/test_api_v1_health_extended_contract.py`
- 类型检查门禁：
  - `make typecheck`
